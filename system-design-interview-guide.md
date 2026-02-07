# System Design Interview Guide

## Section 1: Framework & Template

### 4-Step Framework

| Step | Time (45 min) | Time (60 min) | Focus |
|------|--------------|--------------|-------|
| 1. Requirements & Scope | 5 min | 5-7 min | Functional & non-functional requirements, constraints |
| 2. Back-of-Envelope Estimation | 5 min | 5-8 min | QPS, storage, bandwidth, memory |
| 3. High-Level Design | 15 min | 20 min | API design, data model, architecture diagram |
| 4. Deep Dive | 20 min | 25-30 min | Bottlenecks, scaling, trade-offs |

### Step 1: Requirements Checklist

**Functional Requirements** — What does the system do?
- Core use cases (read-heavy? write-heavy? both?)
- Who are the users? (end users, internal services, APIs)
- Input/output for each operation

**Non-Functional Requirements** — How well does it do it?
- Availability target (99.9%? 99.99%?)
- Latency target (p50, p99)
- Consistency model (strong vs eventual)
- Durability guarantees
- Security & privacy constraints

### Step 2: Estimation Templates

```
Users:        ___M DAU
Read QPS:     DAU × reads_per_user / 86400
Write QPS:    DAU × writes_per_user / 86400
Peak QPS:     Average × 2-5x
Storage/day:  Write QPS × avg_object_size × 86400
Storage/year: Storage/day × 365
Bandwidth:    QPS × avg_object_size
Cache memory: Read QPS × avg_object_size × cache_duration (80/20 rule)
```

### Step 3: Building Blocks Reference

| Component | When to Use |
|-----------|------------|
| Load Balancer | Distribute traffic across servers (L4/L7) |
| API Gateway | Rate limiting, auth, routing, protocol translation |
| CDN | Static content, geographically distributed users |
| Cache (Redis/Memcached) | Reduce DB load, low-latency reads |
| Relational DB (PostgreSQL/MySQL) | Structured data, ACID transactions, joins |
| NoSQL (Cassandra/DynamoDB) | High write throughput, flexible schema, horizontal scaling |
| Document Store (MongoDB) | Semi-structured data, nested objects |
| Search Engine (Elasticsearch) | Full-text search, fuzzy matching, aggregations |
| Message Queue (Kafka/SQS) | Async processing, decoupling, buffering |
| Object Storage (S3) | Files, images, videos, backups |
| Blob Storage | Large binary objects |
| Coordination Service (ZooKeeper) | Leader election, distributed locks, config |
| Task Queue (Celery/Sidekiq) | Background jobs, scheduled tasks |

### Common Trade-offs Table

| Decision | Option A | Option B | Choose A When | Choose B When |
|----------|----------|----------|---------------|---------------|
| Database | SQL | NoSQL | Need ACID, joins, complex queries | Need horizontal scale, flexible schema, high write throughput |
| Consistency | Strong | Eventual | Financial data, inventory | Social feeds, analytics, caching |
| Communication | Sync (REST/gRPC) | Async (message queue) | Low latency needed, simple flow | Decouple services, handle spikes, retry needed |
| Data model | Normalized | Denormalized | Write-heavy, data integrity | Read-heavy, reduce joins |
| Caching | Cache-aside | Write-through | Infrequent reads of same data | Read-heavy with tolerance for write latency |
| ID generation | Auto-increment | Distributed ID (Snowflake) | Single DB, no sharding | Distributed system, need global uniqueness |
| Scaling | Vertical | Horizontal | Simple, under moderate load | High traffic, need fault tolerance |
| Storage | Row-oriented | Column-oriented | OLTP, point lookups | OLAP, aggregations, analytics |
| Push vs Pull | Push (WebSocket/SSE) | Pull (polling) | Real-time updates needed | Infrequent updates, simpler infra |

---

## Section 2: Core Concepts Reference

### Scaling

**Vertical Scaling** — Bigger machine (more CPU/RAM/disk). Simple but has limits and single point of failure.

**Horizontal Scaling** — More machines. Requires stateless services, data partitioning, and service discovery. Preferred for large-scale systems.

### Caching Strategies

| Strategy | How It Works | Pros | Cons |
|----------|-------------|------|------|
| Cache-Aside | App reads cache → miss → read DB → populate cache | Only caches what's needed; cache failure not fatal | Cache miss = extra latency; stale data possible |
| Write-Through | App writes to cache → cache writes to DB | Cache always consistent with DB | Write latency increased; unused data cached |
| Write-Back | App writes to cache → cache async writes to DB | Low write latency; batching | Data loss risk if cache fails before flush |
| Read-Through | Cache itself fetches from DB on miss | Simplified app logic | Cache must understand data source |

**Cache Invalidation** — TTL-based, event-based (pub/sub on writes), or versioned keys. TTL is simplest; event-based is most consistent.

**Cache Stampede Prevention** — Locking (single thread refills), early expiry (probabilistic refresh before TTL), or stale-while-revalidate.

### Database Sharding & Partitioning

**Sharding strategies:**
- **Hash-based** — hash(key) % N. Even distribution but resharding is expensive. Use consistent hashing to minimize data movement.
- **Range-based** — partition by value range (e.g., user ID 1-1M, 1M-2M). Supports range queries but prone to hotspots.
- **Directory-based** — lookup service maps key → shard. Flexible but adds a dependency.

**Problems with sharding:**
- Cross-shard joins (denormalize or application-level joins)
- Hotspots (celebrity problem — further split hot shards)
- Resharding (consistent hashing, virtual nodes)
- Referential integrity (application-level enforcement)

### Consistency Models

| Model | Guarantee | Use Case |
|-------|-----------|----------|
| Strong (linearizable) | Reads always see latest write | Banking, inventory, leader election |
| Sequential | All nodes see operations in same order | Distributed locks |
| Causal | Causally related ops seen in order | Social media comments/replies |
| Eventual | All replicas converge eventually | DNS, social feeds, caches |

**CAP Theorem** — In a network partition, choose Consistency (CP) or Availability (AP). In practice, most systems are AP with tunable consistency per operation.

### Load Balancing Algorithms

- **Round Robin** — Simple, equal distribution. Good when servers are homogeneous.
- **Weighted Round Robin** — Accounts for different server capacities.
- **Least Connections** — Routes to server with fewest active connections. Good for long-lived connections.
- **Consistent Hashing** — Maps requests to servers via hash ring. Minimizes redistribution when servers added/removed. Used for cache sharding.
- **L4 vs L7** — L4 (transport layer, faster, no content inspection) vs L7 (application layer, content-based routing, SSL termination).

**Consistent Hashing Ring Implementation:**
```python
class ConsistentHashRing:
    def __init__(self, nodes=[], vnodes=150):
        self.vnodes = vnodes  # virtual nodes per physical node
        self.ring = {}        # hash -> node mapping
        self.sorted_keys = [] # sorted hash positions
        for node in nodes:
            self.add_node(node)

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node):
        for i in range(self.vnodes):
            vnode_key = f"{node}:vnode{i}"
            hash_val = self._hash(vnode_key)
            self.ring[hash_val] = node
            bisect.insort(self.sorted_keys, hash_val)

    def remove_node(self, node):
        for i in range(self.vnodes):
            vnode_key = f"{node}:vnode{i}"
            hash_val = self._hash(vnode_key)
            del self.ring[hash_val]
            self.sorted_keys.remove(hash_val)

    def get_node(self, key):
        if not self.ring:
            return None
        hash_val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0  # wrap around
        return self.ring[self.sorted_keys[idx]]
```

### Message Queues & Event-Driven Architecture

**When to use:**
- Decouple producers and consumers
- Buffer writes during traffic spikes
- Enable retry and dead-letter handling
- Fan-out to multiple consumers

**Patterns:**
- **Point-to-point** — One producer, one consumer (task queue)
- **Pub/Sub** — One producer, many consumers (event notification)
- **Event Sourcing** — Store events as source of truth, derive state
- **CQRS** — Separate read and write models

**Kafka specifics:** Partitioned topics, consumer groups, offset tracking, log compaction. Guarantees ordering within a partition.

### Replication

- **Single-leader** — One writer, multiple readers. Simple but leader is bottleneck/SPOF. Failover via leader election.
- **Multi-leader** — Multiple writers. Better availability but conflict resolution needed (last-write-wins, CRDTs, merge functions).
- **Leaderless** — Quorum reads/writes (R + W > N). Dynamo-style. No failover needed but more complex.

**Failure Detection & Recovery Protocols:**
- **Heartbeat Detection:** Node states (ALIVE → SUSPECT after missed heartbeats → DEAD after timeout). Typical: heartbeat every 1s, suspect after 3 missed, dead after 10s.
- **Phi-Accrual Detector:** Track heartbeat inter-arrival times, compute probability of failure. Adaptive to network conditions. `phi = -log10(P(heartbeat_late))`. Threshold typically 8-12.
- **Leader Failover Protocol:**
  1. Followers detect leader timeout (e.g., 10s no heartbeat)
  2. Follower with highest priority/log position initiates election
  3. Requests votes from peers (Raft: needs majority)
  4. Winner becomes leader, broadcasts new term
  5. Clients redirect to new leader
- **Read Repair:** On quorum read, if replicas disagree, update stale replicas with latest value
- **Anti-Entropy:** Background process compares Merkle trees between replicas, syncs differences
- **Hinted Handoff:** When target node is down, store write as "hint" on another node, deliver when target recovers

---

## Section 3: Common System Design Questions

---

### 1. Design a URL Shortener (TinyURL)

**Requirements**
- Functional: Create short URL from long URL; redirect short → long; optional custom aliases; optional expiry
- Non-functional: Very low latency redirect (<100ms); high availability; 100M URLs created/day

