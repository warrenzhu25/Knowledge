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

**URL Frontier Implementation:**

*Two-Level Architecture:*
```
                    ┌─────────────────────────────────┐
                    │     Front Queues (Priority)      │
                    │  ┌─────┐ ┌─────┐ ┌─────┐        │
   URLs to crawl ──▶│  │ P1  │ │ P2  │ │ P3  │ ...    │  (by importance)
                    │  │(high)│ │(med)│ │(low)│        │
                    │  └──┬──┘ └──┬──┘ └──┬──┘        │
                    └─────┼──────┼──────┼────────────┘
                          │      │      │
                          ▼      ▼      ▼
                    ┌─────────────────────────────────┐
                    │   Bipartite Mapping (priority    │
                    │   → domain queue assignment)     │
                    └─────────────┬───────────────────┘
                                  │
                    ┌─────────────▼───────────────────┐
                    │     Back Queues (Politeness)     │
                    │  ┌─────┐ ┌─────┐ ┌─────┐        │
                    │  │dom1 │ │dom2 │ │dom3 │ ...    │  (per domain FIFO)
                    │  └──┬──┘ └──┬──┘ └──┬──┘        │
                    └─────┼──────┼──────┼────────────┘
                          │      │      │
                          ▼      ▼      ▼
                    ┌─────────────────────────────────┐
                    │      Back Queue Selector         │
                    │  (round-robin with rate limit)   │
                    └─────────────┬───────────────────┘
                                  │
                                  ▼
                            Fetcher Workers
```

*Priority Score Calculation:*
```python
class URLPrioritizer:
    def calculate_priority(self, url, metadata):
        """Calculate priority score (higher = more important)"""
        score = 0.0

        # 1. PageRank / Domain authority (pre-computed)
        domain = extract_domain(url)
        score += self.domain_authority.get(domain, 0.1) * 40  # 0-40 points

        # 2. URL depth (shorter paths = more important)
        path_depth = url.count('/') - 2  # subtract protocol slashes
        score += max(0, 20 - path_depth * 2)  # 0-20 points

        # 3. Freshness need (time since last crawl)
        if metadata.last_crawled:
            hours_since = (now() - metadata.last_crawled).total_seconds() / 3600
            expected_change_rate = metadata.change_frequency or 24  # hours
            freshness_score = min(hours_since / expected_change_rate, 1.0)
            score += freshness_score * 20  # 0-20 points
        else:
            score += 20  # Never crawled = high priority

        # 4. Content type bonus
        if self._is_important_page(url):
            score += 10  # Homepage, sitemap, etc.

        # 5. Referrer count (how many pages link to this)
        score += min(metadata.inlink_count * 0.5, 10)  # 0-10 points

        return score

    def assign_to_priority_queue(self, score):
        """Map score to priority queue (0 = highest priority)"""
        if score >= 80:
            return 0  # High priority
        elif score >= 50:
            return 1  # Medium priority
        elif score >= 20:
            return 2  # Low priority
        else:
            return 3  # Background priority
```

*URL Frontier with Politeness:*
```python
class URLFrontier:
    def __init__(self, num_priority_queues=4, politeness_delay=1.0):
        # Front queues: priority-based
        self.front_queues = [deque() for _ in range(num_priority_queues)]

        # Back queues: one per domain for politeness
        self.back_queues = {}  # domain -> deque of URLs
        self.domain_heap = []  # min-heap of (next_allowed_time, domain)
        self.politeness_delay = politeness_delay  # seconds between requests

        # Mapping: track which back queue each front queue item goes to
        self.prioritizer = URLPrioritizer()

        # Concurrency control
        self.lock = threading.Lock()

    def add_url(self, url, metadata=None):
        """Add URL to frontier with priority assignment"""
        metadata = metadata or URLMetadata()
        domain = extract_domain(url)

        with self.lock:
            # Check if already in frontier (dedup)
            if self._is_duplicate(url):
                return False

            # Calculate priority and add to front queue
            priority = self.prioritizer.calculate_priority(url, metadata)
            queue_idx = self.prioritizer.assign_to_priority_queue(priority)
            self.front_queues[queue_idx].append((url, domain, priority))

            return True

    def get_next_url(self):
        """Get next URL respecting both priority and politeness"""
        with self.lock:
            current_time = time.time()

            # Find a domain that's ready to be crawled
            while self.domain_heap:
                next_time, domain = self.domain_heap[0]
                if next_time > current_time:
                    # No domain ready yet, wait or return None
                    return None

                heapq.heappop(self.domain_heap)

                # Get URL from this domain's back queue
                if domain in self.back_queues and self.back_queues[domain]:
                    url = self.back_queues[domain].popleft()

                    # Schedule next fetch for this domain
                    next_allowed = current_time + self._get_crawl_delay(domain)
                    if self.back_queues[domain]:  # More URLs waiting
                        heapq.heappush(self.domain_heap, (next_allowed, domain))

                    return url

            # No URLs in back queues, move from front to back
            self._refill_back_queues()
            return self.get_next_url() if self.domain_heap else None

    def _refill_back_queues(self):
        """Move URLs from priority front queues to per-domain back queues"""
        # Process front queues in priority order
        for queue in self.front_queues:
            while queue:
                url, domain, priority = queue.popleft()

                # Add to domain's back queue
                if domain not in self.back_queues:
                    self.back_queues[domain] = deque()
                    # First URL for this domain, add to heap immediately
                    heapq.heappush(self.domain_heap, (time.time(), domain))

                self.back_queues[domain].append(url)

                # Limit refill batch size
                if len(self.domain_heap) >= 1000:
                    return

    def _get_crawl_delay(self, domain):
        """Get politeness delay for domain (from robots.txt or default)"""
        robots_delay = self.robots_cache.get_crawl_delay(domain)
        return max(robots_delay or self.politeness_delay, 1.0)
```

*Distributed Frontier with Redis:*
```python
class DistributedURLFrontier:
    def __init__(self, redis_client, worker_id):
        self.redis = redis_client
        self.worker_id = worker_id

    def add_url(self, url, priority_score):
        """Add URL to distributed priority queue"""
        domain = extract_domain(url)

        # Add to priority sorted set (score = negative priority for min-heap behavior)
        self.redis.zadd(f"frontier:priority:{domain}", {url: -priority_score})

        # Track domain in active domains set
        self.redis.sadd("frontier:domains", domain)

    def get_next_url(self):
        """Atomically get next URL respecting politeness"""
        # Get domains assigned to this worker (consistent hashing)
        my_domains = self._get_assigned_domains()

        for domain in my_domains:
            # Check if domain is ready (politeness)
            last_fetch_key = f"frontier:last_fetch:{domain}"
            last_fetch = self.redis.get(last_fetch_key)

            if last_fetch:
                elapsed = time.time() - float(last_fetch)
                delay = self._get_crawl_delay(domain)
                if elapsed < delay:
                    continue  # Not ready yet

            # Atomically pop highest priority URL for this domain
            result = self.redis.zpopmin(f"frontier:priority:{domain}", count=1)
            if result:
                url, score = result[0]
                # Record fetch time for politeness
                self.redis.set(last_fetch_key, time.time(), ex=3600)
                return url

        return None  # No URLs ready

    def _get_assigned_domains(self):
        """Get domains assigned to this worker via consistent hashing"""
        all_domains = self.redis.smembers("frontier:domains")
        return [d for d in all_domains
                if consistent_hash(d) % NUM_WORKERS == self.worker_id]
```

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

---

### 11. Design a Ride-Sharing Service (Uber/Lyft)

**Requirements**
- Functional: Rider requests ride with pickup/destination; match with nearby driver; real-time tracking; fare calculation; payments; ratings; driver/rider apps
- Non-functional: Match within 30 seconds; location updates every 3-5 seconds; 99.99% availability; support 20M rides/day; global scale
- Scale: 20M rides/day, 5M concurrent users, 1M active drivers

**Estimation**
```
Rides/day:        20M → 230 rides/sec avg, 1000/sec peak
Active drivers:   1M sending location every 4 sec → 250K updates/sec
Location data:    250K × 100 bytes = 25 MB/sec ingestion
Trip storage:     20M × 2 KB = 40 GB/day
ETA calculations: 230 × 10 (driver candidates) = 2300 routing requests/sec
```

**High-Level Design**
```
┌─────────────┐     ┌─────────────┐
│  Rider App  │     │  Driver App │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────────────┐
│              API Gateway                 │
│  (auth, rate limiting, routing)         │
└─────────┬─────────────────┬─────────────┘
          │                 │
    ┌─────┴─────┐     ┌─────┴─────┐
    ▼           ▼     ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  Trip  │ │Location│ │Matching│ │  Fare  │
│Service │ │Service │ │Service │ │Service │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Trip DB │ │Location│ │ Driver │ │Pricing │
│(Postgres│ │ Index  │ │  Pool  │ │ Rules  │
│/Vitess)│ │(Redis) │ │(Redis) │ │  DB    │
└────────┘ └────────┘ └────────┘ └────────┘

            ┌──────────────┐
            │   Kafka      │ → Analytics, ML, Surge Pricing
            │ (event bus)  │
            └──────────────┘
```

**Key Components**

*Location Service & Geospatial Indexing:*
- Drivers send location every 3-5 seconds via WebSocket/MQTT
- Store in geospatial index for fast nearest-neighbor queries
- Options: Redis with Geo commands, custom geohash index, or S2 cells