**Estimation**
- Write QPS: 100M / 86400 ≈ 1200/s
- Read QPS (100:1 read/write): 120K/s
- Storage per URL: ~500 bytes (short + long URL + metadata)
- Storage/year: 100M × 365 × 500B ≈ 18 TB/year

**High-Level Design**
```
Client → API Gateway → Write Service → DB (key-value store)
                     → Read Service  → Cache (Redis) → DB
```

**Key Components**

*Short URL Generation:*
- Base62 encoding of auto-increment ID (a-z, A-Z, 0-9): 7 chars = 62^7 ≈ 3.5 trillion combinations
- Alternatively, hash (MD5/SHA256) of long URL, take first 7 chars. Handle collisions by appending counter.
- For distributed ID generation: pre-allocate ID ranges to each server, or use Snowflake IDs

**Base62 Encoding Implementation:**
```python
CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def encode_base62(num):
    if num == 0:
        return CHARSET[0]
    result = []
    while num > 0:
        result.append(CHARSET[num % 62])
        num //= 62
    return ''.join(reversed(result))

def decode_base62(s):
    num = 0
    for char in s:
        num = num * 62 + CHARSET.index(char)
    return num

# Example: encode_base62(123456789) → "8M0kX"
# 7 chars supports 62^7 = 3.5 trillion unique URLs
```

**Distributed ID Generation:**
```python
class IDGenerator:
    def __init__(self, server_id, range_size=10000):
        self.server_id = server_id
        self.range_size = range_size
        self.current_id = None
        self.range_end = None

    def next_id(self):
        if self.current_id is None or self.current_id >= self.range_end:
            # Request new range from coordination service
            self.current_id, self.range_end = self._allocate_range()
        id = self.current_id
        self.current_id += 1
        return id
```

*Data Model:*
```
urls table:
  short_url (PK) | long_url | created_at | expires_at | user_id
```

*Storage:* Key-value store (DynamoDB/Cassandra) — simple lookups by key, high read throughput, easy to shard by short_url hash.

**Deep Dive**
- **Caching:** Cache-aside with Redis. Cache top 20% of URLs (80/20 rule). ~120K QPS × 500B = 60 MB/s throughput.
- **Read path:** Cache → DB. Hot URLs served from cache at <1ms.
- **Analytics:** Async write click events to Kafka → analytics pipeline.
- **Expiry:** Lazy deletion (check on read) + periodic background cleanup.

**Trade-offs**
- Base62(ID) vs Hash: ID guarantees no collision but is predictable/guessable; hash is random but needs collision handling
- SQL vs NoSQL: NoSQL preferred — simple key-value access, no joins, easy horizontal scaling
- 301 (permanent) vs 302 (temporary) redirect: 301 is cached by browser (fewer requests but lose analytics); 302 lets you track every click

---

### 2. Design a Rate Limiter

**Requirements**
- Functional: Limit requests per client per time window; return 429 when exceeded; configurable rules per API endpoint
- Non-functional: Low latency (<1ms overhead); highly available; accurate limiting in distributed setting

**Estimation**
- 10M active users, peak 1M concurrent
- Rate limit check on every request: 500K QPS
- Minimal storage per counter: user_id + count + timestamp ≈ 50 bytes
- Memory for all counters: 10M × 50B = 500 MB (fits in single Redis instance)

**High-Level Design**
```
Client → API Gateway (rate limiter middleware) → Backend Services
                ↓
         Redis (counters)
         Rules DB (rate limit configs)
```

**Key Components**

*Algorithms:*

| Algorithm | How It Works | Pros | Cons |
|-----------|-------------|------|------|
| Fixed Window | Count requests in fixed time windows | Simple, low memory | Boundary burst (2x limit at window edge) |
| Sliding Window Log | Store timestamp of each request | Accurate | High memory (stores every timestamp) |
| Sliding Window Counter | Weighted combo of current + previous window | Accurate, low memory | Slight approximation |
| Token Bucket | Tokens added at fixed rate, consumed per request | Allows controlled bursts | Slightly more complex |
| Leaky Bucket | Requests processed at fixed rate, queue overflow rejected | Smooth output rate | Doesn't allow bursts |

*Token Bucket (most common):*
```
bucket = {tokens: N, last_refill: timestamp}
on request:
  refill tokens based on elapsed time (up to max)
  if tokens >= 1: allow, decrement
  else: reject (429)
```

*Data Model (Redis):*
```
Key: rate_limit:{user_id}:{endpoint}
Value: {tokens: int, last_refill: timestamp}
Operations: GET + SET with TTL (atomic via Lua script)
```

**Token Bucket Rate Limiter (Redis Lua Script):**
```lua
-- Token Bucket Rate Limiter (atomic Lua script)
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])  -- tokens per second
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4]) or 1

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or max_tokens
local last_refill = tonumber(bucket[2]) or now

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local refill = elapsed * refill_rate
tokens = math.min(max_tokens, tokens + refill)

-- Check if request can be allowed
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, tokens}  -- allowed, remaining tokens
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {0, tokens}  -- rejected, remaining tokens
end
```

**Rate Limiter Usage:**
```python
def check_rate_limit(user_id, endpoint, max_tokens=100, refill_rate=10):
    key = f"ratelimit:{user_id}:{endpoint}"
    now = time.time()
    allowed, remaining = redis.eval(LUA_SCRIPT, 1, key, max_tokens, refill_rate, now, 1)
    return {
        "allowed": bool(allowed),
        "X-RateLimit-Remaining": remaining,
        "X-RateLimit-Limit": max_tokens,
        "X-RateLimit-Reset": int(now) + int((max_tokens - remaining) / refill_rate)
    }
```

**Deep Dive**
- **Distributed rate limiting:** Use Redis with Lua scripts for atomic check-and-decrement. Accept slight over-counting in exchange for performance (no distributed locks).
- **Race conditions:** Redis Lua script makes read-check-update atomic within single Redis node.
- **Multi-datacenter:** Each DC can have local rate limiter with eventual sync, or use a global Redis cluster. Local is faster but allows N× the limit across N DCs.
- **Rules engine:** Store rules in DB, cache in memory on each rate limiter node, refresh periodically.
- **Response headers:** Include `X-RateLimit-Remaining`, `X-RateLimit-Limit`, `X-RateLimit-Reset`.

**Trade-offs**
- Accuracy vs Performance: Strict global limiting requires centralized store (slower); local limiting is fast but approximate
- Token Bucket vs Sliding Window: Token bucket allows bursts (good for bursty traffic); sliding window is smoother
- Hard vs Soft limits: Hard reject (429) vs soft (log and allow, degrade gracefully)

---

### 3. Design a Chat System (WhatsApp/Messenger)

**Requirements**
- Functional: 1:1 messaging; group chat (up to 500 members); online/offline status; message history; read receipts; media sharing
- Non-functional: Low latency delivery (<500ms); message ordering guaranteed per conversation; at-least-once delivery; 500M DAU

**Estimation**
- Messages/day: 500M users × 40 messages = 20B messages/day
- Write QPS: 20B / 86400 ≈ 230K/s
- Message size: ~200 bytes text + metadata
- Storage/day: 20B × 200B = 4 TB/day
- Concurrent WebSocket connections: ~100M

**High-Level Design**
```
Client ↔ WebSocket Server (stateful) ↔ Message Service → Message Queue (Kafka)
                                                        → Message Store (Cassandra)
                                         ↕
                                    Presence Service (Redis)
                                    Group Service
                                    Push Notification Service
```

**Key Components**

*Connection Management:*
- WebSocket for real-time bidirectional communication
- Connection server maintains mapping: user_id → server_id (stored in Redis/ZooKeeper)
- Heartbeat every 30s to detect disconnection
- Reconnection with message catch-up from last received message_id

*Message Flow (1:1):*
1. Sender → WebSocket → Chat Service
2. Chat Service looks up recipient's connection server
3. If online: route message to recipient's WebSocket server → deliver
4. If offline: store in DB, send push notification
5. Acknowledge delivery to sender

*Message Storage:*
```
messages table (Cassandra):
  conversation_id (partition key) | message_id (clustering key, time-based)
  | sender_id | content | type | created_at | status
```
- Cassandra: excellent write throughput, time-series friendly, partition by conversation_id
- Message_id: Snowflake ID for global ordering

*Group Messaging:*
- Small groups (<500): fan-out on write — write message once, create delivery entry per member
- Fan-out via message queue: publish to group topic, each member's delivery worker consumes

*Presence Service:*
- User heartbeat updates Redis: `online:{user_id} → {server_id, last_seen}`
- TTL-based expiry (e.g., 60s). No heartbeat = offline.
- Subscribe to friend presence changes via pub/sub

**Deep Dive**
- **End-to-end encryption:** Signal Protocol. Server stores encrypted blobs, cannot read content. Key exchange on first contact.

**Signal Protocol E2E Encryption Details:**

*Key Types:*
| Key | Lifetime | Purpose |
|-----|----------|---------|
| Identity Key (IK) | Permanent | Long-term identity verification |
| Signed Pre-Key (SPK) | ~1 month | Medium-term, signed by IK |
| One-Time Pre-Keys (OPK) | Single use | Prevent replay attacks |
| Root Key (RK) | Per-conversation | Derives chain keys |
| Chain Key (CK) | Per-message-batch | Derives message keys |
| Message Key (MK) | Single message | Encrypts one message (AES-256-GCM) |