**Geohash-Based Driver Index:**
```python
class DriverLocationIndex:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.precision = 6  # ~1.2km x 0.6km cells

    def update_location(self, driver_id, lat, lng, status='available'):
        geohash = encode_geohash(lat, lng, self.precision)
        # Store in sorted set: score = timestamp, enables TTL-based cleanup
        self.redis.zadd(f"drivers:{geohash}", {driver_id: time.time()})
        self.redis.hset(f"driver:{driver_id}", mapping={
            'lat': lat, 'lng': lng, 'status': status, 'geohash': geohash
        })
        self.redis.expire(f"driver:{driver_id}", 30)  # TTL for stale drivers

    def find_nearby_drivers(self, lat, lng, radius_km=3, limit=10):
        center_hash = encode_geohash(lat, lng, self.precision)
        # Get 9 neighboring cells (center + 8 adjacent)
        neighbors = get_geohash_neighbors(center_hash)

        candidates = []
        for gh in neighbors:
            driver_ids = self.redis.zrange(f"drivers:{gh}", 0, -1)
            for did in driver_ids:
                driver = self.redis.hgetall(f"driver:{did}")
                if driver.get('status') == 'available':
                    dist = haversine(lat, lng, driver['lat'], driver['lng'])
                    if dist <= radius_km:
                        candidates.append((did, dist, driver))

        # Sort by distance, return closest
        candidates.sort(key=lambda x: x[1])
        return candidates[:limit]
```

*Matching Algorithm:*
```python
class RideMatchingService:
    def match_rider_to_driver(self, rider_request):
        pickup = rider_request.pickup_location

        # 1. Find nearby available drivers (expand radius if needed)
        for radius in [2, 5, 10]:  # km
            candidates = location_index.find_nearby_drivers(
                pickup.lat, pickup.lng, radius, limit=20
            )
            if len(candidates) >= 5:
                break

        if not candidates:
            return None  # No drivers available

        # 2. Calculate ETA for each candidate (parallel API calls)
        with ThreadPoolExecutor() as executor:
            etas = list(executor.map(
                lambda d: routing_service.get_eta(d.location, pickup),
                candidates
            ))

        # 3. Score candidates (ETA + driver rating + acceptance rate)
        scored = []
        for driver, eta in zip(candidates, etas):
            score = (
                -eta.minutes * 2.0 +           # Lower ETA is better
                driver.rating * 1.0 +           # Higher rating is better
                driver.acceptance_rate * 0.5    # Higher acceptance is better
            )
            scored.append((driver, eta, score))

        scored.sort(key=lambda x: -x[2])  # Highest score first

        # 4. Dispatch to best driver (with timeout for response)
        for driver, eta, score in scored:
            offer = create_ride_offer(rider_request, driver, eta)
            response = send_offer_with_timeout(driver, offer, timeout=15)
            if response.accepted:
                return create_trip(rider_request, driver, eta)
            # Driver declined or timeout, try next

        return None  # All drivers declined
```

*Supply Positioning (Driver Demand Heatmap):*
```python
class DemandHeatmapService:
    def __init__(self):
        self.cell_size = 500  # meters
        self.history_window = 30  # minutes

    def calculate_demand_heatmap(self, city_bounds):
        """Predict demand per cell for next 15 minutes"""
        cells = grid_partition(city_bounds, self.cell_size)

        for cell in cells:
            # Historical demand (same time, day of week, weather)
            historical = self.get_historical_demand(cell, lookback_weeks=4)
            # Recent trend (last 30 min requests in this cell)
            recent = self.get_recent_requests(cell, self.history_window)
            # Events (concerts, sports games from calendar API)
            events = self.get_nearby_events(cell)

            cell.predicted_demand = (
                0.5 * historical.avg +
                0.3 * recent.trend +
                0.2 * events.impact
            )
            cell.current_supply = len(self.get_drivers_in_cell(cell))
            cell.supply_gap = cell.predicted_demand - cell.current_supply

        return cells

    def suggest_driver_repositioning(self, driver):
        """Suggest where driver should move for higher earnings"""
        nearby_cells = self.get_cells_within_radius(driver.location, 5)  # 5km
        # Find undersupplied cells with high demand
        opportunities = [c for c in nearby_cells if c.supply_gap > 2]
        opportunities.sort(key=lambda c: -c.supply_gap)
        return opportunities[:3]
```

*Surge Pricing:*
```python
def calculate_surge_multiplier(cell, current_time):
    demand = cell.pending_requests  # Unfulfilled requests
    supply = cell.available_drivers

    if supply == 0:
        return MAX_SURGE  # e.g., 3.0x

    ratio = demand / supply

    # Tiered surge pricing
    if ratio < 1.0:
        return 1.0
    elif ratio < 1.5:
        return 1.0 + (ratio - 1.0) * 0.5  # 1.0x - 1.25x
    elif ratio < 2.0:
        return 1.25 + (ratio - 1.5) * 0.5  # 1.25x - 1.5x
    elif ratio < 3.0:
        return 1.5 + (ratio - 2.0) * 0.5   # 1.5x - 2.0x
    else:
        return min(2.0 + (ratio - 3.0) * 0.25, MAX_SURGE)  # Cap at 3.0x
```

*Fare Calculation:*
```python
def calculate_fare(trip):
    base_fare = city_config.base_fare  # e.g., $2.50
    per_mile = city_config.per_mile    # e.g., $1.50
    per_minute = city_config.per_minute  # e.g., $0.25
    minimum_fare = city_config.minimum  # e.g., $8.00

    distance_fare = trip.distance_miles * per_mile
    time_fare = trip.duration_minutes * per_minute

    subtotal = base_fare + distance_fare + time_fare

    # Apply surge
    subtotal *= trip.surge_multiplier

    # Apply promotions/discounts
    subtotal -= apply_promotions(trip.rider, subtotal)

    # Tolls, airport fees, etc.
    subtotal += trip.additional_fees

    return max(subtotal, minimum_fare)
```

**Deep Dive**
- **Real-time tracking:** WebSocket connection for both rider and driver apps. Location updates published to Kafka topic, consumed by trip tracking service which pushes to connected clients. Fallback to polling if WebSocket disconnects.
- **Consistency:** Trip state machine (REQUESTED → MATCHED → DRIVER_EN_ROUTE → ARRIVED → IN_PROGRESS → COMPLETED). State transitions are atomic. Optimistic locking prevents double-matching.
- **High availability:** Stateless services behind load balancer. Redis cluster for location index (replicated). Trip DB uses Vitess or CockroachDB for horizontal scaling. Multi-region deployment with geo-routing.
- **ETA calculation:** Pre-computed routing tiles for common routes. Real-time traffic overlay from driver GPS traces. Cache ETAs for popular origin-destination pairs. Use OSRM or Valhalla for routing.

**Trade-offs**
- Push (dispatch to driver) vs Pull (drivers see available rides): Push gives platform control over matching and pricing; pull gives drivers choice but may cause hotspots
- Exact location vs Cell-based matching: Exact is more accurate but slower (more candidates); cell-based is faster but may miss optimal match
- Real-time surge vs Smoothed surge: Real-time reacts quickly but causes price volatility; smoothed is fairer but slower to respond to sudden demand

---

### 12. Design a Calendar System (Google Calendar)

**Requirements**
- Functional: Create/edit/delete events; recurring events; invitations with RSVP; shared calendars; reminders/notifications; find free time across attendees; timezone support; all-day events
- Non-functional: 99.99% availability; sync across devices in <5 seconds; support 1B users; fast conflict detection
- Scale: 1B users, 10 events/user/day = 10B events/day read, 100M new events/day

**Estimation**
```
Users:              1B total, 100M DAU
Events:             100B stored events (avg 100 per user)
New events/day:     100M → 1200/sec
Event reads/day:    10B → 115K/sec
Event size:         1 KB average
Storage:            100B × 1 KB = 100 TB
Recurring events:   10% of events, expand on read
```

**High-Level Design**
```
┌──────────────────────────────────────────────────────┐
│  Clients (Web, iOS, Android, Desktop)                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                │
│  │ Web App │ │iOS App  │ │ Android │                │
│  └────┬────┘ └────┬────┘ └────┬────┘                │
│       │           │           │                      │
│       ▼           ▼           ▼                      │
│  ┌─────────────────────────────────────┐            │
│  │     Sync Engine (per device)        │            │
│  │  - Local DB (SQLite/IndexedDB)      │            │
│  │  - Conflict resolution              │            │
│  │  - Offline support                  │            │
│  └─────────────────────────────────────┘            │
└──────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   API Gateway                        │
└───────────┬─────────────────────────────┬───────────┘
            │                             │
            ▼                             ▼
┌───────────────────┐         ┌───────────────────────┐
│   Event Service   │         │  Calendar Service     │
│  - CRUD events    │         │  - Calendar mgmt      │
│  - Recurrence     │         │  - Sharing/ACL        │
│  - Reminders      │         │  - Subscriptions      │
└─────────┬─────────┘         └───────────┬───────────┘
          │                               │
          ▼                               ▼
┌───────────────────┐         ┌───────────────────────┐
│ Event Store       │         │  Calendar Store       │
│ (sharded by       │         │  (PostgreSQL)         │
│  user_id)         │         │                       │
└───────────────────┘         └───────────────────────┘

┌───────────────────┐         ┌───────────────────────┐
│ Notification Svc  │         │  Search Service       │
│ - Email/Push      │         │  (Elasticsearch)      │
│ - Reminder queue  │         │                       │
└───────────────────┘         └───────────────────────┘
```

**Key Components**

*Data Model:*
```sql
-- Calendars
calendars:
  calendar_id (PK) | owner_id | name | timezone | color | visibility

-- Calendar sharing
calendar_shares:
  calendar_id | user_id | permission (owner/editor/viewer)

-- Events (single and recurring master)
events:
  event_id (PK) | calendar_id | user_id | title | description
  | start_time | end_time | timezone | location
  | recurrence_rule | recurrence_end | is_all_day
  | created_at | updated_at | etag

-- Recurring event exceptions/modifications
event_exceptions:
  event_id | original_start_time | modified_event (JSON) | is_deleted

-- Attendees
attendees:
  event_id | user_id | email | response_status (yes/no/maybe/pending)
  | is_organizer | is_optional

-- Reminders
reminders:
  reminder_id | event_id | user_id | minutes_before | method (email/push/sms)
```

**Recurring Event Handling (RFC 5545 / iCal):**
```python
class RecurrenceRule:
    """Parse and expand RRULE format"""
    # Example: RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20251231T235959Z

    def __init__(self, rrule_string):
        self.freq = None       # DAILY, WEEKLY, MONTHLY, YEARLY
        self.interval = 1      # Every N freq units
        self.byday = []        # MO, TU, WE, etc.
        self.bymonthday = []   # 1-31
        self.bymonth = []      # 1-12
        self.until = None      # End date
        self.count = None      # Max occurrences
        self._parse(rrule_string)

    def expand(self, start_time, range_start, range_end, exceptions=None):
        """Generate all occurrences within the given time range"""
        exceptions = exceptions or {}
        occurrences = []
        current = start_time
        count = 0

        while current <= range_end:
            if self.until and current > self.until:
                break
            if self.count and count >= self.count:
                break

            if current >= range_start:
                original_start = current
                if original_start in exceptions:
                    exc = exceptions[original_start]
                    if not exc.is_deleted:
                        # Modified instance
                        occurrences.append(exc.modified_event)
                else:
                    # Regular instance
                    occurrences.append(self._create_instance(current))

            current = self._next_occurrence(current)
            count += 1

        return occurrences

    def _next_occurrence(self, current):
        if self.freq == 'DAILY':
            return current + timedelta(days=self.interval)
        elif self.freq == 'WEEKLY':
            # Handle BYDAY (e.g., MO,WE,FR)
            return self._next_weekly(current)
        elif self.freq == 'MONTHLY':
            return self._next_monthly(current)
        elif self.freq == 'YEARLY':
            return current.replace(year=current.year + self.interval)
```

**Event Instance Expansion on Query:**
```python
def get_events_in_range(user_id, calendar_ids, start, end):
    events = []

    # 1. Get non-recurring events in range
    simple_events = db.query("""
        SELECT * FROM events
        WHERE calendar_id IN :calendar_ids
        AND recurrence_rule IS NULL
        AND start_time < :end AND end_time > :start
    """, calendar_ids=calendar_ids, start=start, end=end)
    events.extend(simple_events)

    # 2. Get recurring event masters that might have instances in range
    recurring_masters = db.query("""
        SELECT * FROM events
        WHERE calendar_id IN :calendar_ids
        AND recurrence_rule IS NOT NULL
        AND start_time < :end
        AND (recurrence_end IS NULL OR recurrence_end > :start)
    """, calendar_ids=calendar_ids, start=start, end=end)

    # 3. Expand each recurring event
    for master in recurring_masters:
        exceptions = get_exceptions(master.event_id)
        rule = RecurrenceRule(master.recurrence_rule)
        instances = rule.expand(master.start_time, start, end, exceptions)
        events.extend(instances)

    # 4. Sort by start time
    events.sort(key=lambda e: e.start_time)
    return events
```

**Free/Busy Query (Find Available Time):**
```python
class FreeBusyService:
    def find_free_slots(self, attendee_ids, date, duration_minutes,
                        working_hours=(9, 17)):
        """Find available time slots when all attendees are free"""
        busy_intervals = []

        # Collect busy times for all attendees
        for user_id in attendee_ids:
            calendars = get_user_calendars(user_id, include_shared=True)
            events = get_events_in_range(
                user_id, calendars,
                start=date.start_of_day(),
                end=date.end_of_day()
            )
            for event in events:
                if event.show_as == 'busy':
                    busy_intervals.append((event.start_time, event.end_time))

        # Merge overlapping intervals
        merged = merge_intervals(sorted(busy_intervals))

        # Find gaps that fit the required duration
        free_slots = []
        day_start = date.replace(hour=working_hours[0])
        day_end = date.replace(hour=working_hours[1])

        current = day_start
        for busy_start, busy_end in merged:
            if current < busy_start:
                gap_minutes = (busy_start - current).total_seconds() / 60
                if gap_minutes >= duration_minutes:
                    free_slots.append((current, busy_start))
            current = max(current, busy_end)

        # Check time after last busy period
        if current < day_end:
            gap_minutes = (day_end - current).total_seconds() / 60
            if gap_minutes >= duration_minutes:
                free_slots.append((current, day_end))

        return free_slots

def merge_intervals(intervals):
    """Merge overlapping time intervals"""
    if not intervals:
        return []
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
```

**Sync Protocol (Incremental Sync):**
```python
class CalendarSyncService:
    def sync(self, user_id, device_id, last_sync_token):
        """Return changes since last sync"""
        if last_sync_token is None:
            # Full sync - return all events
            events = get_all_user_events(user_id)
            new_token = generate_sync_token(user_id)
            return {'events': events, 'sync_token': new_token, 'full_sync': True}

        # Incremental sync - return only changes
        last_sync_time = decode_sync_token(last_sync_token)

        changes = db.query("""
            SELECT event_id, updated_at, is_deleted
            FROM events
            WHERE user_id = :user_id
            AND updated_at > :last_sync
            ORDER BY updated_at
        """, user_id=user_id, last_sync=last_sync_time)

        updated_events = []
        deleted_event_ids = []

        for change in changes:
            if change.is_deleted:
                deleted_event_ids.append(change.event_id)
            else:
                updated_events.append(get_event(change.event_id))

        new_token = generate_sync_token(user_id)
        return {
            'updated': updated_events,
            'deleted': deleted_event_ids,
            'sync_token': new_token,
            'full_sync': False
        }
```

**Conflict Resolution (Last-Write-Wins with Version):**
```python
def update_event(event_id, updates, client_etag):
    """Update event with optimistic concurrency control"""
    current = db.get_event(event_id)

    if current.etag != client_etag:
        # Conflict detected
        raise ConflictError(
            message="Event was modified by another client",
            current_event=current
        )

    new_etag = generate_etag()
    updates['etag'] = new_etag
    updates['updated_at'] = now()

    db.update_event(event_id, updates)

    # Notify other devices of this user
    push_sync_notification(current.user_id, event_id)

    # Notify attendees if significant change
    if significant_change(current, updates):
        notify_attendees(event_id, updates)

    return new_etag
```

**Deep Dive**
- **Timezone handling:** Store all times in UTC with IANA timezone identifier. Convert to user's timezone on display. Recurring events store the original timezone — "every Monday 9am Pacific" stays correct even when user travels.
- **Reminders at scale:** Reminder queue partitioned by fire time (minute buckets). Worker processes reminders for current minute, sends push/email. Handle clock skew with small buffer window.
- **Invitation flow:** Create event → send invite email → attendee clicks link → update response status → notify organizer. Support external attendees (non-users) via email-only flow.
- **Sharding strategy:** Shard events by user_id for single-user queries. For shared calendar queries, fan-out to relevant shards or maintain denormalized view.

**Trade-offs**
- Store expanded instances vs Expand on read: Storing is faster to query but wastes storage and complicates edits; expand on read is flexible but slower for long ranges
- Push sync vs Pull sync: Push (WebSocket) is real-time but requires connection management; pull (polling) is simpler but higher latency
- Single event store vs Per-user store: Single is simpler for shared calendars; per-user is faster for personal calendar but requires fan-out for shared

---

### 13. Design a Payment System (Stripe/PayPal)

**Requirements**
- Functional: Process payments (credit card, bank transfer, wallets); handle refunds; support multiple currencies; recurring billing/subscriptions; payouts to merchants; fraud detection; PCI DSS compliance
- Non-functional: 99.999% availability for payment processing; exactly-once payment semantics; <500ms payment latency; support $1B/day transaction volume
- Scale: 10M transactions/day, $1B daily volume, 100K merchants

**Estimation**
```
Transactions/day:    10M → 115/sec avg, 500/sec peak
Transaction size:    $100 average
Daily volume:        $1B
Storage per txn:     2 KB (request + response + audit log)
Storage/year:        10M × 2 KB × 365 = 7 TB
Ledger entries:      2-4 per transaction (double-entry) = 40M/day
```

**High-Level Design**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Merchant   │    │  Consumer   │    │   Mobile    │
│   Website   │    │    App      │    │   Wallet    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────┐
│                    API Gateway                       │
│  (TLS termination, auth, rate limiting, idempotency)│
└─────────────────────────┬───────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Payment    │   │   Wallet    │   │   Payout    │
│  Service    │   │   Service   │   │   Service   │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Risk &    │   │   Ledger    │   │   Account   │
│   Fraud     │   │   Service   │   │   Service   │
└──────┬──────┘   └─────────────┘   └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              Payment Service Provider                │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│   │  Card   │  │  Bank   │  │  Wallet │            │
│   │ Network │  │ (ACH)   │  │ (PayPal)│            │
│   │(Visa/MC)│  │         │  │         │            │
│   └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐
│            Data Stores               │
│  ┌──────────┐  ┌──────────┐         │
│  │ Payment  │  │  Ledger  │         │
│  │    DB    │  │    DB    │         │
│  └──────────┘  └──────────┘         │
│  ┌──────────┐  ┌──────────┐         │
│  │  Event   │  │  Audit   │         │
│  │   Log    │  │   Log    │         │
│  │ (Kafka)  │  │          │         │
│  └──────────┘  └──────────┘         │
└──────────────────────────────────────┘
```

**Key Components**

*Payment State Machine:*
```
     ┌──────────────────────────────────────────────────────────────┐
     │                                                              │
     ▼                                                              │
 CREATED → PROCESSING → AUTHORIZED → CAPTURED → SETTLED            │
     │         │             │           │          │               │
     │         │             │           │          └──→ REFUNDED ──┘
     │         │             │           │                   │
     │         │             │           └──→ PARTIALLY_REFUNDED
     │         │             │
     │         │             └──→ VOIDED
     │         │
     │         └──→ DECLINED
     │
     └──→ FAILED (validation error)