*X3DH Key Exchange (first message):*
```
Alice (initiator):                    Server:                    Bob (recipient):
1. Fetch Bob's keys          →        Returns IK_B, SPK_B, OPK_B
2. Generate ephemeral key EK_A
3. Compute shared secrets:
   DH1 = DH(IK_A, SPK_B)     # Alice's identity, Bob's signed pre-key
   DH2 = DH(EK_A, IK_B)      # Alice's ephemeral, Bob's identity
   DH3 = DH(EK_A, SPK_B)     # Alice's ephemeral, Bob's signed pre-key
   DH4 = DH(EK_A, OPK_B)     # Alice's ephemeral, Bob's one-time pre-key
   SK = KDF(DH1 || DH2 || DH3 || DH4)
4. Send encrypted message    →        Store for Bob
5. Bob receives, computes same DH values, derives SK, decrypts
```

*Double Ratchet (ongoing messages):*
- **DH Ratchet:** New DH key pair per message batch → forward secrecy
- **Symmetric Ratchet:** Chain key → message key via KDF → each message has unique key
- **Result:** Compromise of one key doesn't expose past/future messages

*Server sees only:* sender, recipient, timestamp, encrypted blob (cannot decrypt content)

- **Message ordering:** Snowflake IDs ensure global ordering. Within a conversation, Cassandra clustering key orders by time.
- **Multi-device sync:** Each device has device_id. Messages delivered to all active devices. Sync cursor per device.
- **Media:** Upload to object storage (S3), send URL in message. Thumbnail generation via async worker.

**Trade-offs**
- WebSocket vs Long Polling: WebSocket is more efficient for high-frequency messaging; long polling is simpler but higher latency
- Fan-out on write vs read: Write (small groups, low latency read) vs Read (large groups, saves storage)
- Cassandra vs MySQL: Cassandra scales writes better; MySQL better for complex queries but harder to shard

---

### 4. Design a Video Streaming Service (YouTube)

**Requirements**
- Functional: Upload videos; stream (adaptive bitrate); search; recommendations; comments/likes; channels/subscriptions
- Non-functional: High availability; low startup latency (<2s); smooth playback; support 1B DAU; global reach

**Estimation**
- DAU: 1B; average 5 videos/day watched
- Video views: 5B/day → 58K/s
- Uploads: 500K videos/day → 6/s
- Average video: 300 MB (pre-transcoding), 5 min
- Upload storage/day: 500K × 300 MB = 150 TB/day
- Transcoded (multiple resolutions): 5× = 750 TB/day
- Bandwidth (streaming): 58K/s × 3 MB/s average bitrate = 174 TB/s (served from CDN)

**High-Level Design**
```
Upload Path:
  Creator → Upload Service → Object Storage (raw)
                           → Transcoding Pipeline (async) → Object Storage (transcoded)
                           → Metadata Service → DB

Streaming Path:
  Viewer → CDN (cache hit) → Stream video
         → CDN (cache miss) → Origin Storage → CDN → Stream
  Viewer → API Server → Metadata/Search/Recommendation Services → DB
```

**Key Components**

*Video Upload & Processing Pipeline:*
1. Client uploads to Upload Service (resumable upload via chunked transfer)
2. Raw video stored in object storage (S3)
3. Message sent to transcoding queue (Kafka)
4. Transcoding workers: convert to multiple resolutions (360p, 720p, 1080p, 4K) and codecs (H.264, VP9, AV1)
5. Generate thumbnails, extract metadata
6. Store transcoded videos in object storage
7. Update metadata DB with video status = "ready"

*Adaptive Bitrate Streaming (ABR):*
- Video split into segments (2-10 seconds each)
- Each segment available in multiple bitrates
- Client requests manifest file (HLS .m3u8 or DASH .mpd)
- Client dynamically selects bitrate per segment based on bandwidth

**HLS Manifest Examples:**

*Master Manifest (.m3u8):*
```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
360p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1400000,RESOLUTION=854x480
480p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720
720p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p/playlist.m3u8
```

*Media Playlist (720p/playlist.m3u8):*
```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:6.0,
segment_0.ts
#EXTINF:6.0,
segment_1.ts
...
```

**Bitrate Selection Algorithm:**
```python
class ABRController:
    def __init__(self):
        self.throughput_history = []  # last N measurements
        self.buffer_level = 0         # seconds of buffered video

    def select_variant(self, variants, measured_throughput):
        # Exponential weighted moving average of throughput
        self.throughput_history.append(measured_throughput)
        ewma = self._compute_ewma(self.throughput_history, alpha=0.3)

        # Conservative estimate: use 70% of measured throughput
        safe_bandwidth = ewma * 0.7

        # Buffer-based adjustment
        if self.buffer_level < 5:      # low buffer: be conservative
            safe_bandwidth *= 0.5
        elif self.buffer_level > 30:   # high buffer: can be aggressive
            safe_bandwidth *= 1.2

        # Select highest variant that fits
        selected = variants[0]  # lowest quality as fallback
        for variant in sorted(variants, key=lambda v: v.bandwidth):
            if variant.bandwidth <= safe_bandwidth:
                selected = variant
        return selected
```

*CDN Strategy:*
- Serve popular videos from edge caches (80/20 rule)
- Multi-tier: Edge → Regional → Origin
- Pre-populate edge caches with trending videos
- Long-tail content served from origin with caching on first access

*Data Model:*
```
videos: video_id (PK) | creator_id | title | description | status | upload_time | view_count
video_segments: video_id | resolution | segment_number | storage_url | duration
```

**Deep Dive**
- **Transcoding at scale:** DAG-based pipeline (split → transcode in parallel per resolution → merge). Use spot/preemptible instances for cost savings. Prioritize popular creator uploads.
- **Search:** Elasticsearch index on title, description, tags. Ranking by relevance + popularity.
- **Recommendations:** Collaborative filtering + content-based. Precomputed for active users, real-time blending at serving time.
- **Cost optimization:** Compress older/less-viewed videos more aggressively. Tiered storage (hot → warm → cold).

**Trade-offs**
- Pre-transcode all resolutions vs On-demand: Pre-transcode (higher storage cost, instant playback) vs on-demand (lower storage, initial delay, good for long-tail)
- Push to CDN vs Pull: Push popular content proactively; pull for long-tail
- Monolith vs Microservices: Microservices for upload, transcode, search, recommendation, streaming — each scales independently

---

### 5. Design a Social Media Feed (Instagram/Twitter)