```

**Idempotency for Exactly-Once Payments:**
```python
class PaymentService:
    def process_payment(self, request, idempotency_key):
        """Process payment with exactly-once semantics"""
        # 1. Check idempotency cache
        cached = self.idempotency_store.get(idempotency_key)
        if cached:
            if cached.status == 'processing':
                raise PaymentInProgressError("Payment is being processed")
            return cached.response  # Return cached result

        # 2. Lock the idempotency key
        lock_acquired = self.idempotency_store.set_if_absent(
            idempotency_key,
            {'status': 'processing', 'created_at': now()},
            ttl=86400  # 24 hours
        )
        if not lock_acquired:
            # Another request beat us
            return self.process_payment(request, idempotency_key)  # Retry

        try:
            # 3. Create payment record
            payment = self.create_payment_record(request)

            # 4. Risk assessment
            risk_score = self.risk_service.evaluate(payment)
            if risk_score > RISK_THRESHOLD:
                payment.status = 'DECLINED'
                payment.decline_reason = 'high_risk'
                self.save_and_cache(payment, idempotency_key)
                return PaymentResponse(payment)

            # 5. Process with payment processor
            processor_response = self.payment_processor.authorize(payment)

            # 6. Update payment status
            if processor_response.approved:
                payment.status = 'AUTHORIZED'
                payment.authorization_code = processor_response.auth_code
            else:
                payment.status = 'DECLINED'
                payment.decline_reason = processor_response.decline_code

            # 7. Save and cache result
            self.save_and_cache(payment, idempotency_key)

            # 8. Emit event for downstream services
            self.event_bus.publish('payment.processed', payment)

            return PaymentResponse(payment)

        except Exception as e:
            # Mark idempotency key as failed (allow retry)
            self.idempotency_store.delete(idempotency_key)
            raise

    def save_and_cache(self, payment, idempotency_key):
        self.db.save(payment)
        self.idempotency_store.set(
            idempotency_key,
            {'status': 'completed', 'response': payment.to_dict()},
            ttl=86400
        )
```

**Double-Entry Ledger:**
```python
class LedgerService:
    def record_payment(self, payment):
        """Record payment using double-entry bookkeeping"""
        entries = []

        # Debit: Customer's liability decreases (they owe less)
        # Credit: Merchant's receivable increases (they're owed more)

        # Entry 1: Debit Cash/Receivables, Credit Revenue
        entries.append(LedgerEntry(
            transaction_id=payment.id,
            account_id=self.get_cash_account(),
            entry_type='DEBIT',
            amount=payment.amount,
            currency=payment.currency,
            timestamp=now()
        ))

        entries.append(LedgerEntry(
            transaction_id=payment.id,
            account_id=payment.merchant_account_id,
            entry_type='CREDIT',
            amount=payment.amount,
            currency=payment.currency,
            timestamp=now()
        ))

        # Entry 2: Record platform fee
        if payment.platform_fee > 0:
            entries.append(LedgerEntry(
                transaction_id=payment.id,
                account_id=payment.merchant_account_id,
                entry_type='DEBIT',
                amount=payment.platform_fee,
                currency=payment.currency
            ))
            entries.append(LedgerEntry(
                transaction_id=payment.id,
                account_id=self.get_platform_revenue_account(),
                entry_type='CREDIT',
                amount=payment.platform_fee,
                currency=payment.currency
            ))

        # Atomic insert of all entries
        self.db.batch_insert(entries)

        # Verify debits = credits (invariant check)
        self.verify_transaction_balance(payment.id)

    def get_account_balance(self, account_id, as_of=None):
        """Calculate account balance from ledger entries"""
        as_of = as_of or now()
        credits = self.db.sum("""
            SELECT SUM(amount) FROM ledger_entries
            WHERE account_id = :account_id
            AND entry_type = 'CREDIT'
            AND timestamp <= :as_of
        """, account_id=account_id, as_of=as_of)

        debits = self.db.sum("""
            SELECT SUM(amount) FROM ledger_entries
            WHERE account_id = :account_id
            AND entry_type = 'DEBIT'
            AND timestamp <= :as_of
        """, account_id=account_id, as_of=as_of)

        return credits - debits  # For liability/revenue accounts
```

**Fraud Detection (Real-time Scoring):**
```python
class FraudDetectionService:
    def evaluate(self, payment):
        """Real-time fraud scoring"""
        signals = []

        # 1. Velocity checks
        recent_txns = self.get_recent_transactions(
            payment.card_fingerprint, hours=24
        )
        signals.append(('velocity_24h', len(recent_txns)))
        signals.append(('amount_24h', sum(t.amount for t in recent_txns)))

        # 2. Geolocation
        ip_location = self.geoip.lookup(payment.ip_address)
        card_country = payment.card_country
        signals.append(('geo_mismatch', ip_location.country != card_country))

        # 3. Device fingerprint
        device_score = self.device_intelligence.score(payment.device_id)
        signals.append(('device_risk', device_score))

        # 4. Behavioral analysis
        user_history = self.get_user_history(payment.user_id)
        signals.append(('first_purchase', len(user_history) == 0))
        signals.append(('unusual_amount',
            payment.amount > user_history.avg_amount * 3))

        # 5. Card BIN analysis
        bin_info = self.bin_database.lookup(payment.card_bin)
        signals.append(('prepaid_card', bin_info.is_prepaid))
        signals.append(('high_risk_country', bin_info.country in HIGH_RISK))

        # 6. ML model prediction
        ml_score = self.fraud_model.predict(signals)
        signals.append(('ml_score', ml_score))

        # Combine signals into final score
        final_score = self.calculate_final_score(signals)

        # Store for model training
        self.log_evaluation(payment.id, signals, final_score)

        return FraudResult(
            score=final_score,
            signals=signals,
            action=self.recommend_action(final_score)
        )

    def recommend_action(self, score):
        if score < 30:
            return 'APPROVE'
        elif score < 70:
            return 'REVIEW'  # Manual review or 3DS challenge
        else:
            return 'DECLINE'
```

**Retry Logic with Exponential Backoff:**
```python
class PaymentRetryHandler:
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1  # seconds

    async def process_with_retry(self, payment):
        """Retry failed payments with exponential backoff"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await self.payment_processor.process(payment)
                return result
            except RetryableError as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # 1, 2, 4 seconds
                    delay += random.uniform(0, 1)  # Jitter
                    await asyncio.sleep(delay)
                    continue
            except NonRetryableError as e:
                # Don't retry: invalid card, insufficient funds, fraud
                raise

        raise MaxRetriesExceeded(last_error)
```

**Reconciliation System:**
```python
class ReconciliationService:
    def daily_reconciliation(self, date):
        """Reconcile internal records with processor settlements"""
        # 1. Get our internal transactions
        internal_txns = self.db.query("""
            SELECT * FROM payments
            WHERE DATE(created_at) = :date
            AND status IN ('CAPTURED', 'SETTLED')
        """, date=date)
        internal_by_id = {t.processor_txn_id: t for t in internal_txns}

        # 2. Get processor settlement report
        processor_txns = self.processor.get_settlement_report(date)
        processor_by_id = {t.id: t for t in processor_txns}

        # 3. Find discrepancies
        discrepancies = []

        # Transactions in our system but not in processor
        for txn_id, our_txn in internal_by_id.items():
            if txn_id not in processor_by_id:
                discrepancies.append({
                    'type': 'MISSING_IN_PROCESSOR',
                    'transaction': our_txn
                })
            else:
                proc_txn = processor_by_id[txn_id]
                if our_txn.amount != proc_txn.amount:
                    discrepancies.append({
                        'type': 'AMOUNT_MISMATCH',
                        'internal': our_txn,
                        'processor': proc_txn
                    })

        # Transactions in processor but not in our system
        for txn_id, proc_txn in processor_by_id.items():
            if txn_id not in internal_by_id:
                discrepancies.append({
                    'type': 'MISSING_IN_INTERNAL',
                    'transaction': proc_txn
                })

        # 4. Generate report and alerts
        if discrepancies:
            self.alert_finance_team(discrepancies)

        return ReconciliationReport(
            date=date,
            internal_count=len(internal_txns),
            processor_count=len(processor_txns),
            discrepancies=discrepancies
        )
```

**PCI DSS Compliance Architecture:**
```
┌────────────────────────────────────────────────────────────────┐
│                     PCI DSS Scope Boundary                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Cardholder Data Environment               │  │
│  │                                                          │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │  │
│  │  │   Card      │    │   Token     │    │   HSM       │  │  │
│  │  │  Capture    │───▶│   Vault     │───▶│ (encryption)│  │  │
│  │  │  (iframe)   │    │             │    │             │  │  │
│  │  └─────────────┘    └──────┬──────┘    └─────────────┘  │  │
│  │                            │                             │  │
│  │                            ▼                             │  │
│  │                     ┌─────────────┐                      │  │
│  │                     │   Token     │                      │  │
│  │                     │ (e.g., tok_│                      │  │
│  │                     │  abc123)   │                      │  │
│  │                     └─────────────┘                      │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                               │
                               │ Token only (no card data)
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                   Non-PCI Environment                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Payment    │    │   Order     │    │  Merchant   │        │
│  │  Service    │    │   Service   │    │   Portal    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
│  These services only see tokens, never raw card numbers        │
└────────────────────────────────────────────────────────────────┘
```

**Deep Dive**
- **Exactly-once semantics:** Idempotency keys stored in Redis with TTL. Before processing, check if key exists. If in-progress, wait and return. If completed, return cached result. If not exists, lock and process. Handle crashes by allowing retry after lock TTL.
- **Multi-currency:** Store amounts in smallest unit (cents) with currency code. Use exchange rate service for conversion. Lock exchange rate at quote time for consistency. Settlement in merchant's preferred currency.
- **Subscription billing:** Scheduler triggers recurring charges. Retry failed charges with exponential backoff over 7 days. Notify customer of failures. Dunning management: email → SMS → account suspension.
- **Disaster recovery:** Active-active across regions. Database with synchronous replication. Payment requests include region affinity. On region failure, DNS failover routes to healthy region.

**Trade-offs**
- Sync vs Async payment processing: Sync is simpler and gives immediate response; async handles higher throughput but complicates client experience
- Token vault in-house vs Third-party (Stripe, Braintree): In-house gives more control but requires PCI Level 1 compliance; third-party reduces scope but adds dependency
- Eventual vs Strong consistency for balance: Strong prevents overdraft but limits throughput; eventual allows higher throughput but needs overdraft handling

---

### 14. Design a Distributed Lock Service (Redlock/Chubby)

**Requirements**
- Functional: Acquire/release locks by name; lock with TTL (auto-release); blocking and non-blocking acquire; lock extension (renewal); fencing tokens to prevent stale clients
- Non-functional: High availability (survive node failures); mutual exclusion guarantee; low latency (<10ms acquire); prevent split-brain; handle clock skew
- Scale: 100K locks, 10K acquire/release per second, 5 nodes for fault tolerance

**Estimation**
```
Lock operations:    10K/sec acquire + 10K/sec release = 20K ops/sec
Active locks:       100K × 100 bytes = 10 MB state
Replication:        5 nodes, quorum = 3
Lock TTL:           30 seconds typical, renewal every 10 seconds
Fencing tokens:     64-bit monotonic counter per lock
```

**High-Level Design**
```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │Client 1 │  │Client 2 │  │Client 3 │  │Client N │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
└───────┼───────────┼───────────┼───────────┼────────────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Lock Service Cluster                          │
│                                                                  │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │
│   │ Node 1  │   │ Node 2  │   │ Node 3  │   │ Node 4  │  ...   │
│   │┌───────┐│   │┌───────┐│   │┌───────┐│   │┌───────┐│        │
│   ││ Locks ││   ││ Locks ││   ││ Locks ││   ││ Locks ││        │
│   │└───────┘│   │└───────┘│   │└───────┘│   │└───────┘│        │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘        │
│                                                                  │
│   Consensus: Raft (single leader) OR Redlock (multi-master)     │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components**

*Lock Data Structure:*
```python
@dataclass
class Lock:
    name: str                    # Lock identifier
    owner: str                   # Client ID holding the lock
    token: int                   # Fencing token (monotonic)
    acquired_at: float           # Timestamp when acquired
    ttl_ms: int                  # Time-to-live in milliseconds

    def is_expired(self):
        return time.time() * 1000 > self.acquired_at + self.ttl_ms

    def remaining_ttl(self):
        return max(0, (self.acquired_at + self.ttl_ms) - time.time() * 1000)
```

**Single-Node Lock Manager:**
```python
class LockManager:
    def __init__(self):
        self.locks = {}           # name -> Lock
        self.token_counter = 0    # Monotonic fencing token generator
        self.lock = threading.Lock()

    def acquire(self, lock_name, client_id, ttl_ms=30000):
        """Try to acquire lock, return (success, token, ttl_remaining)"""
        with self.lock:
            current = self.locks.get(lock_name)

            # Check if lock exists and is not expired
            if current and not current.is_expired():
                if current.owner == client_id:
                    # Re-entrant: extend TTL, return same token
                    current.acquired_at = time.time() * 1000
                    current.ttl_ms = ttl_ms
                    return True, current.token, ttl_ms
                else:
                    # Lock held by another client
                    return False, None, current.remaining_ttl()

            # Lock available - acquire it
            self.token_counter += 1
            new_lock = Lock(
                name=lock_name,
                owner=client_id,
                token=self.token_counter,
                acquired_at=time.time() * 1000,
                ttl_ms=ttl_ms
            )
            self.locks[lock_name] = new_lock
            return True, new_lock.token, ttl_ms

    def release(self, lock_name, client_id, token):
        """Release lock only if caller owns it with correct token"""
        with self.lock:
            current = self.locks.get(lock_name)
            if not current:
                return True  # Already released

            if current.owner != client_id:
                return False  # Not the owner

            if current.token != token:
                return False  # Stale token (lock was re-acquired)

            del self.locks[lock_name]
            return True

    def extend(self, lock_name, client_id, token, ttl_ms):
        """Extend lock TTL if caller still owns it"""
        with self.lock:
            current = self.locks.get(lock_name)
            if not current or current.owner != client_id or current.token != token:
                return False, 0

            if current.is_expired():
                return False, 0  # Too late, lock expired

            current.acquired_at = time.time() * 1000
            current.ttl_ms = ttl_ms
            return True, ttl_ms
```

**Redlock Algorithm (Distributed, Multi-Master):**
```python
class RedlockClient:
    """
    Redlock: Acquire lock on majority of independent Redis nodes.
    Tolerates up to (N-1)/2 node failures.
    """
    def __init__(self, nodes, quorum=None):
        self.nodes = nodes  # List of Redis connections
        self.quorum = quorum or (len(nodes) // 2 + 1)
        self.clock_drift_factor = 0.01  # 1% clock drift allowance

    def acquire(self, lock_name, ttl_ms=30000):
        """
        Try to acquire lock on majority of nodes.
        Returns (success, token, valid_until) or (False, None, None)
        """
        client_id = str(uuid.uuid4())
        start_time = time.time() * 1000

        # Try to acquire on all nodes
        acquired_count = 0
        for node in self.nodes:
            try:
                # SET lock_name client_id NX PX ttl_ms
                if node.set(lock_name, client_id, nx=True, px=ttl_ms):
                    acquired_count += 1
            except Exception:
                continue  # Node unavailable, skip

        # Calculate elapsed time and remaining validity
        elapsed = time.time() * 1000 - start_time
        drift = ttl_ms * self.clock_drift_factor + 2  # Clock drift allowance
        validity = ttl_ms - elapsed - drift

        # Check if we got quorum and lock is still valid
        if acquired_count >= self.quorum and validity > 0:
            return True, client_id, start_time + validity

        # Failed to get quorum - release all acquired locks
        self._release_all(lock_name, client_id)
        return False, None, None

    def release(self, lock_name, client_id):
        """Release lock on all nodes"""
        self._release_all(lock_name, client_id)

    def _release_all(self, lock_name, client_id):
        """Release lock on all nodes (only if we own it)"""
        # Lua script: atomic check-and-delete
        release_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        for node in self.nodes:
            try:
                node.eval(release_script, 1, lock_name, client_id)
            except Exception:
                continue

    def acquire_with_retry(self, lock_name, ttl_ms=30000,
                           max_retries=3, retry_delay_ms=200):
        """Acquire with exponential backoff retry"""
        for attempt in range(max_retries):
            success, token, valid_until = self.acquire(lock_name, ttl_ms)
            if success:
                return success, token, valid_until

            # Random delay to avoid thundering herd
            delay = retry_delay_ms * (2 ** attempt) + random.randint(0, 100)
            time.sleep(delay / 1000)

        return False, None, None
```

**Fencing Tokens (Prevent Stale Client Writes):**
```python
class FencedResource:
    """
    Resource that rejects operations from stale lock holders.
    Fencing token is monotonically increasing - higher token wins.
    """
    def __init__(self):
        self.last_token = 0
        self.lock = threading.Lock()

    def write(self, data, fencing_token):
        """
        Write data only if fencing_token is >= last seen token.
        Prevents writes from clients whose lock expired and was re-acquired.
        """
        with self.lock:
            if fencing_token < self.last_token:
                raise StaleTokenError(
                    f"Token {fencing_token} is stale, current is {self.last_token}"
                )
            self.last_token = fencing_token
            self._do_write(data)
            return True

# Usage pattern:
# 1. Acquire lock, get fencing token
# 2. Pass fencing token to all protected resources
# 3. Resources reject operations with old tokens

def safe_critical_section(lock_service, resource, lock_name):
    success, token, valid_until = lock_service.acquire(lock_name)
    if not success:
        raise LockNotAcquiredError()

    try:
        # Token protects against GC pauses, network delays, etc.
        resource.write({"data": "value"}, fencing_token=token)
    finally:
        lock_service.release(lock_name, token)
```

**Raft-Based Lock Service (Consensus Approach):**
```python
class RaftLockService:
    """
    Lock service using Raft consensus (like Chubby, etcd, ZooKeeper).
    Single leader handles all requests - provides linearizable operations.
    """
    def __init__(self, raft_cluster):
        self.raft = raft_cluster  # Raft consensus module
        self.locks = {}           # Replicated state machine
        self.sessions = {}        # Client sessions with keepalive

    def acquire(self, session_id, lock_name, ttl_ms):
        """Acquire lock - must go through Raft log"""
        if not self.raft.is_leader():
            # Redirect to leader
            return self.raft.get_leader().acquire(session_id, lock_name, ttl_ms)

        # Create log entry
        entry = {
            'type': 'ACQUIRE',
            'session_id': session_id,
            'lock_name': lock_name,
            'ttl_ms': ttl_ms,
            'timestamp': time.time()
        }

        # Replicate through Raft (blocks until committed)
        result = self.raft.replicate(entry)
        return result

    def apply(self, entry):
        """Apply committed log entry to state machine"""
        if entry['type'] == 'ACQUIRE':
            return self._apply_acquire(entry)
        elif entry['type'] == 'RELEASE':
            return self._apply_release(entry)
        elif entry['type'] == 'SESSION_EXPIRE':
            return self._apply_session_expire(entry)

    def _apply_acquire(self, entry):
        lock_name = entry['lock_name']
        session_id = entry['session_id']

        current = self.locks.get(lock_name)
        if current and not current.is_expired():
            if current.session_id == session_id:
                # Extend existing lock
                current.ttl_ms = entry['ttl_ms']
                current.acquired_at = entry['timestamp']
                return True, current.token
            return False, None  # Lock held by another session

        # Grant new lock
        token = self._next_token()
        self.locks[lock_name] = Lock(
            name=lock_name,
            session_id=session_id,
            token=token,
            acquired_at=entry['timestamp'],
            ttl_ms=entry['ttl_ms']
        )
        return True, token
```

**Lock Client with Auto-Renewal:**
```python
class DistributedLockClient:
    def __init__(self, lock_service, renewal_interval_ms=10000):
        self.lock_service = lock_service
        self.renewal_interval = renewal_interval_ms
        self.active_locks = {}  # lock_name -> (token, renewal_thread)

    def acquire(self, lock_name, ttl_ms=30000, blocking=True, timeout=None):
        """Acquire lock with automatic renewal"""
        start = time.time()

        while True:
            success, token, _ = self.lock_service.acquire(lock_name, ttl_ms)

            if success:
                # Start renewal thread
                renewal_thread = threading.Thread(
                    target=self._renewal_loop,
                    args=(lock_name, token, ttl_ms),
                    daemon=True
                )
                renewal_thread.start()
                self.active_locks[lock_name] = (token, renewal_thread)
                return LockHandle(self, lock_name, token)

            if not blocking:
                return None

            if timeout and (time.time() - start) > timeout:
                raise LockTimeoutError(f"Could not acquire {lock_name}")

            time.sleep(0.1)  # Brief sleep before retry

    def _renewal_loop(self, lock_name, token, ttl_ms):
        """Background thread to renew lock before expiry"""
        while lock_name in self.active_locks:
            time.sleep(self.renewal_interval / 1000)

            if lock_name not in self.active_locks:
                break

            success, _ = self.lock_service.extend(lock_name, token, ttl_ms)
            if not success:
                # Lock lost - notify application
                self._on_lock_lost(lock_name)
                break

    def release(self, lock_name, token):
        """Release lock and stop renewal"""
        if lock_name in self.active_locks:
            del self.active_locks[lock_name]
        self.lock_service.release(lock_name, token)

class LockHandle:
    """Context manager for automatic lock release"""
    def __init__(self, client, lock_name, token):
        self.client = client
        self.lock_name = lock_name
        self.token = token

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.release(self.lock_name, self.token)
        return False

# Usage:
# with lock_client.acquire("resource:123") as lock:
#     do_critical_section()
```

**Deep Dive**
- **Clock synchronization:** Redlock assumes bounded clock drift. Use NTP with monitoring. If clock jumps, lock validity may be affected. Conservative TTL helps.
- **Split-brain prevention:** Quorum ensures at most one client holds lock. With 5 nodes, tolerates 2 failures. With 3 nodes, tolerates 1.
- **GC pauses:** Client may pause during critical section, lock expires, another client acquires. Fencing tokens protect the resource by rejecting stale writes.
- **Liveness:** Use TTL to ensure lock is eventually released even if client crashes. Renewal threads extend TTL for long operations.

**Trade-offs**
- Redlock vs Raft-based: Redlock is simpler (no leader election) but weaker guarantees; Raft provides linearizability but requires leader
- Short TTL vs Long TTL: Short TTL recovers faster from failures but needs more renewals; long TTL is more resilient to network blips but slower recovery
- Blocking vs Non-blocking acquire: Blocking is simpler for caller but can cause thread starvation; non-blocking requires caller to handle retry

---

### 15. Design a Proximity Service (Yelp/Find Nearby)

**Requirements**
- Functional: Find businesses within radius of location; filter by category, rating, price; return sorted by distance or relevance; support 200M businesses globally
- Non-functional: <100ms latency for nearby search; support 100K QPS; real-time updates for new businesses; global coverage
- Scale: 200M businesses, 100K searches/sec, 1K business updates/sec

**Estimation**
```
Businesses:         200M total, 100 bytes each = 20 GB
Searches:           100K/sec
Business updates:   1K/sec (new, edit, delete)
Geospatial index:   200M points, ~30 GB with indexing overhead
Typical query:      5km radius, return top 20 results
```

**High-Level Design**
```
┌─────────────────────────────────────────────────────────────────┐
│                          Clients                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway                                │
│              (rate limiting, auth, geo-routing)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│    Search     │  │   Business    │  │   Location    │
│   Service     │  │    Service    │  │   Service     │
│ (nearby query)│  │  (CRUD ops)   │  │ (geocoding)   │
└───────┬───────┘  └───────┬───────┘  └───────────────┘
        │                  │
        ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Geospatial Index                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │  Geohash    │  │   QuadTree  │  │   Google    │             │
│   │  (Redis)    │  │  (in-memory)│  │    S2       │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Business Database                             │
│                (PostgreSQL with PostGIS)                         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components**

*Approach 1: Geohash-Based Indexing:*
```python
class GeohashIndex:
    """
    Geohash divides Earth into grid cells with hierarchical precision.
    Nearby points share common prefix in their geohash.

    Precision levels:
    1: ±2500 km  (5 bits)
    4: ±20 km    (20 bits)
    6: ±0.6 km   (30 bits)
    8: ±19 m     (40 bits)
    """

    BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'

    def encode(self, lat, lng, precision=6):
        """Encode lat/lng to geohash string"""
        lat_range = (-90.0, 90.0)
        lng_range = (-180.0, 180.0)
        geohash = []
        bits = 0
        bit = 0
        ch = 0
        even = True

        while len(geohash) < precision:
            if even:  # Longitude
                mid = (lng_range[0] + lng_range[1]) / 2
                if lng >= mid:
                    ch |= (1 << (4 - bit))
                    lng_range = (mid, lng_range[1])
                else:
                    lng_range = (lng_range[0], mid)
            else:  # Latitude
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat >= mid:
                    ch |= (1 << (4 - bit))
                    lat_range = (mid, lat_range[1])
                else:
                    lat_range = (lat_range[0], mid)

            even = not even
            bit += 1

            if bit == 5:
                geohash.append(self.BASE32[ch])
                bit = 0
                ch = 0

        return ''.join(geohash)

    def get_neighbors(self, geohash):
        """Get 8 neighboring geohash cells (for edge cases)"""
        # Returns adjacent cells: N, NE, E, SE, S, SW, W, NW
        # Implementation handles wraparound at edges
        neighbors = []
        for dlat in [-1, 0, 1]:
            for dlng in [-1, 0, 1]:
                if dlat == 0 and dlng == 0:
                    continue
                neighbors.append(self._neighbor(geohash, dlat, dlng))
        return neighbors

class GeohashProximitySearch:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.geohash = GeohashIndex()

    def add_business(self, business_id, lat, lng, data):
        """Index business by geohash"""
        # Use precision 6 (~600m cells) for nearby searches
        gh = self.geohash.encode(lat, lng, precision=6)

        # Store in Redis sorted set (score = geohash prefix for range queries)
        self.redis.geoadd("businesses:geo", lng, lat, business_id)

        # Also store by geohash prefix for fast lookup
        self.redis.sadd(f"businesses:geohash:{gh}", business_id)

        # Store business data
        self.redis.hset(f"business:{business_id}", mapping={
            'lat': lat, 'lng': lng, 'data': json.dumps(data)
        })

    def search_nearby(self, lat, lng, radius_km, limit=20):
        """Find businesses within radius"""
        # Determine geohash precision based on radius
        precision = self._radius_to_precision(radius_km)
        center_hash = self.geohash.encode(lat, lng, precision)

        # Get center cell + neighbors (9 cells total)
        cells = [center_hash] + self.geohash.get_neighbors(center_hash)

        # Collect candidate businesses from all cells
        candidates = []
        for cell in cells:
            # Get all businesses in this cell
            business_ids = self.redis.smembers(f"businesses:geohash:{cell}")
            for bid in business_ids:
                biz = self.redis.hgetall(f"business:{bid}")
                candidates.append((bid, float(biz['lat']), float(biz['lng'])))

        # Filter by exact distance and sort
        results = []
        for bid, blat, blng in candidates:
            dist = self._haversine(lat, lng, blat, blng)
            if dist <= radius_km:
                results.append((bid, dist))

        results.sort(key=lambda x: x[1])
        return results[:limit]

    def _haversine(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points in km"""
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def _radius_to_precision(self, radius_km):
        """Choose geohash precision based on search radius"""
        if radius_km > 100:
            return 3   # ~78km cells
        elif radius_km > 10:
            return 4   # ~20km cells
        elif radius_km > 1:
            return 5   # ~2.4km cells
        else:
            return 6   # ~0.6km cells