**Requirements**
- Functional: Post creation (text, images, video); news feed (timeline of followed users' posts); follow/unfollow; like/comment; stories (ephemeral)
- Non-functional: Feed generation <500ms; eventual consistency acceptable; 500M DAU; read-heavy (100:1)

**Estimation**
- DAU: 500M; average 10 feed refreshes/day
- Feed reads: 5B/day → 58K/s
- New posts: 500M × 2 posts/day = 1B/day → 12K/s
- Feed size: 50 posts × 1 KB = 50 KB per feed load

**High-Level Design**
```
Post Creation:
  User → Post Service → Posts DB → Fan-out Service → Feed Cache (per user)

Feed Read:
  User → Feed Service → Feed Cache → Hydrate (post details, user info) → Return
```

**Key Components**

*Fan-out Strategies:*

| Strategy | How | Pros | Cons |
|----------|-----|------|------|
| Fan-out on Write (push) | On new post, write to every follower's feed cache | Fast reads, precomputed feed | Slow writes for users with millions of followers; wasted work for inactive users |
| Fan-out on Read (pull) | On feed request, query all followed users' posts | No wasted computation | Slow reads, query N users at read time |
| Hybrid | Push for normal users; pull for celebrity users | Best of both | More complex |

*Hybrid approach (recommended):*
- Users with <10K followers: fan-out on write (push to follower feeds)
- Celebrities (>10K followers): fan-out on read (merge at read time)
- Feed = precomputed feed cache + real-time merge of celebrity posts

*Feed Cache (Redis sorted set):*
```
Key: feed:{user_id}
Value: sorted set of (post_id, timestamp), keep latest 500
```

*Data Model:*
```
posts: post_id | user_id | content | media_urls | created_at
follows: follower_id | followee_id | created_at
feed_cache: user_id → [post_id list ordered by time]
```

*Feed Ranking:*
- Chronological base ordering
- ML ranking model: engagement prediction (P(like), P(comment), P(share))
- Features: post age, author relationship strength, content type, user engagement history

**ML Ranking Model Architecture:**

*Two-Stage Architecture:*
```
Stage 1: Candidate Retrieval (1000s → 500)
├── Recent posts from followed users (last 48h)
├── Trending posts (high engagement velocity)
└── Collaborative filtering (users similar to you liked this)

Stage 2: Ranking (500 → 50)
└── Multi-task neural network scores each candidate
```

*Feature Categories:*
| Category | Features |
|----------|----------|
| User | demographics, past engagement rates, session time, following count |
| Post | age_minutes, media_type, text_length, creator_follower_count |
| User-Post | is_following, past_interactions_with_author, topic_affinity |
| Context | time_of_day, device_type, current_session_depth |

*Multi-Task Ranking Model:*
```
Input Features (embeddings + numeric)
         ↓
[Shared Dense Layers: 256 → 128 → 64]
         ↓
    ┌────┴────┬────────┬────────┬────────┐
    ↓         ↓        ↓        ↓        ↓
P(like)  P(comment) P(share) P(save)  P(hide)
  0.12      0.03      0.01     0.05    0.002

Final Score = w1*P(like) + w2*P(comment) + w3*P(share) + w4*P(save) - w5*P(hide)
            = 0.4*0.12  + 0.3*0.03    + 0.2*0.01   + 0.2*0.05  - 1.0*0.002
            = 0.068
```

*Latency Budget:* Retrieval: 20ms | Ranking: 30ms | Total: <100ms for 50 posts

**Deep Dive**
- **Fan-out service:** Async via Kafka. On new post, fan-out workers read follower list and write to each follower's feed cache. Batch updates for efficiency.
- **Media storage:** Images/videos stored in S3, served via CDN. Multiple resolutions generated on upload.
- **Trending/Explore:** Separate pipeline. Aggregate engagement signals (likes, shares, comments) in real-time (Flink/Spark Streaming). Surface trending content to explore tab.
- **Stories:** Separate data path with TTL (24 hours). Redis with TTL or Cassandra with TTL columns.

**Trade-offs**
- Push vs Pull vs Hybrid: Hybrid handles the celebrity problem while keeping reads fast
- Consistency: Eventual consistency for feed (slight delay in post appearing is acceptable). Strong consistency for follow/unfollow actions.
- Chronological vs Ranked feed: Ranked increases engagement but reduces transparency; offer toggle

---

### 6. Design a Search Autocomplete System

**Requirements**
- Functional: Return top 5-10 suggestions as user types; suggestions based on popularity/frequency; update with new queries
- Non-functional: <100ms latency per keystroke; high availability; scale to 10B queries/day

**Estimation**
- 10B queries/day, average 4 characters typed per suggestion → 40B autocomplete requests/day
- QPS: 40B / 86400 ≈ 460K/s
- Unique queries: ~5B (store top 10M for autocomplete)
- Trie node count: ~10M × avg 15 chars = 150M nodes × 100 bytes = 15 GB (fits in memory)

**High-Level Design**
```
User types → API Server → Trie Service (in-memory trie) → Return top suggestions
                                    ↑
                    Trie Builder (offline, periodic) ← Query Analytics (Kafka → aggregation)
```

**Key Components**

*Trie (Prefix Tree):*
- Each node stores: character, children map, top-K suggestions (precomputed)
- Precomputing top-K at each node avoids traversal at query time → O(prefix_length) lookup
- Example: node for "app" stores ["apple", "application", "app store", "appointment", "appetite"]

*Data Gathering Pipeline (offline):*
1. Search queries logged to Kafka
2. Aggregation service (Spark/Flink) counts query frequency in sliding windows (hourly, daily, weekly)
3. Trie builder constructs new trie from aggregated data
4. New trie deployed to trie servers via blue-green swap

*Serving Architecture:*
- Trie replicated across multiple servers per region
- Consistent hashing to shard by prefix (a-f → shard 1, g-m → shard 2, etc.)
- Or replicate full trie if it fits in memory (15 GB)
- Client-side optimizations: debounce (wait 100-200ms between requests), cache previous results, only query after 2+ characters

*Filtering:*
- Remove offensive/harmful suggestions (blocklist filter)
- Remove low-quality or spammy suggestions
- Personalization layer (optional): boost suggestions based on user history

**Deep Dive**
- **Trie update frequency:** Rebuild every 15-60 minutes from aggregated data. Not real-time — trending queries appear with slight delay.
- **Multi-language support:** Separate tries per language. Detect language from user locale or input characters.
- **Scaling:** Shard by prefix for very large datasets. Each shard handles a range of prefixes. Add replicas for read throughput.
- **Caching:** Browser caches results for typed prefixes. CDN caches popular prefixes. Redis cache in front of trie servers.

**Trade-offs**
- Trie vs Elasticsearch prefix queries: Trie is faster for pure prefix matching; ES is more flexible but higher latency
- Precomputed top-K vs Real-time ranking: Precomputed is faster but stale; real-time is fresh but slower
- Full replication vs Sharding: Replication is simpler (data fits in memory); sharding needed if dataset grows beyond single node

---

### 7. Design a Notification System

**Requirements**
- Functional: Push notifications (mobile), SMS, email; template-based messages; subscription preferences; scheduling; analytics (delivered, opened, clicked)
- Non-functional: Soft real-time (<30s delivery); at-least-once delivery; no duplicate delivery; 100M notifications/day

**Estimation**
- 100M notifications/day → 1200/s average, 5000/s peak
- Storage per notification: 500 bytes (metadata + content)
- Storage/day: 100M × 500B = 50 GB/day

**High-Level Design**
```
Event Sources → Notification Service → Preference Check → Priority Queue → Delivery Workers
  (services,                              (user prefs,       (Kafka)        ↓        ↓       ↓
   cron jobs,                               rate limit,                   APNS    SMTP    SMS
   API calls)                               dedup)                       (iOS)   (Email)  (Twilio)
                                                                                    ↓
                                                                             Analytics Store
```

**Key Components**

*Notification Flow:*
1. Event source sends notification request (user_id, type, template_id, params)
2. Notification Service validates, checks user preferences (opt-in/out per channel)
3. Rate limiting per user (no more than N notifications per hour)
4. Deduplication (idempotency key check against Redis)
5. Template rendering (inject params into template)
6. Enqueue to channel-specific Kafka topic (push, email, SMS)
7. Delivery workers consume and send via third-party providers
8. Track delivery status (sent, delivered, failed, opened)

*Data Model:*
```
notifications: notification_id | user_id | channel | content | status | created_at | sent_at
preferences: user_id | channel | category | enabled
templates: template_id | channel | subject_template | body_template
```

*Priority System:*
- Separate Kafka topics or partitions by priority (critical, high, medium, low)
- Critical: security alerts, OTP codes (immediate delivery)
- Low: marketing, weekly digests (can be batched/delayed)

**Deep Dive**
- **Reliability:** Kafka provides durability. Delivery workers acknowledge only after successful send. Failed deliveries go to retry queue with exponential backoff. Dead letter queue for permanent failures.
- **Deduplication:** Store idempotency keys in Redis with TTL. Before sending, check if notification was already sent.
- **Analytics pipeline:** Delivery events → Kafka → Flink → aggregation store. Track funnel: sent → delivered → opened → clicked.
- **Third-party provider failover:** Multiple providers per channel (e.g., two SMS providers). Circuit breaker pattern — if primary fails, route to secondary.

**Trade-offs**
- Push vs Pull: Push for time-sensitive; pull (in-app notification center) for non-urgent
- At-least-once vs Exactly-once: At-least-once is simpler; exactly-once requires dedup at consumer
- Immediate vs Batched: Immediate for transactional (OTP, alerts); batched for marketing (digest emails)

---

### 8. Design a Distributed Cache (Redis-like)

**Requirements**
- Functional: GET/SET/DELETE by key; TTL support; support various data structures (strings, lists, sets, hashes); pub/sub
- Non-functional: Sub-millisecond latency; 1M+ ops/sec per node; high availability; linear horizontal scaling

**Estimation**
- 1M ops/sec per node; 10 nodes = 10M ops/sec cluster
- Average key-value size: 1 KB
- Total data: 10 nodes × 64 GB RAM = 640 GB cache capacity
- Network: 10M ops × 1 KB = 10 GB/s cluster throughput

**High-Level Design**
```
Client (with client-side consistent hashing)
  ↓
Cache Node 1    Cache Node 2    Cache Node 3  ...  Cache Node N
[Hash Ring]     [Hash Ring]     [Hash Ring]        [Hash Ring]
[In-Memory      [In-Memory      [In-Memory         [In-Memory
 Hash Table]     Hash Table]     Hash Table]         Hash Table]
  ↓                ↓                ↓                   ↓
[AOF/RDB        [AOF/RDB        [AOF/RDB           [AOF/RDB
 Persistence]    Persistence]    Persistence]        Persistence]
```

**Key Components**

*Data Partitioning (Consistent Hashing):*
- Hash ring with virtual nodes (100-200 vnodes per physical node)
- Client hashes key → maps to position on ring → routes to responsible node
- Adding/removing node only affects neighboring keys (~1/N of data migrates)

*In-Memory Data Store:*
- Hash table for O(1) key lookup
- Each entry: key, value, TTL, metadata
- Eviction policies when memory full: LRU (least recently used), LFU (least frequently used), random, TTL-based

*TTL & Expiration:*
- Lazy expiration: check TTL on access, delete if expired
- Active expiration: background thread samples random keys periodically, deletes expired ones
- Combination of both (Redis approach)

*Replication & High Availability:*
- Each primary node has 1-2 replica nodes
- Async replication (primary → replica) for performance
- On primary failure: replica promoted via leader election (Raft or sentinel-based)
- Client redirected to new primary

*Persistence (optional):*
- RDB snapshots: periodic point-in-time snapshot to disk. Fast recovery but potential data loss between snapshots.
- AOF (Append-Only File): log every write operation. More durable but larger files. Periodically rewrite/compact.

**Deep Dive**
- **Single-threaded event loop:** Process commands sequentially per node (like Redis). Avoids locking overhead. I/O multiplexing (epoll) handles many concurrent connections.
- **Cluster coordination:** Gossip protocol for node health and cluster state. Each node pings random peers, shares cluster topology.
- **Hot key problem:** Detect hot keys via access counting. Solutions: read from replicas, client-side caching, key splitting (append random suffix, fan-out reads).
- **Memory management:** Pre-allocate memory pools. Use memory-efficient encodings for small data (ziplist for small lists/hashes).

**Trade-offs**
- Consistency vs Performance: Async replication is fast but risks data loss on failover; sync replication is safe but slower
- Memory vs Disk: Pure in-memory (fastest, volatile) vs persistence (slower writes, durable)
- Single-threaded vs Multi-threaded: Single-threaded avoids locking (simpler, predictable latency); multi-threaded can use all cores but adds complexity

---

### 9. Design an Object Storage System (S3-like)

**Requirements**
- Functional: PUT/GET/DELETE objects by key; bucket-based namespace; support objects from 1 KB to 5 TB; versioning; metadata; access control
- Non-functional: 99.999999999% (11 nines) durability; 99.99% availability; high throughput for large objects; billions of objects

**Estimation**
- 1B objects, average 1 MB = 1 EB total storage
- 100K PUT/s, 500K GET/s
- Write throughput: 100K × 1 MB = 100 GB/s
- Replication factor 3 → 3 EB raw storage

**High-Level Design**
```
Client → API Gateway (auth, routing)
           ↓
         Metadata Service → Metadata DB (key → location mapping)
           ↓
         Data Service → Data Nodes (actual blob storage)
```

**Key Components**

*Separation of Metadata and Data:*
- Metadata: object key, size, checksum, location (list of data nodes + chunk offsets), ACL, versioning info
- Data: actual bytes, stored as chunks on data nodes

*Metadata Store:*
- Distributed key-value store (sharded by bucket + object key hash)
- Schema: `(bucket, key) → {object_id, version, size, checksum, chunk_locations[], created_at, acl}`
- Must handle billions of keys: consistent hashing or range-based sharding

*Data Storage:*
- Large objects split into chunks (e.g., 64 MB each)
- Each chunk replicated to 3+ data nodes across failure domains (rack, AZ)
- Erasure coding for cold data: store k data chunks + m parity chunks (e.g., 8+4). Recoverable from any k chunks. 1.5× storage vs 3× for replication.
- Data nodes manage local disk, report health to coordination service

*Write Path:*
1. Client → API Gateway → Metadata Service allocates object_id, selects target data nodes
2. Client streams data to Data Service → primary data node
3. Primary replicates to secondary nodes
4. On success, Metadata Service records chunk locations
5. Return success to client

*Read Path:*
1. Client → Metadata Service → lookup chunk locations
2. Client (or Data Service) reads chunks from data nodes (closest/fastest)
3. Assemble and return object

*Durability:*
- 3-way replication across availability zones
- Periodic integrity checks (checksums on read and background scrubbing)
- Repair: detect missing/corrupt replicas, re-replicate from healthy copies
- Erasure coding for archival tier

**Deep Dive**
- **Garbage collection:** Deleted objects marked for deletion. Background GC reclaims disk space. Versioned objects retain old versions until explicitly deleted.
- **Multipart upload:** Large files uploaded in parallel parts (e.g., 100 MB each). Parts assembled server-side on completion. Allows resume on failure.
- **Storage tiers:** Hot (SSD, frequent access), Warm (HDD), Cold (tape/deep archive). Lifecycle policies auto-transition objects.
- **Consistency:** Strong consistency for metadata (object visible immediately after PUT). Data nodes eventually consistent for replication.

**Trade-offs**
- Replication vs Erasure Coding: Replication (simple, fast reads, 3× storage) vs EC (complex, slower reads, 1.5× storage). Use replication for hot data, EC for cold.
- Flat namespace vs Hierarchical: Flat is simpler and scales better; hierarchical (folders) can be simulated with prefix-based listing
- Strong vs Eventual consistency: Strong (simpler for clients, read-after-write) vs eventual (higher availability)

---

### 10. Design a Web Crawler

**Requirements**
- Functional: Crawl web pages starting from seed URLs; extract and follow links; store page content; respect robots.txt; handle deduplication
- Non-functional: Crawl 1B pages/day; politeness (don't overload sites); fault-tolerant; extensible (support different content types)

**Estimation**
- 1B pages/day → 11,500 pages/s
- Average page size: 500 KB (HTML + resources)
- Storage/day: 1B × 500 KB = 500 TB/day (compressed ~100 TB)
- URLs to track: 10B URLs in frontier → ~1 TB for URL metadata

**High-Level Design**
```
Seed URLs → URL Frontier (priority queue)
                ↓
            Fetcher Workers (distributed)
                ↓
            Content Parser → Extract links → URL Filter/Dedup → URL Frontier
                ↓
            Content Store (S3/HDFS) → Indexer
```

**Key Components**

*URL Frontier:*
- Priority queue: prioritize by page importance (PageRank, domain authority, freshness)
- Politeness queue: separate queue per domain, enforce delay between requests to same domain (respect crawl-delay in robots.txt)
- Implementation: multiple FIFO queues (one per domain) behind a priority selector

*Fetcher:*
- Distributed workers fetch URLs from frontier
- DNS resolver cache (avoid repeated DNS lookups)
- HTTP client with timeout, redirect following, retry logic
- Robots.txt parser and cache (per domain, refresh periodically)
- User-Agent identification

*Deduplication:*
- URL dedup: Bloom filter (space-efficient, allows false positives but no false negatives). 10B URLs × 10 bits = ~12 GB.
- Content dedup: SimHash or MinHash for near-duplicate detection. Compute fingerprint of page content, compare against seen fingerprints.

*Content Processing:*
1. Parse HTML, extract text and links
2. Normalize URLs (remove fragments, canonicalize)
3. Check URL against Bloom filter (skip if seen)
4. Add new URLs to frontier
5. Store page content with metadata (URL, timestamp, HTTP headers)

**Deep Dive**
- **Politeness:** Maintain per-domain rate limit. Typically 1 request per second per domain. Use domain-based queue sharding — each worker handles specific domains.
- **Spider traps:** Detect infinite URL patterns (e.g., calendar pages generating infinite dates). Limit crawl depth. URL pattern detection (reject URLs matching repetitive patterns).
- **Freshness:** Re-crawl pages based on change frequency. Track page change rate, prioritize frequently changing pages. Use HTTP conditional requests (If-Modified-Since, ETag).
- **Fault tolerance:** Checkpoint frontier state periodically. On worker failure, reassign URLs. Idempotent processing — re-crawling a URL is safe.
- **Distributed coordination:** Partition URL space across workers by domain hash. Central coordination service manages worker assignments and health.

**Trade-offs**
- BFS vs DFS: BFS finds important pages first (broader coverage); DFS goes deeper into specific sites. BFS preferred for general crawlers.
- Bloom filter vs Exact set: Bloom filter uses ~12 GB for 10B URLs (vs 1 TB for hash set); accepts ~1% false positive (skip some valid URLs)
- Store raw HTML vs Parsed text: Raw is larger but preserves structure for re-processing; parsed is smaller but lossy

## Section 4: Data Platform Questions

### Question 11: Design a Stream Processing System (Flink/Spark Streaming)

**Requirements**
- Functional: Ingest continuous event streams, apply transformations/aggregations, produce output to sinks (DB, queue, lake). Support windowed aggregations (tumbling, sliding, session). Exactly-once processing semantics.
- Non-functional: Sub-second latency for simple transforms, low-single-digit seconds for windowed aggregations. Handle 1M+ events/sec. Fault-tolerant with automatic recovery. Backpressure handling to avoid data loss.
- Scale: 1M events/sec ingestion, 1 KB avg event size → ~1 GB/s throughput. Thousands of parallel tasks across hundreds of nodes.

**Estimation**
```
Events:           1M/sec × 1 KB = 1 GB/sec ingestion
State size:       Windows × keys × value size. E.g., 5-min window, 1M keys, 100 bytes = 100 GB state
Checkpoints:      State snapshot every 30-60 sec → 100 GB written per checkpoint
Output:           ~500K aggregated results/sec to sinks
Cluster:          ~200 task slots across 50 nodes (4 slots each)
```

**High-Level Design**
```
Data Sources (Kafka topics)
       │
       ▼
┌─────────────────────────┐
│     Source Operators     │  (parallel readers, one per partition)
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Processing Operators   │  (map, filter, keyBy, window, aggregate)
│  ┌───────────────────┐  │
│  │  State Backend     │  │  (RocksDB for large state, heap for small)
│  └───────────────────┘  │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│     Sink Operators      │  (write to Kafka, DB, cloud storage)
└─────────────────────────┘

Coordination:
┌──────────────────┐     ┌──────────────────┐
│   Job Manager    │────▶│ Checkpoint Store  │ (GCS/S3/HDFS)
│  (coordination,  │     └──────────────────┘
│   scheduling)    │
└──────────────────┘
```

**Key Components**

*Windowing:*
- Tumbling: Fixed non-overlapping intervals (e.g., every 5 min)
- Sliding: Overlapping intervals (5-min window every 1 min)
- Session: Gap-based, per key (close window after N min inactivity)
- Watermarks: Track event-time progress, trigger window evaluation. Watermark = max_event_time - allowed_lateness.

**Watermark Calculation:**

*Bounded Out-of-Order Watermark:*
```python
class BoundedWatermarkGenerator:
    def __init__(self, max_out_of_order_ms=5000):
        self.max_out_of_order = max_out_of_order_ms
        self.max_timestamp_seen = 0

    def on_event(self, event_time):
        self.max_timestamp_seen = max(self.max_timestamp_seen, event_time)

    def current_watermark(self):
        # Watermark = max seen timestamp - allowed lateness
        return self.max_timestamp_seen - self.max_out_of_order

# Example timeline:
# Event times:  [10:00:01, 10:00:05, 10:00:03, 10:00:08]
# max_seen:     [10:00:01, 10:00:05, 10:00:05, 10:00:08]
# watermark:    [09:59:56, 10:00:00, 10:00:00, 10:00:03]  (5s lateness)
```

*Per-Partition Watermarks (Kafka):*
```
Partition 0: watermark = 10:00:03
Partition 1: watermark = 10:00:07
Partition 2: watermark = 10:00:01  (slow partition)

Global watermark = min(all partitions) = 10:00:01
Window [10:00:00-10:00:05] cannot close until slowest partition advances
```

*Handling Idle Partitions:*
```python
if partition.idle_for > idle_timeout:
    partition.watermark = current_processing_time  # advance artificially
```

*Exactly-Once Semantics:*
- Source: Replayable sources (Kafka offsets). On recovery, replay from last committed offset.
- Internal: Checkpoint barriers flow through the DAG. Aligned barriers ensure consistent snapshots across all operators. On failure, restore state from last checkpoint and replay.
- Sink: Idempotent writes (upsert by key) or two-phase commit (pre-commit on checkpoint, commit on checkpoint-complete).

*Checkpointing:*
- Periodic async snapshots of all operator state.
- Barrier alignment: Barriers from job manager flow through DAG. Operator snapshots state when barrier arrives from all inputs.
- Incremental checkpoints: Only write changed state (RocksDB SST diffs). Reduces checkpoint size from 100 GB to ~1-5 GB incremental.

*Backpressure:*
- Credit-based flow control: Downstream operators advertise available buffer capacity. Upstream slows when no credits available.
- Propagates naturally through the DAG to sources.
- Metrics: Track buffer utilization per operator to identify bottlenecks.

**Deep Dive**
- **State management:** RocksDB state backend for large state (spills to disk, supports incremental checkpoints). Heap backend for small state (<1 GB, faster access). State TTL to auto-expire stale keys.
- **Late data:** Watermarks define "completeness." Late events (after watermark) can trigger side-output or update previously emitted results. Allowed lateness window: keep window state for extra time to handle stragglers.
- **Rescaling:** Redistribute state across new parallelism. Key-group-based state partitioning — state split into max-parallelism key groups, redistributed on scale-up/down.
- **Failure recovery:** On task failure, restart from last successful checkpoint. All operators restore state, sources replay from checkpointed offsets. Recovery time = checkpoint restore + replay gap (typically 10-30 sec).

**Trade-offs**
- Micro-batch (Spark Streaming) vs Continuous (Flink): Micro-batch has higher latency (~seconds) but simpler exactly-once; continuous has sub-second latency but more complex state management.
- Aligned vs Unaligned checkpoints: Aligned is simpler but can cause backpressure during checkpoint; unaligned avoids this but increases checkpoint size.
- Event time vs Processing time: Event time gives correct results for out-of-order data but requires watermarks and buffering; processing time is simpler but less accurate.

---

### Question 12: Design a Data Lake / Lakehouse Platform

**Requirements**
- Functional: Ingest data from diverse sources (streaming, batch, CDC). Store structured/semi-structured data on cloud object storage. Support SQL queries, ML workloads, and batch ETL. Schema enforcement and evolution. ACID transactions on the lake.
- Non-functional: Petabyte-scale storage. Query latency from seconds (interactive) to hours (batch). 99.9% availability for query engine. Cost-efficient (separate storage and compute).
- Scale: 10 PB total data, 100 TB daily ingestion, 1000+ concurrent users, 10K+ tables.

**Estimation**
```
Storage:          10 PB on cloud storage (GCS/S3) at ~$20/TB/mo = $200K/mo
Daily ingestion:  100 TB/day → ~1.2 GB/sec sustained
Tables:           10K tables, avg 1 TB each, Parquet format (~3:1 compression)
Queries:          1000 concurrent users × 10 queries/day = 10K queries/day
Metadata:         10K tables × 1000 partitions × 100 files = 1B file entries
```

**High-Level Design**
```
Data Sources                        Query Engines
(Kafka, DBs, APIs, Files)          (Spark, Presto/Trino, Hive)
       │                                    │
       ▼                                    ▼
┌──────────────┐               ┌───────────────────┐
│  Ingestion   │               │   Query Planning   │
│  Layer       │               │   & Optimization   │
│ (batch/CDC/  │               └────────┬──────────┘
│  streaming)  │                        │
└──────┬───────┘                        │
       │          ┌─────────────┐       │
       └─────────▶│  Table      │◀──────┘
                  │  Format     │
                  │ (Delta/     │
                  │  Iceberg/   │
                  │  Hudi)      │
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌────────────┐
        │ Metadata │ │ Data   │ │ Catalog    │
        │ (txn log,│ │(Parquet│ │(Hive Meta- │
        │ manifest)│ │on GCS/ │ │ store/     │
        │          │ │S3)     │ │ Unity/     │
        └──────────┘ └────────┘ │ Glue)      │
                                └────────────┘
```

**Key Components**

*Storage Layer:*
- Columnar formats: Parquet (most common) or ORC. Column pruning, predicate pushdown, efficient compression.
- Partitioning: By date/region/key. Reduces scan scope. Avoid over-partitioning (small files problem).
- File sizing: Target 128 MB-1 GB per file. Small files degrade query performance (metadata overhead, task scheduling).

*Table Format (Delta/Iceberg/Hudi):*
- Transaction log: Ordered log of commits (add/remove files). Provides ACID — concurrent writers use optimistic concurrency.
- Schema evolution: Add/rename/drop columns without rewriting data. Reader handles missing columns with defaults.
- Time travel: Query data as of any past commit/timestamp. Enabled by retaining old file references in the transaction log.
- Compaction: Background process merges small files into larger ones. Z-order or Hilbert curve clustering for multi-dimensional query optimization.

**Z-Ordering Algorithm:**

*Z-Value Calculation (bit interleaving):*
```python
def z_order_2d(x, y):
    """Interleave bits of x and y to create Z-value"""
    z = 0
    for i in range(16):  # 16 bits per coordinate
        z |= ((x & (1 << i)) << i) | ((y & (1 << i)) << (i + 1))
    return z

# Example: x=5 (0101), y=3 (0011)
# Interleaved: 00_01_11_01 = 0x1D = 29
# Points close in 2D space have similar Z-values
```

*Multi-Column Z-Ordering:*
```python
def z_order_multi(values, bits_per_col=16):
    """Z-order for N columns"""
    z = 0
    n_cols = len(values)
    for bit in range(bits_per_col):
        for col_idx, val in enumerate(values):
            if val & (1 << bit):
                z |= 1 << (bit * n_cols + col_idx)
    return z
```

*Delta Lake Usage:*
```sql
OPTIMIZE my_table
ZORDER BY (date, user_id, product_id)
```

*How Data Skipping Works:*
```
File 1: date=[2024-01-01, 2024-01-03], user_id=[100, 500]   # Z-values: 0-1000
File 2: date=[2024-01-01, 2024-01-03], user_id=[501, 900]   # Z-values: 1001-2000
File 3: date=[2024-01-04, 2024-01-06], user_id=[100, 500]   # Z-values: 2001-3000

Query: WHERE date = '2024-01-02' AND user_id = 250
→ Only scan File 1 (skip Files 2, 3 based on min/max stats)
```

*When NOT to use Z-order:*
- Single-column filters (use regular partitioning instead)
- Highly skewed columns (one value dominates)
- Very high cardinality columns (>1M distinct values)

*Metadata Catalog:*
- Central registry of tables, schemas, partitions, and statistics.
- Hive Metastore (legacy) or modern catalogs (Unity Catalog, AWS Glue, Nessie).
- Column-level statistics (min/max, null count, distinct count) for query optimization.

*Ingestion Patterns:*
- Batch: Spark jobs writing partitioned Parquet. Append or overwrite partitions.
- CDC (Change Data Capture): Debezium → Kafka → merge into lake table (upsert by primary key).
- Streaming: Spark Structured Streaming or Flink writing micro-batches to Delta/Iceberg tables.

**Deep Dive**
- **Query optimization:** Partition pruning (skip irrelevant partitions), data skipping via min/max stats (skip files where predicate cannot match), Z-ordering co-locates related data to maximize skipping effectiveness.
- **Concurrency control:** Optimistic concurrency — writers check for conflicts at commit time. Conflict if two writers modify same partition/files. Retry on conflict. Readers always see consistent snapshot (MVCC via transaction log).
- **Small file problem:** Many small files degrade performance. Auto-compaction merges files. Bin-packing: group small files into target size. Scheduled compaction jobs (e.g., hourly).
- **Cost optimization:** Separate storage (cheap, $20/TB/mo on GCS/S3) from compute (expensive, on-demand). Lifecycle policies: move cold data to archive tiers. Cache hot data on local SSD for interactive queries.

**Trade-offs**
- Delta vs Iceberg vs Hudi: Delta is Spark-native with strong Databricks integration; Iceberg has better multi-engine support and hidden partitioning; Hudi excels at upsert-heavy workloads with record-level indexing.
- Parquet vs ORC: Parquet is more widely adopted (Spark default, better ecosystem support); ORC has better built-in indexing and is Hive-native.
- Single large cluster vs Multiple small clusters: Large cluster has better resource utilization; multiple clusters provide isolation and independent scaling per workload.

---

### Question 13: Design a Workflow/Pipeline Orchestration System (Airflow-like)

**Requirements**
- Functional: Define pipelines as DAGs (directed acyclic graphs). Schedule DAGs on cron or event triggers. Manage task dependencies, retries, and timeouts. Support backfill (re-run historical date ranges). Provide UI for monitoring, logs, and manual actions.
- Non-functional: Execute 100K+ task instances/day. No single point of failure. Task execution exactly-once semantics (or at-least-once with idempotent tasks). Sub-minute scheduling latency.
- Scale: 10K DAGs, 100K task instances/day, 1000 concurrent tasks.

**Estimation**
```
DAGs:             10K DAGs, avg 10 tasks each = 100K task definitions
Task instances:   100K/day = ~1.2/sec avg, peak 10/sec
Execution:        1000 concurrent tasks × avg 10 min = ~170 worker slots needed
Metadata DB:      100K rows/day × 365 days × 1 KB = ~36 GB/year
Logs:             100K tasks/day × 100 KB avg log = 10 GB/day
```

**High-Level Design**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Web UI     │    │  CLI / API   │    │  DAG Files   │
└──────┬───────┘    └──────┬───────┘    │  (Git repo)  │
       │                   │            └──────┬───────┘
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────┐
│                  API Server                      │
│  (DAG parsing, REST API, auth)                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                  Scheduler                       │
│  (DAG scheduling, dependency resolution,         │
│   task queuing, trigger management)              │
└──────────┬────────────────────┬─────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│   Metadata DB    │  │   Task Queue     │
│  (PostgreSQL)    │  │  (Redis/Celery/  │
│  - DAG state     │  │   K8s queue)     │
│  - Task state    │  └────────┬─────────┘
│  - Run history   │           │
└──────────────────┘           ▼
                     ┌──────────────────┐
                     │   Workers        │
                     │  (execute tasks, │
                     │   report status) │
                     │  ┌────┐ ┌────┐   │
                     │  │ W1 │ │ W2 │...│
                     │  └────┘ └────┘   │
                     └──────────────────┘
```

**Key Components**

*DAG Parsing & Scheduling:*
- DAGs defined as code (Python). Parsed by scheduler to build dependency graph.
- Scheduler loop: For each active DAG, check if schedule interval has elapsed. For each ready run, find tasks with all dependencies met → enqueue.
- Scheduler HA: Multiple schedulers with distributed locking (DB row-level locks) to avoid duplicate scheduling.

*Task Lifecycle:*
```
scheduled → queued → running → success/failed/up_for_retry
                              → upstream_failed (dep failed)
```
- Retries: Configurable per task (retry count, delay, exponential backoff).
- Timeouts: Execution timeout (kill task), DAG-level timeout.
- SLAs: Alert when task doesn't complete by expected time.

*Executor Models:*
- Local: Single-machine, tasks run as subprocesses. Good for development.
- Celery: Distributed workers via message queue (Redis/RabbitMQ). Persistent workers.
- Kubernetes: Each task runs as a K8s pod. Best isolation, auto-scaling, but higher overhead per task.

*Backfill:*
- Re-run DAG for historical date range. Creates task instances for each past interval.
- Respects dependencies. Can run multiple dates in parallel (configurable).
- Idempotent tasks required — re-execution must produce same result (overwrite partition, upsert by key).

**Backfill Parallelization:**

*Backfill Execution Strategy:*
```python
class BackfillController:
    def __init__(self, dag_id, start_date, end_date, max_parallel=10):
        self.dag_id = dag_id
        self.dates = generate_date_range(start_date, end_date)
        self.max_parallel = max_parallel
        self.completed = set()
        self.failed = set()

    def get_next_batch(self):
        """Return next dates to run, respecting parallelism limit"""
        pending = [d for d in self.dates
                   if d not in self.completed and d not in self.failed]
        # Run oldest dates first (dependencies may exist)
        pending.sort()
        return pending[:self.max_parallel]

    def on_complete(self, date, success):
        if success:
            self.completed.add(date)
        else:
            self.failed.add(date)
```

*Dependency-Aware Backfill (DAG with dependencies):*
```
For each date partition:
  Task A (date) → Task B (date) → Task C (date)

Execution order (max_parallel=3):
  Day 1: A    Day 2: A    Day 3: A    (parallel by date, serial within date)
  Day 1: B    Day 2: B    Day 3: B
  Day 1: C    Day 2: C    Day 3: C
```

*Idempotency Patterns:*
| Pattern | Implementation | Use When |
|---------|---------------|----------|
| Partition Overwrite | `INSERT OVERWRITE PARTITION (date='...')` | Partitioned tables |
| Merge/Upsert | `MERGE INTO ... WHEN MATCHED THEN UPDATE` | Dimension tables |
| Delete-then-Insert | `DELETE WHERE date=X; INSERT...` | No native MERGE support |
| Truncate-and-Load | `TRUNCATE TABLE; INSERT...` | Full table refresh |

*Checkpoint/Recovery:*
```python
# Save progress to metadata DB
def checkpoint_state():
    db.execute("""
        INSERT INTO backfill_state (dag_id, date, status, completed_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (dag_id, date) DO UPDATE SET status = %s
    """, (dag_id, date, status, now, status))

# On restart, resume from last checkpoint
def resume_backfill():
    completed = db.query("SELECT date FROM backfill_state WHERE status='success'")
    return [d for d in all_dates if d not in completed]
```

**Deep Dive**
- **Dependency management:** Task dependencies within a DAG (upstream/downstream). Cross-DAG dependencies via sensors (poll for external condition) or dataset-triggered DAGs (DAG runs when upstream DAG writes to a dataset).
- **Scalability bottleneck — Scheduler:** Scheduler must scan all DAGs and tasks. At scale (10K DAGs), single-loop scheduling becomes slow. Solutions: multiple schedulers with DB-based locking, DAG-level sharding, priority queues.
- **Exactly-once execution:** Queue can deliver task twice (worker crash after dequeue). Rely on idempotent tasks + DB state. Worker heartbeat — if heartbeat lost, scheduler marks task as failed and re-queues. DB records final state.
- **Observability:** Task logs stored in cloud storage (GCS/S3), accessible via UI. Metrics: task duration, queue time, failure rate. Alerts on SLA miss, repeated failures.

**Trade-offs**
- DAGs-as-code vs YAML config: Code is flexible and testable but can introduce bugs and is harder to validate statically; YAML is simpler and declarative but limited in expressiveness.
- Pull-based (workers pull tasks) vs Push-based (scheduler assigns tasks): Pull is simpler and naturally load-balances; push gives scheduler more control over placement and priority.
- Celery vs Kubernetes executor: Celery has lower overhead per task (persistent workers) but less isolation; K8s has per-task isolation and auto-scaling but higher startup latency (~10-30 sec pod spin-up).

---

### Question 14: Design a Data Quality & Observability Platform

**Requirements**
- Functional: Define and evaluate data quality rules (schema, nulls, ranges, uniqueness, referential integrity). Detect anomalies (volume changes, distribution drift). Track data lineage (column-level). Monitor freshness (when was table last updated). Alert on violations.
- Non-functional: Evaluate rules within minutes of data landing. Scale to 10K+ tables. Low false-positive rate on anomaly detection. Minimal performance impact on production pipelines.
- Scale: 10K tables, 100K quality rules, 1M rule evaluations/day.

**Estimation**
```
Tables:           10K tables monitored
Rules:            100K rules (avg 10 per table)
Evaluations:      1M/day = ~12/sec avg
Rule execution:   Avg 10 sec per rule (SQL query against table)
Compute:          12 concurrent evaluations × 10 sec = ~120 concurrent queries
Metadata:         1M evaluation results/day × 500 bytes = 500 MB/day
Lineage graph:    10K tables × 50 columns = 500K column nodes, ~2M edges
```

**High-Level Design**
```
┌──────────────────────────────────────────────┐
│                    UI / Dashboard             │
│  (rule management, lineage viewer, alerts)   │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│                 API Server                    │
└───────┬──────────┬──────────┬────────────────┘
        │          │          │
        ▼          ▼          ▼
┌────────────┐ ┌─────────┐ ┌──────────────┐
│ Rule       │ │ Anomaly │ │ Lineage      │
│ Engine     │ │ Detector│ │ Service      │
│            │ │         │ │              │
│ - Schema   │ │ - Stats │ │ - Parse SQL/ │
│ - Null %   │ │   model │ │   Spark plans│
│ - Range    │ │ - Volume│ │ - Column-    │
│ - Unique   │ │   drift │ │   level DAG  │
│ - Custom   │ │ - Dist  │ │ - Impact     │
│   SQL      │ │   shift │ │   analysis   │
└─────┬──────┘ └────┬────┘ └──────┬───────┘
      │             │             │
      ▼             ▼             ▼
┌──────────────────────────────────────────────┐
│            Metadata Store (PostgreSQL)        │
│  Rules, results, lineage graph, alert config │
└──────────────────────────────────────────────┘
      │
      ▼
┌──────────────────┐    ┌──────────────────┐
│  Alert Service   │    │  Data Warehouse  │
│  (PagerDuty,     │    │  / Lake (execute │
│   Slack, email)  │    │   quality queries│
└──────────────────┘    └──────────────────┘
```

**Key Components**

*Rule Engine:*
- Rule types: Schema (column exists, type matches), completeness (null percentage < threshold), validity (values in expected range/set), uniqueness (no duplicates on key columns), freshness (updated within N hours), custom SQL (arbitrary boolean query).
- Rules translated to SQL queries executed against the data warehouse/lake.
- Evaluation triggered by: pipeline completion event, schedule, or manual.

*Anomaly Detection:*
- Statistical profiling: Maintain rolling statistics per column (mean, stddev, percentiles, distinct count, null rate).
- Volume monitoring: Track row count per partition. Alert on significant deviation from historical pattern (e.g., >3 sigma from 7-day rolling average).
- Distribution drift: Compare current value distribution against baseline (KL divergence, KS test). Detect when data semantics change.

*Data Lineage:*
- Parse SQL queries and Spark execution plans to extract column-level lineage.
- Build DAG: source columns → transformations → target columns.
- Impact analysis: Given a quality issue in table A, which downstream tables/dashboards are affected?
- Root cause: Given bad data in table Z, trace back to find the source table/column where the issue originated.

*Freshness Monitoring:*
- Track last-modified timestamp for each table/partition.
- Expected freshness SLA per table (e.g., updated within 2 hours of midnight).
- Alert when table is stale (not updated within SLA window).

**Deep Dive**
- **Minimizing performance impact:** Run quality queries during off-peak hours or on read replicas. Sample large tables instead of full scans (e.g., 1% sample for distribution checks). Profile incrementally — only scan new partitions.
- **False positive management:** Require N consecutive violations before alerting (avoid flapping). Seasonal adjustments (weekday vs weekend patterns). User feedback loop — mark false positives to improve thresholds. Severity tiers: warning vs critical.
- **Lineage accuracy:** SQL parsing covers most cases but misses dynamic queries (string-concatenated SQL). Spark plan parsing catches runtime lineage. Combine static (SQL parse) and runtime (plan) for best coverage. Manual annotations for edge cases.
- **Integration with pipelines:** Embed quality checks as pipeline steps (fail pipeline on critical violations). Gate downstream tasks on upstream quality passing. Publish quality metrics as events for downstream consumers.

**Trade-offs**
- Proactive (in-pipeline checks) vs Reactive (post-pipeline monitoring): Proactive catches issues before they propagate but adds pipeline latency; reactive is non-blocking but issues may reach downstream before detection.
- Full scan vs Sampling: Full scan gives exact results but expensive on large tables; sampling is fast but may miss localized issues (e.g., one bad partition).
- Rule-based vs ML-based anomaly detection: Rules are predictable and explainable but require manual tuning; ML adapts automatically but can be opaque and produce unexpected alerts.

---

### Question 15: Design a Distributed Job Scheduler (Dataproc/YARN-like)

**Requirements**
- Functional: Accept job submissions (Spark, MapReduce, Hive, Presto). Manage cluster resources (CPU, memory, GPU). Multi-tenant resource isolation with quotas and priorities. Auto-scale clusters based on workload. Support preemptible/spot instances for cost savings. Queue management with fair/capacity scheduling.
- Non-functional: Schedule jobs within seconds of submission. Support 10K+ concurrent jobs across 1000+ nodes. 99.9% scheduler availability. Efficient resource utilization (>70% cluster utilization).
- Scale: 1000 nodes, 10K concurrent jobs, 100K cores, 500 TB total memory.

**Estimation**
```
Cluster:          1000 nodes × 100 cores × 500 GB mem = 100K cores, 500 TB mem
Jobs:             10K concurrent, avg 100 tasks each = 1M concurrent tasks
Scheduling:       1000 scheduling decisions/sec at peak
Job submission:   ~100 new jobs/min
Heartbeats:       1000 nodes × 1 heartbeat/3 sec = 333 heartbeats/sec
State:            1M task states × 500 bytes = 500 MB in-memory
```

**High-Level Design**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Spark      │  │   Hive       │  │   Presto     │
│   Driver     │  │   Server     │  │   Coord.     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│           Resource Manager (Master)              │
│  ┌─────────────┐ ┌────────────┐ ┌────────────┐  │
│  │  Scheduler  │ │ App Manager│ │ Node Tracker│  │
│  │ (Fair/FIFO/ │ │ (lifecycle │ │ (health,    │  │
│  │  Capacity)  │ │  mgmt)     │ │  resources) │  │
│  └─────────────┘ └────────────┘ └────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Node    │ │  Node    │ │  Node    │
    │ Manager 1│ │ Manager 2│ │ Manager N│
    │ ┌──┐┌──┐│ │ ┌──┐┌──┐│ │ ┌──┐┌──┐│
    │ │C1││C2││ │ │C1││C2││ │ │C1││C2││  (Containers)
    │ └──┘└──┘│ │ └──┘└──┘│ │ └──┘└──┘│
    └──────────┘ └──────────┘ └──────────┘

Auto-scaler:
┌─────────────────────┐
│  Cluster Autoscaler │ ──▶ Cloud API (add/remove nodes)
│  (metrics-based     │
│   scaling policy)   │
└─────────────────────┘
```

**Key Components**

*Resource Scheduler:*
- FIFO: Simple queue, first-come-first-served. Starves small jobs behind large ones.
- Fair Scheduler: Divides resources equally across queues/users. Preempts over-allocated jobs. Ensures all tenants get fair share.
- Capacity Scheduler: Each queue gets guaranteed capacity percentage. Can borrow from idle queues (elastic). Hierarchical queues (org → team → user).

*Resource Isolation:*
- Containers: Each task runs in a container with capped CPU/memory. Linux cgroups enforce limits.
- Queue quotas: Max resources per queue (prevents one team from consuming entire cluster).
- Preemption: When high-priority job arrives and cluster is full, preempt containers from lower-priority jobs. Preempted tasks are re-queued (requires checkpoint or idempotent tasks).

**Preemption Strategy:**

*Fair Share Calculation:*
```python
def calculate_fair_share(queues, total_resources):
    """Calculate fair share for each queue based on weight and demand"""
    total_weight = sum(q.weight for q in queues)

    for queue in queues:
        queue.fair_share = (queue.weight / total_weight) * total_resources
        # Constrain by actual demand (don't allocate more than needed)
        queue.fair_share = min(queue.fair_share, queue.demand)

    # Redistribute unused share to queues with unmet demand
    redistribute_unused(queues, total_resources)
```

*Preemption Decision Algorithm:*
```python
def should_preempt(queue, cluster_state):
    """Determine if queue should preempt resources from others"""
    # Don't preempt if recently preempted (cooldown period)
    if time_since_last_preempt(queue) < PREEMPTION_COOLDOWN:  # e.g., 30 sec
        return False

    # Calculate how far below fair share this queue is
    current_usage = queue.current_allocated
    shortfall = queue.fair_share - current_usage

    # Only preempt if significantly below fair share (e.g., >10%)
    if shortfall < queue.fair_share * 0.1:
        return False

    # Check if there are queues using more than their fair share
    for other in cluster_state.queues:
        if other.current_allocated > other.fair_share * 1.1:
            return True
    return False

def select_victims(needed_resources, candidate_containers):
    """Select containers to preempt to free needed resources"""
    # Sort by: priority (low first), then runtime (short first)
    candidates = sorted(candidate_containers,
                       key=lambda c: (c.priority, c.runtime))

    victims = []
    freed = 0
    for container in candidates:
        if freed >= needed_resources:
            break
        victims.append(container)
        freed += container.resources
    return victims
```

*Graceful Preemption Process:*
```
1. Mark container for preemption
2. Send SIGTERM to application (allow graceful shutdown)
3. Wait grace_period (e.g., 30 sec) for checkpoint/cleanup
4. If still running, send SIGKILL
5. Release resources, update cluster state
6. Re-queue preempted task for later execution
```

*YARN-Style Configuration:*
```xml
<property>
    <name>yarn.scheduler.fair.preemption</name>
    <value>true</value>
</property>
<property>
    <name>yarn.scheduler.fair.preemption.cluster-utilization-threshold</name>
    <value>0.8</value>  <!-- Only preempt when cluster >80% utilized -->
</property>
<property>
    <name>yarn.scheduler.fair.waitTimeBeforeKill</name>
    <value>30000</value>  <!-- 30 sec grace period -->
</property>
```

*Node Management:*
- Heartbeat: Each node sends heartbeat every 3 sec with resource availability and container status.
- Health check: Detect unhealthy nodes (high error rate, disk failure, network issues). Mark as decommissioned, reschedule tasks.
- Node labels: Tag nodes with attributes (SSD, GPU, high-memory). Jobs can request specific labels for placement.

*Auto-scaling:*
- Scale-up trigger: Pending tasks > threshold for N minutes, or queue wait time > SLA.
- Scale-down trigger: Node idle for N minutes (no running containers). Graceful decommission — wait for tasks to finish, then remove.
- Preemptible/Spot instances: Use for fault-tolerant workloads (Spark with checkpointing). Mix on-demand (30% baseline) + spot (70% burst). Handle spot interruption: 2-min warning → checkpoint and migrate tasks.

*Job Lifecycle:*
```
submitted → accepted → running → finished/failed/killed
```
- Application master: Per-job process that negotiates resources and manages task execution.
- Speculative execution: If a task is slow (>1.5× median), launch duplicate on another node. Take result from whichever finishes first.

**Deep Dive**
- **Scheduling at scale:** 1000 scheduling decisions/sec requires efficient data structures. Maintain sorted queue of pending requests. Use node-capacity index for fast matching (which nodes can satisfy a request). Batch scheduling: process multiple requests per scheduling cycle.
- **Multi-tenancy:** Hierarchical queues map to organization structure. Guaranteed capacity prevents starvation. Elastic sharing borrows idle resources. Preemption policy: configurable (never, within-queue, cross-queue). Fair share calculated recursively through queue hierarchy.
- **Spot instance management:** Maintain pool of spot instances across multiple instance types/zones (diversification reduces simultaneous interruption). On interruption: gracefully migrate tasks (checkpoint + restart). Track spot pricing and bid strategy. Fallback to on-demand if spot unavailable.
- **Fault tolerance:** Resource Manager HA: active-standby with ZooKeeper leader election. State persisted to ZooKeeper or DB. On failover, rebuild state from node heartbeats and running applications. Node failure: reschedule all containers from failed node to healthy nodes.

**Trade-offs**
- Monolithic scheduler vs Two-level (Mesos-style): Monolithic has global view for optimal placement but is a bottleneck at scale; two-level delegates to framework schedulers but can lead to suboptimal global utilization.
- Fair vs Capacity scheduling: Fair gives equal share and is simpler to reason about; Capacity gives guaranteed minimums with borrowing, better for organizations with defined resource budgets.
- Eager vs Lazy autoscaling: Eager (scale up quickly, scale down slowly) reduces wait time but wastes money on idle resources; lazy (scale up cautiously) saves money but jobs wait longer. Typical: scale up in 2 min, scale down after 10 min idle.