```

*Approach 2: QuadTree (In-Memory):*
```python
class QuadTree:
    """
    Recursively divide 2D space into 4 quadrants.
    Each node holds points until capacity, then splits.

    Good for: non-uniform distribution, dynamic updates
    Query time: O(log n) average
    """

    def __init__(self, boundary, capacity=4):
        self.boundary = boundary  # (x, y, width, height)
        self.capacity = capacity
        self.points = []          # [(id, x, y, data), ...]
        self.divided = False
        self.nw = self.ne = self.sw = self.se = None

    def insert(self, point_id, x, y, data=None):
        """Insert a point into the quadtree"""
        if not self._contains(x, y):
            return False

        if len(self.points) < self.capacity and not self.divided:
            self.points.append((point_id, x, y, data))
            return True

        if not self.divided:
            self._subdivide()

        # Insert into appropriate quadrant
        return (self.nw.insert(point_id, x, y, data) or
                self.ne.insert(point_id, x, y, data) or
                self.sw.insert(point_id, x, y, data) or
                self.se.insert(point_id, x, y, data))

    def _subdivide(self):
        """Split node into 4 quadrants"""
        x, y, w, h = self.boundary
        hw, hh = w / 2, h / 2

        self.nw = QuadTree((x, y + hh, hw, hh), self.capacity)
        self.ne = QuadTree((x + hw, y + hh, hw, hh), self.capacity)
        self.sw = QuadTree((x, y, hw, hh), self.capacity)
        self.se = QuadTree((x + hw, y, hw, hh), self.capacity)
        self.divided = True

        # Re-insert existing points into children
        for pid, px, py, data in self.points:
            self._insert_into_children(pid, px, py, data)
        self.points = []

    def query_radius(self, cx, cy, radius):
        """Find all points within radius of (cx, cy)"""
        results = []
        self._query_radius(cx, cy, radius, results)
        return results

    def _query_radius(self, cx, cy, radius, results):
        """Recursive radius query"""
        # Skip if this quadrant doesn't intersect the search circle
        if not self._intersects_circle(cx, cy, radius):
            return

        # Check points in this node
        for pid, px, py, data in self.points:
            dist = math.sqrt((px - cx)**2 + (py - cy)**2)
            if dist <= radius:
                results.append((pid, px, py, dist, data))

        # Recurse into children
        if self.divided:
            self.nw._query_radius(cx, cy, radius, results)
            self.ne._query_radius(cx, cy, radius, results)
            self.sw._query_radius(cx, cy, radius, results)
            self.se._query_radius(cx, cy, radius, results)

    def _intersects_circle(self, cx, cy, radius):
        """Check if this quadrant intersects the search circle"""
        x, y, w, h = self.boundary
        # Find closest point on rectangle to circle center
        closest_x = max(x, min(cx, x + w))
        closest_y = max(y, min(cy, y + h))
        dist = math.sqrt((closest_x - cx)**2 + (closest_y - cy)**2)
        return dist <= radius

    def _contains(self, x, y):
        bx, by, w, h = self.boundary
        return bx <= x < bx + w and by <= y < by + h

class QuadTreeProximityService:
    def __init__(self):
        # Cover entire world: lng [-180, 180], lat [-90, 90]
        self.tree = QuadTree((-180, -90, 360, 180), capacity=100)
        self.businesses = {}  # id -> full business data

    def add_business(self, business):
        self.businesses[business.id] = business
        # Note: QuadTree uses flat coordinates; for accuracy,
        # convert to projected coordinates or use haversine for distance
        self.tree.insert(business.id, business.lng, business.lat, None)

    def search_nearby(self, lat, lng, radius_km, filters=None, limit=20):
        # Convert km to degrees (approximate)
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km

        candidates = self.tree.query_radius(lng, lat, radius_deg)

        # Apply filters and calculate exact distance
        results = []
        for pid, px, py, _, _ in candidates:
            biz = self.businesses[pid]

            # Apply filters
            if filters:
                if not self._matches_filters(biz, filters):
                    continue

            # Calculate exact distance using haversine
            dist = self._haversine(lat, lng, biz.lat, biz.lng)
            if dist <= radius_km:
                results.append((biz, dist))

        # Sort by distance
        results.sort(key=lambda x: x[1])
        return results[:limit]
```

*Approach 3: Google S2 Cells:*
```python
class S2ProximitySearch:
    """
    S2 Geometry: Projects Earth onto a cube, then uses Hilbert curve
    for 1D ordering. Provides tight covering of arbitrary regions.

    Advantages over geohash:
    - No discontinuities at edges
    - Better coverage of polar regions
    - Variable-size cells for efficient covering
    """

    def __init__(self, db):
        self.db = db  # Database with S2 cell index

    def search_nearby(self, lat, lng, radius_km, limit=20):
        # Create S2 point for center
        center = s2.S2LatLng.FromDegrees(lat, lng).ToPoint()

        # Create spherical cap (circle on sphere)
        radius_radians = radius_km / 6371.0  # Earth radius in km
        cap = s2.S2Cap.FromCenterAngle(center, s2.S1Angle.Radians(radius_radians))

        # Get covering cells at appropriate level
        coverer = s2.S2RegionCoverer()
        coverer.set_max_cells(20)        # Limit cell count for query efficiency
        coverer.set_min_level(10)         # ~10km cells
        coverer.set_max_level(16)         # ~150m cells

        covering = coverer.GetCovering(cap)

        # Query database for each covering cell
        candidates = []
        for cell_id in covering:
            # Range query: all cells that start with this prefix
            cell_range = self._get_cell_range(cell_id)
            results = self.db.query(
                "SELECT * FROM businesses WHERE s2_cell BETWEEN ? AND ?",
                cell_range
            )
            candidates.extend(results)

        # Filter by exact distance
        results = []
        for biz in candidates:
            dist = self._haversine(lat, lng, biz.lat, biz.lng)
            if dist <= radius_km:
                results.append((biz, dist))

        results.sort(key=lambda x: x[1])
        return results[:limit]

    def add_business(self, business):
        # Calculate S2 cell at leaf level (level 30)
        point = s2.S2LatLng.FromDegrees(business.lat, business.lng)
        cell = s2.S2CellId.FromLatLng(point)

        # Store with cell ID for range queries
        self.db.insert(
            "INSERT INTO businesses (id, lat, lng, s2_cell, data) VALUES (?, ?, ?, ?, ?)",
            (business.id, business.lat, business.lng, cell.id(), business.data)
        )
```

**Sharding Strategy:**
```python
class ShardedProximityService:
    """
    Shard businesses by geographic region for horizontal scaling.
    Each shard handles a contiguous region (e.g., city, country).
    """

    def __init__(self, shards):
        # shards: {region_id: (geohash_prefix, shard_connection)}
        self.shards = shards
        self.region_index = self._build_region_index()

    def search_nearby(self, lat, lng, radius_km, limit=20):
        # Determine which shards to query
        center_geohash = encode_geohash(lat, lng, precision=2)  # ~600km
        relevant_shards = self._get_shards_for_region(center_geohash, radius_km)

        # Query all relevant shards in parallel
        with ThreadPoolExecutor() as executor:
            futures = []
            for shard in relevant_shards:
                futures.append(
                    executor.submit(shard.search_nearby, lat, lng, radius_km, limit)
                )

            # Merge results
            all_results = []
            for future in futures:
                all_results.extend(future.result())

        # Sort merged results by distance
        all_results.sort(key=lambda x: x[1])
        return all_results[:limit]

    def _get_shards_for_region(self, center_geohash, radius_km):
        """Find all shards that may contain results"""
        shards = set()
        shards.add(self.region_index[center_geohash])

        # If radius is large, include neighboring regions
        if radius_km > 50:  # Crosses region boundaries
            for neighbor in get_geohash_neighbors(center_geohash):
                if neighbor in self.region_index:
                    shards.add(self.region_index[neighbor])

        return list(shards)
```

**Deep Dive**
- **Index choice:** Geohash is simple and works well with Redis/DB range queries. QuadTree is better for in-memory with non-uniform distribution. S2 is most accurate for spherical geometry and used by Google.
- **Caching:** Cache popular location queries (city centers, airports). Use geohash as cache key. Invalidate on nearby business updates.
- **Real-time updates:** For 1K updates/sec, use write-through to update index. Batch updates for efficiency. Eventually consistent is usually acceptable.
- **Ranking:** Combine distance with rating, review count, and user preferences. Personalization based on past behavior.

**Trade-offs**
- Geohash vs QuadTree vs S2: Geohash is simplest with DB integration; QuadTree handles non-uniform distribution; S2 is most accurate but complex
- In-memory vs Database index: In-memory (QuadTree) is faster but limited by RAM; DB index (PostGIS, Redis Geo) scales better but slower
- Fixed grid vs Dynamic: Fixed grid (geohash) is simpler; dynamic (QuadTree) adapts to density but harder to distribute

---

### 16. Design a Unique ID Generator (Snowflake)

**Requirements**
- Functional: Generate globally unique 64-bit IDs; IDs should be roughly time-ordered; no coordination between generators; support 10K+ IDs per second per node
- Non-functional: High availability (no SPOF); low latency (<1ms); unique across data centers; survive clock skew
- Scale: 1000 nodes, 10M IDs/sec total, multi-datacenter

**Estimation**
```
ID rate:            10M/sec globally, 10K/sec per node
Nodes:              1000 generators
Bits available:     64 bits total
Time precision:     Millisecond (need ~41 bits for 69 years)
Sequence:           4096 per millisecond per node (12 bits)
Node ID:            1024 nodes (10 bits)
```

**High-Level Design**
```
┌─────────────────────────────────────────────────────────────────┐
│                     Snowflake ID Structure                       │
│                         (64 bits)                                │
│                                                                  │
│  ┌───┬────────────────────────┬──────────┬─────────────────┐    │
│  │ 0 │      Timestamp         │  Node ID │    Sequence     │    │
│  │   │     (41 bits)          │ (10 bits)│    (12 bits)    │    │
│  │ 1 │                        │          │                 │    │
│  │bit│   69 years of ms       │  1024    │  4096 per ms    │    │
│  └───┴────────────────────────┴──────────┴─────────────────┘    │
│                                                                  │
│  Example: 0 | 1704067200000 | 42 | 1234                         │
│  Binary:  0 | 41 bits       | 10 | 12 bits                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Deployment                                 │
│                                                              │
│   ┌───────────────┐    ┌───────────────┐                    │
│   │  Datacenter 1 │    │  Datacenter 2 │                    │
│   │ ┌───────────┐ │    │ ┌───────────┐ │                    │
│   │ │ Node 0-99 │ │    │ │Node 100-199│                    │
│   │ │ Generator │ │    │ │ Generator │ │                    │
│   │ └───────────┘ │    │ └───────────┘ │                    │
│   └───────────────┘    └───────────────┘                    │
│                                                              │
│   Node IDs assigned at deployment (static or via ZooKeeper) │
└──────────────────────────────────────────────────────────────┘
```

**Key Components**

**Snowflake ID Generator:**
```python
class SnowflakeGenerator:
    """
    Twitter Snowflake-style 64-bit ID generator.

    Bit allocation:
    - 1 bit:  Sign (always 0 for positive)
    - 41 bits: Timestamp (milliseconds since custom epoch)
    - 10 bits: Node/Machine ID (0-1023)
    - 12 bits: Sequence number (0-4095 per millisecond)

    Properties:
    - Time-ordered: IDs generated later have higher values
    - Unique: Node ID + sequence ensures uniqueness within millisecond
    - No coordination: Each node generates independently
    """

    # Custom epoch: 2020-01-01 00:00:00 UTC
    EPOCH = 1577836800000

    # Bit lengths
    TIMESTAMP_BITS = 41
    NODE_ID_BITS = 10
    SEQUENCE_BITS = 12

    # Max values
    MAX_NODE_ID = (1 << NODE_ID_BITS) - 1      # 1023
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1     # 4095

    # Bit shifts
    TIMESTAMP_SHIFT = NODE_ID_BITS + SEQUENCE_BITS  # 22
    NODE_ID_SHIFT = SEQUENCE_BITS                    # 12

    def __init__(self, node_id):
        if node_id < 0 or node_id > self.MAX_NODE_ID:
            raise ValueError(f"Node ID must be between 0 and {self.MAX_NODE_ID}")

        self.node_id = node_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def generate(self):
        """Generate next unique ID"""
        with self.lock:
            timestamp = self._current_time_ms()

            if timestamp < self.last_timestamp:
                # Clock moved backwards - this is a problem!
                raise ClockMovedBackwardsError(
                    f"Clock moved backwards by {self.last_timestamp - timestamp}ms"
                )

            if timestamp == self.last_timestamp:
                # Same millisecond - increment sequence
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE

                if self.sequence == 0:
                    # Sequence exhausted for this millisecond - wait for next ms
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                # New millisecond - reset sequence
                self.sequence = 0

            self.last_timestamp = timestamp

            # Compose the 64-bit ID
            id = ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) | \
                 (self.node_id << self.NODE_ID_SHIFT) | \
                 self.sequence

            return id

    def _current_time_ms(self):
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp):
        """Spin until clock advances to next millisecond"""
        timestamp = self._current_time_ms()
        while timestamp <= last_timestamp:
            timestamp = self._current_time_ms()
        return timestamp

    def parse(self, id):
        """Extract components from a Snowflake ID"""
        timestamp = ((id >> self.TIMESTAMP_SHIFT) & ((1 << self.TIMESTAMP_BITS) - 1))
        timestamp += self.EPOCH

        node_id = (id >> self.NODE_ID_SHIFT) & self.MAX_NODE_ID
        sequence = id & self.MAX_SEQUENCE

        return {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp / 1000),
            'node_id': node_id,
            'sequence': sequence
        }
```

**Handling Clock Skew:**
```python
class RobustSnowflakeGenerator:
    """
    Enhanced Snowflake with clock skew handling.
    """

    def __init__(self, node_id, max_clock_skew_ms=5000):
        self.node_id = node_id
        self.max_clock_skew_ms = max_clock_skew_ms
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def generate(self):
        with self.lock:
            timestamp = self._current_time_ms()

            if timestamp < self.last_timestamp:
                skew = self.last_timestamp - timestamp

                if skew <= self.max_clock_skew_ms:
                    # Small skew: wait it out
                    time.sleep(skew / 1000.0)
                    timestamp = self._current_time_ms()
                else:
                    # Large skew: something seriously wrong
                    raise ClockSkewTooLargeError(f"Clock skew of {skew}ms exceeds max")

            # Rest of generation logic...
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & SnowflakeGenerator.MAX_SEQUENCE
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            return self._compose_id(timestamp, self.node_id, self.sequence)

class LogicalClockSnowflake:
    """
    Alternative: Use logical timestamp that never goes backwards.
    Trade-off: IDs may drift from wall clock during skew.
    """

    def __init__(self, node_id):
        self.node_id = node_id
        self.sequence = 0
        self.logical_time = self._current_time_ms()
        self.lock = threading.Lock()

    def generate(self):
        with self.lock:
            wall_time = self._current_time_ms()

            # Logical time = max(wall_time, last_logical_time)
            self.logical_time = max(wall_time, self.logical_time)

            self.sequence = (self.sequence + 1) & SnowflakeGenerator.MAX_SEQUENCE
            if self.sequence == 0:
                # Force logical time forward
                self.logical_time += 1

            return self._compose_id(self.logical_time, self.node_id, self.sequence)
```

**Node ID Assignment:**
```python
class NodeIDAssigner:
    """
    Strategies for assigning unique node IDs:
    1. Static configuration (simplest, requires manual management)
    2. ZooKeeper-based (automatic, survives restarts)
    3. Database-based (simple coordination)
    """

    # Strategy 1: Static from config/environment
    @staticmethod
    def from_config():
        return int(os.environ['SNOWFLAKE_NODE_ID'])

    # Strategy 2: ZooKeeper ephemeral sequential nodes
    @staticmethod
    def from_zookeeper(zk_client, service_name):
        """
        Create ephemeral sequential node in ZooKeeper.
        Node ID = sequence number from ZK path.
        """
        path = f"/snowflake/{service_name}/nodes/node-"
        created_path = zk_client.create(
            path,
            ephemeral=True,
            sequence=True
        )
        # Extract sequence number: /snowflake/svc/nodes/node-0000000042 -> 42
        node_id = int(created_path.split('-')[-1])

        if node_id > SnowflakeGenerator.MAX_NODE_ID:
            raise TooManyNodesError(f"Node ID {node_id} exceeds max")

        return node_id

    # Strategy 3: Database with lease
    @staticmethod
    def from_database(db, hostname, lease_duration_sec=300):
        """
        Claim a node ID from database with time-based lease.
        """
        # Try to claim an existing expired lease
        result = db.execute("""
            UPDATE node_leases
            SET hostname = ?,
                lease_until = NOW() + INTERVAL ? SECOND
            WHERE lease_until < NOW()
            ORDER BY node_id
            LIMIT 1
            RETURNING node_id
        """, (hostname, lease_duration_sec))

        if result:
            return result['node_id']

        # No expired leases - create new one if under limit
        result = db.execute("""
            INSERT INTO node_leases (hostname, lease_until)
            SELECT ?, NOW() + INTERVAL ? SECOND
            WHERE (SELECT COUNT(*) FROM node_leases) < 1024
            RETURNING node_id
        """, (hostname, lease_duration_sec))

        if result:
            return result['node_id']

        raise NoNodeIDAvailableError("All 1024 node IDs are in use")
```

**Datacenter-Aware Snowflake:**
```python
class DatacenterSnowflake:
    """
    Split node ID bits between datacenter and machine.

    Bit allocation:
    - 41 bits: Timestamp
    - 5 bits:  Datacenter ID (0-31)
    - 5 bits:  Machine ID (0-31 per datacenter)
    - 12 bits: Sequence

    Total: 32 datacenters × 32 machines = 1024 nodes
    """

    DATACENTER_BITS = 5
    MACHINE_BITS = 5
    SEQUENCE_BITS = 12

    MAX_DATACENTER_ID = (1 << DATACENTER_BITS) - 1  # 31
    MAX_MACHINE_ID = (1 << MACHINE_BITS) - 1        # 31
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1          # 4095

    def __init__(self, datacenter_id, machine_id):
        if datacenter_id > self.MAX_DATACENTER_ID:
            raise ValueError(f"Datacenter ID must be <= {self.MAX_DATACENTER_ID}")
        if machine_id > self.MAX_MACHINE_ID:
            raise ValueError(f"Machine ID must be <= {self.MAX_MACHINE_ID}")

        self.datacenter_id = datacenter_id
        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def generate(self):
        with self.lock:
            timestamp = self._current_time_ms()

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            # Compose ID with datacenter and machine
            id = ((timestamp - self.EPOCH) << 22) | \
                 (self.datacenter_id << 17) | \
                 (self.machine_id << 12) | \
                 self.sequence

            return id
```

**Alternative: ULID (Lexicographically Sortable):**
```python
class ULIDGenerator:
    """
    ULID: Universally Unique Lexicographically Sortable Identifier

    Format: 26 characters, Crockford Base32 encoded
    - 48 bits: Timestamp (milliseconds, good for 10889 years)
    - 80 bits: Randomness

    Properties:
    - Lexicographically sortable (can use string comparison)
    - Case insensitive
    - No special characters (URL safe)
    - 128 bits total (same as UUID)

    Trade-off vs Snowflake:
    - ULID: No node ID needed, but randomness means tiny collision risk
    - Snowflake: Guaranteed unique, but requires node ID management
    """

    ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford Base32

    def __init__(self):
        self.last_time = 0
        self.random_bits = 0
        self.lock = threading.Lock()

    def generate(self):
        with self.lock:
            now = int(time.time() * 1000)

            if now == self.last_time:
                # Same millisecond - increment random portion
                self.random_bits += 1
                if self.random_bits > (1 << 80) - 1:
                    # Overflow - wait for next millisecond
                    while int(time.time() * 1000) == now:
                        pass
                    now = int(time.time() * 1000)
                    self.random_bits = random.getrandbits(80)
            else:
                # New millisecond - generate new random bits
                self.random_bits = random.getrandbits(80)

            self.last_time = now

            return self._encode(now, self.random_bits)

    def _encode(self, timestamp, random_bits):
        """Encode to 26-character Crockford Base32 string"""
        # 10 chars for timestamp (48 bits)
        # 16 chars for randomness (80 bits)
        result = []

        # Encode timestamp (48 bits = 10 chars × 5 bits, with 2 bits padding)
        for i in range(9, -1, -1):
            result.append(self.ENCODING[(timestamp >> (i * 5)) & 0x1F])

        # Encode randomness (80 bits = 16 chars × 5 bits)
        for i in range(15, -1, -1):
            result.append(self.ENCODING[(random_bits >> (i * 5)) & 0x1F])

        return ''.join(result)
```

**ID Generator Service:**
```python
class IDGeneratorService:
    """
    HTTP service wrapper for Snowflake generator.
    Supports batch generation for efficiency.
    """

    def __init__(self, node_id):
        self.generator = SnowflakeGenerator(node_id)
        self.batch_cache = queue.Queue(maxsize=1000)
        self._start_batch_generator()

    def _start_batch_generator(self):
        """Background thread to pre-generate IDs"""
        def generate_batch():
            while True:
                if self.batch_cache.qsize() < 500:
                    for _ in range(100):
                        try:
                            id = self.generator.generate()
                            self.batch_cache.put(id, block=False)
                        except queue.Full:
                            break
                time.sleep(0.001)

        thread = threading.Thread(target=generate_batch, daemon=True)
        thread.start()

    def get_id(self):
        """Get single ID from pre-generated cache or generate on demand"""
        try:
            return self.batch_cache.get_nowait()
        except queue.Empty:
            return self.generator.generate()

    def get_ids(self, count):
        """Get batch of IDs"""
        ids = []
        for _ in range(count):
            ids.append(self.get_id())
        return ids
```

**Deep Dive**
- **Clock synchronization:** Use NTP with monitoring. Alert if clock drifts >1 second. Consider GPS time for financial systems.
- **Sequence exhaustion:** 4096 IDs per millisecond per node = 4M IDs/sec/node. If exceeded, wait for next millisecond (adds latency).
- **ID ordering:** IDs are roughly time-ordered (same millisecond may have different node IDs interleaved). For strict ordering, use single generator or logical clocks.
- **Database considerations:** 64-bit IDs fit in BIGINT. Time-ordered IDs cause B-tree hotspots on recent inserts (use hash partitioning if problematic).

**Trade-offs**
- Snowflake vs UUID: Snowflake is 64 bits (smaller, sortable), UUID is 128 bits (no coordination, but larger and random)
- Timestamp precision: Millisecond gives 69 years; second gives 69,000 years but only 4K IDs/sec
- Node ID bits vs Sequence bits: More node bits = more machines; more sequence bits = higher throughput per machine

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
