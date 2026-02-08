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

*Data Structures:*
- `ring`: Map of hash_position → server_name
- `sorted_keys`: Sorted list of all hash positions on the ring
- `vnodes`: Number of virtual nodes per physical server (typically 100-200)

*Adding a Server:*
```
FOR i = 0 to num_virtual_nodes:
    virtual_key = server_name + ":vnode" + i
    hash_position = MD5(virtual_key) as integer
    ring[hash_position] = server_name
    INSERT hash_position into sorted_keys (maintaining sorted order)
```

*Removing a Server:*
```
FOR i = 0 to num_virtual_nodes:
    virtual_key = server_name + ":vnode" + i
    hash_position = MD5(virtual_key) as integer
    DELETE ring[hash_position]
    REMOVE hash_position from sorted_keys
```

*Finding Server for a Key:*
```
hash_position = MD5(key) as integer
index = binary_search(sorted_keys, hash_position)  // find first position >= hash
IF index reaches end of list:
    index = 0  // wrap around to first server
RETURN ring[sorted_keys[index]]
```

*Why Virtual Nodes:* Without vnodes, removing one server moves all its keys to just one neighbor. With 150 vnodes per server, keys redistribute evenly across ~150 different neighbors.

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

*Characters:* 0-9 (10) + A-Z (26) + a-z (26) = 62 characters

*Encode (number → short string):*
```
WHILE number > 0:
    remainder = number % 62
    PREPEND charset[remainder] to result
    number = number / 62 (integer division)
RETURN result

Example: 123456789 → "8M0kX"
```

*Decode (short string → number):*
```
number = 0
FOR each character in string:
    number = number × 62 + position_of(character)
RETURN number
```

*Capacity:* 7 characters = 62^7 = 3.5 trillion unique URLs

**Distributed ID Generation (Range-Based):**

*How It Works:*
```
Each server pre-allocates a range of IDs from central coordinator:
  Server 1 gets range [1 - 10000]
  Server 2 gets range [10001 - 20000]
  ...

When generating next ID:
  IF current_id is empty OR current_id >= range_end:
      Request new range from coordinator
  RETURN current_id, then increment it
```

*Benefit:* No coordination needed for each ID—only when range exhausted (~every 10K IDs)

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

**Token Bucket Rate Limiter (Atomic Redis Operation):**

*Algorithm (executed atomically in Redis):*
```
INPUT: user_key, max_tokens (e.g., 100), refill_rate (e.g., 10/sec), current_time

1. READ bucket from Redis: {tokens, last_refill_time}
   - If not exists, initialize with max_tokens

2. REFILL tokens based on elapsed time:
   elapsed_seconds = current_time - last_refill_time
   tokens_to_add = elapsed_seconds × refill_rate
   new_tokens = MIN(max_tokens, current_tokens + tokens_to_add)

3. CHECK if request allowed:
   IF new_tokens >= 1:
       new_tokens = new_tokens - 1
       SAVE {tokens: new_tokens, last_refill: current_time}
       RETURN allowed=true, remaining=new_tokens
   ELSE:
       SAVE {tokens: new_tokens, last_refill: current_time}
       RETURN allowed=false, remaining=new_tokens

4. SET key expiry to 1 hour (cleanup inactive users)
```

*Why Atomic:* Lua script runs as single Redis command—no race condition between read and write.

*Response Headers:*
```
X-RateLimit-Limit: 100           (max tokens)
X-RateLimit-Remaining: 47        (tokens left)
X-RateLimit-Reset: 1704067205    (Unix time when bucket refills)
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

*Inputs:*
- Available quality variants: [360p@800kbps, 480p@1.4Mbps, 720p@2.8Mbps, 1080p@5Mbps]
- Measured download throughput (from last segment download)
- Buffer level (seconds of video already buffered)

*Selection Logic:*
```
1. CALCULATE smoothed throughput:
   - Use exponential weighted moving average (EWMA) of recent measurements
   - Smooths out network fluctuations

2. APPLY safety margin:
   safe_bandwidth = smoothed_throughput × 0.7   (use 70% to avoid rebuffering)

3. ADJUST based on buffer level:
   IF buffer < 5 seconds:
       safe_bandwidth = safe_bandwidth × 0.5   (low buffer, be conservative)
   ELSE IF buffer > 30 seconds:
       safe_bandwidth = safe_bandwidth × 1.2   (high buffer, can try higher quality)

4. SELECT highest quality that fits:
   FOR each variant (sorted by bandwidth, lowest first):
       IF variant.bandwidth <= safe_bandwidth:
           selected = variant
   RETURN selected

Example:
  Measured throughput: 4 Mbps
  EWMA smoothed: 3.5 Mbps
  Safe bandwidth: 3.5 × 0.7 = 2.45 Mbps
  Buffer: 12 seconds (normal)
  → Select 720p (2.8 Mbps > 2.45, so pick 480p@1.4 Mbps)
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

| Factor | Points | Logic |
|--------|--------|-------|
| Domain Authority | 0-40 | PageRank or pre-computed authority score × 40 |
| URL Depth | 0-20 | 20 - (number_of_slashes × 2). Shorter paths = higher priority |
| Freshness | 0-20 | hours_since_crawl / expected_change_rate. Never crawled = 20 |
| Important Page | +10 | Bonus for homepage, sitemap, robots.txt |
| Inlink Count | 0-10 | More pages linking to it = more important |

*Queue Assignment:*
```
Score 80-100 → Queue 0 (High priority)
Score 50-79  → Queue 1 (Medium priority)
Score 20-49  → Queue 2 (Low priority)
Score 0-19   → Queue 3 (Background)
```

*URL Frontier with Politeness:*

*Data Structures:*
- `front_queues[4]`: Priority queues (high/medium/low/background)
- `back_queues{domain → queue}`: Per-domain FIFO queues
- `domain_heap`: Min-heap of (next_allowed_time, domain) for scheduling

*Adding a URL:*
```
1. Check if URL already in frontier (skip duplicates)
2. Calculate priority score
3. Assign to appropriate front queue based on score
```

*Getting Next URL (respects both priority and politeness):*
```
1. LOOK at domain_heap to find domain ready for crawling:
   - Peek at smallest (next_allowed_time, domain)
   - IF next_allowed_time > current_time: no domain ready, wait

2. POP that domain from heap
3. GET first URL from that domain's back queue
4. SCHEDULE next crawl for this domain:
   next_allowed = now + crawl_delay (from robots.txt or default 1s)
   IF more URLs waiting for this domain:
       PUSH (next_allowed, domain) back to heap
5. RETURN the URL

If back queues empty: refill from front queues
```

*Refilling Back Queues:*
```
FOR each front queue (high priority first):
    WHILE queue not empty:
        Take (url, domain, priority)
        IF domain not in back_queues:
            Create new back queue for domain
            Add (current_time, domain) to heap (ready immediately)
        Add URL to domain's back queue
        STOP if 1000+ domains active (batch limit)
```

*Distributed Frontier with Redis:*

*Redis Data Structures:*
- `frontier:priority:{domain}` → Sorted Set (score = negative priority)
- `frontier:domains` → Set of all active domains
- `frontier:last_fetch:{domain}` → Last fetch timestamp (with 1hr expiry)

*Adding URL:*
```
ZADD frontier:priority:{domain} {url: -priority_score}
SADD frontier:domains {domain}
```

*Getting Next URL:*
```
1. GET domains assigned to this worker (via consistent hashing)

2. FOR each assigned domain:
   - CHECK last fetch time from Redis
   - IF elapsed < crawl_delay: skip (not ready)
   - ZPOPMIN to atomically get highest priority URL
   - SET last fetch time
   - RETURN url

3. If no URLs ready: RETURN null
```

*Worker Assignment:* `consistent_hash(domain) % num_workers == my_worker_id`

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

*Redis Data Structures:*
- `drivers:{geohash}` → Sorted Set of driver_ids (score = timestamp)
- `driver:{driver_id}` → Hash with lat, lng, status, geohash (expires in 30s)

*Updating Driver Location:*
```
1. ENCODE driver's lat/lng to geohash (precision 6 = ~1km cells)
2. ADD driver_id to sorted set for that geohash cell
3. STORE driver details (lat, lng, status) in hash
4. SET 30-second expiry (auto-remove stale drivers)
```

*Finding Nearby Drivers:*
```
1. ENCODE pickup location to geohash
2. GET 9 cells: center cell + 8 neighbors (handles edge cases)
3. FOR each cell:
     GET all driver_ids from that cell's sorted set
     FOR each driver:
       IF status = "available":
         CALCULATE exact distance using Haversine formula
         IF distance ≤ radius: add to candidates
4. SORT candidates by distance
5. RETURN closest N drivers
```

*Matching Algorithm:*

```
Step 1: Find nearby drivers (expand search if needed)
  TRY radius 2km, then 5km, then 10km
  STOP when at least 5 candidates found
  IF no candidates: return "no drivers available"

Step 2: Calculate ETA for each candidate (in parallel)
  CALL routing service for each driver → pickup location

Step 3: Score each candidate
  score = (-ETA × 2) + (rating × 1) + (acceptance_rate × 0.5)

  Example: 5 min ETA, 4.8 rating, 90% acceptance
  score = (-5 × 2) + (4.8 × 1) + (0.9 × 0.5) = -10 + 4.8 + 0.45 = -4.75

Step 4: Dispatch to drivers in score order
  FOR each driver (best score first):
    SEND ride offer with 15-second timeout
    IF driver accepts: CREATE trip, RETURN success
    IF declined or timeout: try next driver
  RETURN "all drivers declined"
```

*Supply Positioning (Demand Heatmap):*

*Predicting Demand per Cell:*
```
Divide city into 500m × 500m grid cells

FOR each cell:
  predicted_demand =
      50% × historical_average (same time, day of week, last 4 weeks)
    + 30% × recent_trend (requests in last 30 minutes)
    + 20% × event_impact (nearby concerts, games, etc.)

  current_supply = count of drivers in this cell
  supply_gap = predicted_demand - current_supply
```

*Driver Repositioning Suggestions:*
```
1. FIND all cells within 5km of driver
2. FILTER to cells where supply_gap > 2 (undersupplied)
3. SORT by supply_gap descending
4. RETURN top 3 opportunities
```

*Surge Pricing:*

```
ratio = pending_requests / available_drivers

IF no drivers: surge = 3.0x (maximum)

Surge tiers:
  ratio < 1.0  → 1.0x (no surge)
  ratio 1.0-1.5 → 1.0x to 1.25x
  ratio 1.5-2.0 → 1.25x to 1.5x
  ratio 2.0-3.0 → 1.5x to 2.0x
  ratio > 3.0  → 2.0x to 3.0x (capped)

Example: 15 requests, 10 drivers → ratio 1.5 → surge 1.25x
```

*Fare Calculation:*

```
fare = base_fare + (distance × per_mile_rate) + (duration × per_minute_rate)

Example (5 miles, 15 minutes):
  $2.50 + (5 × $1.50) + (15 × $0.25) = $2.50 + $7.50 + $3.75 = $13.75

THEN apply surge: $13.75 × 1.5 = $20.63
THEN subtract promotions: $20.63 - $5.00 coupon = $15.63
THEN add fees: $15.63 + $3 airport fee = $18.63
FINALLY ensure minimum: MAX($18.63, $8.00) = $18.63
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

*RRULE Format Examples:*
```
RRULE:FREQ=DAILY;INTERVAL=1                    → Every day
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR              → Every Mon, Wed, Fri
RRULE:FREQ=MONTHLY;BYMONTHDAY=15              → 15th of every month
RRULE:FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=25    → Every Dec 25
RRULE:FREQ=WEEKLY;COUNT=10                     → Weekly, 10 occurrences total
RRULE:FREQ=DAILY;UNTIL=20251231T235959Z       → Daily until end of 2025
```

*Expanding Occurrences:*
```
INPUT: recurrence rule, query range (start, end), exceptions map

current = event's original start time
count = 0

WHILE current <= query_end:
    IF rule has UNTIL date AND current > UNTIL: stop
    IF rule has COUNT AND count >= COUNT: stop

    IF current >= query_start:
        IF current is in exceptions map:
            IF not deleted: add modified version to results
        ELSE:
            add regular instance to results

    current = next_occurrence(current, rule)
    count++

RETURN results

Next occurrence by frequency:
  DAILY:   add interval days
  WEEKLY:  find next day matching BYDAY (MO,WE,FR)
  MONTHLY: find next month, same day (or last day if month is shorter)
  YEARLY:  add interval years
```

**Event Instance Expansion on Query:**

```
INPUT: user_id, calendar_ids, date range (start, end)

Step 1: Get simple (non-recurring) events
  SELECT * FROM events
  WHERE calendar_id IN calendar_ids
    AND recurrence_rule IS NULL
    AND event overlaps with range

Step 2: Get recurring event masters
  SELECT * FROM events
  WHERE calendar_id IN calendar_ids
    AND recurrence_rule IS NOT NULL
    AND master_start < end
    AND (recurrence_end IS NULL OR recurrence_end > start)

Step 3: Expand each recurring master
  FOR each master event:
    GET exceptions (modified/deleted instances)
    PARSE recurrence rule
    GENERATE all instances within range
    ADD to results

Step 4: Sort all events by start time
```

**Free/Busy Query (Find Available Meeting Time):**

```
INPUT: list of attendee_ids, date, required duration, working hours (9am-5pm)

Step 1: Collect all busy intervals
  FOR each attendee:
    GET their calendars (including shared ones)
    GET all events for the day
    FOR each event marked as "busy":
      ADD (start_time, end_time) to busy_intervals

Step 2: Merge overlapping intervals
  SORT intervals by start time
  FOR each interval:
    IF overlaps with previous: extend previous
    ELSE: add as new interval

  Example: [(9:00-10:00), (9:30-11:00), (14:00-15:00)]
       → [(9:00-11:00), (14:00-15:00)]

Step 3: Find gaps that fit the meeting
  current = 9:00 AM (working hours start)
  FOR each busy block:
    gap = busy_start - current
    IF gap >= required_duration:
      ADD (current, busy_start) to free_slots
    current = MAX(current, busy_end)

  Check gap after last busy block until 5pm

RETURN free_slots
```

**Sync Protocol (Incremental Sync):**

```
INPUT: user_id, device_id, last_sync_token

IF no sync token (first sync):
    RETURN all user's events + new sync token

ELSE (incremental sync):
    DECODE token to get last_sync_timestamp

    QUERY: events WHERE updated_at > last_sync_timestamp

    FOR each changed event:
        IF deleted: add to deleted_ids list
        ELSE: add full event to updated list

    RETURN {
        updated: [full event objects],
        deleted: [event_ids to remove locally],
        sync_token: new_token
    }
```

**Conflict Resolution (Optimistic Concurrency):**

```
INPUT: event_id, updates, client's etag

1. FETCH current event from database

2. COMPARE etags:
   IF current.etag ≠ client_etag:
      REJECT with "Event was modified by another client"
      RETURN current event (so client can merge)

3. GENERATE new etag (random hash or timestamp)
   SET updated_at = now
   SAVE event with new etag

4. NOTIFY user's other devices to sync
5. IF significant change (time, location):
      NOTIFY all attendees

RETURN new_etag
```

*Why ETags:* Each edit increments version. If client A and B both edit, first one succeeds, second gets conflict and must refresh before retrying.

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

*The Problem:* Network timeout → client retries → two payments charged. We need exactly-once.

*Solution:* Client sends unique `idempotency_key` with each request. Server returns cached result for duplicate keys.

```
Step 1: Check idempotency cache
  IF key exists AND status = "processing": return "payment in progress"
  IF key exists AND status = "completed": return cached result

Step 2: Lock the key (atomic set-if-absent)
  SET key = {status: "processing"} with 24hr TTL
  IF lock failed (another request got it): retry from step 1

Step 3-4: Create payment record, run fraud check
  IF fraud score too high: mark DECLINED, cache result, return

Step 5-6: Call payment processor (Visa/Mastercard)
  IF approved: status = AUTHORIZED, save auth code
  ELSE: status = DECLINED, save decline reason

Step 7: Save to DB and cache final result

Step 8: Publish event for analytics, notifications

ON ERROR: Delete idempotency key (allow client to retry)
```

*Key insight:* Idempotency key stored in Redis with TTL. Same key always returns same result.

**Double-Entry Ledger:**

*Rule:* Every transaction has equal debits and credits. If they don't balance, something is wrong.

*Recording a $100 payment with $3 platform fee:*
```
Entry 1: Payment received
  DEBIT  Cash Account         +$100  (asset increases)
  CREDIT Merchant Account     +$100  (liability to merchant)

Entry 2: Platform fee
  DEBIT  Merchant Account     -$3    (reduce what we owe merchant)
  CREDIT Platform Revenue     +$3    (our earnings)

Result: Merchant balance = $97, Platform earned = $3
```

*Calculating Account Balance:*
```
balance = SUM(all credits) - SUM(all debits)

For merchant: $100 credit - $3 debit = $97 balance
```

*Why Double-Entry:* Every dollar is accounted for. Bugs that lose money are immediately detectable (debits ≠ credits).

**Fraud Detection (Real-time Scoring):**

| Signal | What It Checks | Risk Indicator |
|--------|----------------|----------------|
| Velocity | Transactions in last 24 hours | >10 txns = suspicious |
| Geo mismatch | IP country ≠ card country | High risk if different |
| Device fingerprint | Known fraudster device? | Score from 0-100 |
| First purchase | New customer? | Slightly higher risk |
| Unusual amount | 3x higher than user's average | Suspicious |
| Prepaid card | Card is prepaid/gift card | Higher fraud rate |
| High-risk country | Card from known fraud region | Higher risk |
| ML model | Trained on historical fraud | Score 0-100 |

*Decision Thresholds:*
```
Final score < 30  → APPROVE automatically
Final score 30-70 → REVIEW (3D Secure challenge or manual review)
Final score > 70  → DECLINE automatically
```

**Retry Logic with Exponential Backoff:**

```
max_retries = 3
delays = [1s, 2s, 4s]  (doubles each time)

FOR attempt = 0 to 3:
    TRY process payment
    IF success: RETURN result

    IF error is retryable (network timeout, processor busy):
        wait = delays[attempt] + random(0-1 second)  ← jitter prevents thundering herd
        SLEEP(wait)
        CONTINUE

    IF error is non-retryable (invalid card, insufficient funds):
        THROW error immediately (don't retry)

THROW "max retries exceeded"
```

*Retryable:* Network timeout, 503 Service Unavailable, rate limited
*Non-retryable:* Invalid card number, expired card, insufficient funds, fraud decline

**Reconciliation System:**

*Daily Process (runs at end of each day):*
```
Step 1: Get OUR records
  SELECT all payments from today WHERE status = CAPTURED or SETTLED

Step 2: Get PROCESSOR's settlement report
  Download from Visa/Mastercard API

Step 3: Compare and find discrepancies

  FOR each of our transactions:
    IF not in processor's report → flag "MISSING_IN_PROCESSOR"
    IF amounts don't match → flag "AMOUNT_MISMATCH"

  FOR each processor transaction:
    IF not in our records → flag "MISSING_IN_INTERNAL"

Step 4: Alert finance team if any discrepancies found
```

*Common Discrepancies:*
- MISSING_IN_PROCESSOR: We think it succeeded, they say it didn't (lost transaction)
- MISSING_IN_INTERNAL: They have record we don't (system bug)
- AMOUNT_MISMATCH: Currency conversion difference, partial capture

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
```
Lock {
    name:        "resource-123"        // Lock identifier
    owner:       "client-abc"          // Who holds the lock
    token:       42                    // Fencing token (monotonically increasing)
    acquired_at: 1704067200000         // When acquired (epoch ms)
    ttl_ms:      30000                 // Expires in 30 seconds
}

is_expired = current_time > acquired_at + ttl_ms
remaining_ttl = MAX(0, acquired_at + ttl_ms - current_time)
```

**Single-Node Lock Manager:**

*Acquire Lock:*
```
INPUT: lock_name, client_id, ttl_ms (default 30s)

1. CHECK if lock exists and not expired:
   IF lock exists AND not expired:
       IF owner == client_id:
           // Re-entrant: same client, extend TTL
           RESET acquired_at to now
           RETURN success, same token
       ELSE:
           // Someone else holds it
           RETURN failure, remaining_ttl

2. Lock is available (doesn't exist or expired):
   INCREMENT global token counter (ensures monotonic tokens)
   CREATE new lock with client as owner
   RETURN success, new token

Token: 40 → 41 → 42 → ... (never decreases)
```

*Release Lock:*
```
INPUT: lock_name, client_id, token

1. IF lock doesn't exist: return success (already released)
2. IF owner ≠ client_id: return failure (not your lock)
3. IF token ≠ lock's token: return failure (stale token)
4. DELETE lock, return success
```

*Extend Lock:*
```
INPUT: lock_name, client_id, token, new_ttl_ms

1. VERIFY: lock exists, owner matches, token matches, not expired
2. IF any check fails: return failure
3. RESET acquired_at to now, update ttl_ms
4. RETURN success
```

**Redlock Algorithm (Distributed, Multi-Master):**

*Setup:* 5 independent Redis nodes, quorum = 3 (majority)

*Acquire Lock:*
```
1. Generate unique client_id (UUID)
2. Record start_time

3. FOR each of 5 Redis nodes:
   TRY: SET lock_name client_id NX PX ttl_ms
        (NX = only if not exists, PX = expire in ms)
   IF success: acquired_count++
   IF node down: skip (continue to next)

4. CALCULATE validity:
   elapsed = now - start_time
   clock_drift = ttl_ms × 1% + 2ms   (safety margin)
   validity = ttl_ms - elapsed - clock_drift

5. IF acquired_count >= 3 AND validity > 0:
   // Got quorum and lock hasn't expired
   RETURN success, client_id, valid_until

6. ELSE:
   // Failed - release all locks we acquired
   FOR each node: DELETE lock_name IF value == client_id
   RETURN failure
```

*Release Lock:*
```
FOR each Redis node:
    Atomically: IF GET(lock_name) == client_id THEN DELETE
```

*Retry with Backoff:*
```
FOR attempt = 0 to max_retries:
    TRY acquire
    IF success: return
    delay = 200ms × (2^attempt) + random(0-100ms)
    SLEEP(delay)
```

**Fencing Tokens (Prevent Stale Client Writes):**

*The Problem:*
```
1. Client A acquires lock, gets token=42
2. Client A pauses (GC pause, network delay)
3. Lock expires
4. Client B acquires lock, gets token=43
5. Client A wakes up, thinks it still has lock
6. Both A and B try to write → DATA CORRUPTION
```

*The Solution:* Resources check token before accepting writes
```
Resource stores: last_seen_token = 0

ON write(data, fencing_token):
    IF fencing_token < last_seen_token:
        REJECT "stale token"
    last_seen_token = fencing_token
    PERFORM write
```

*Example:*
```
Client A (token=42) writes → accepted, last_seen=42
Client A pauses, lock expires
Client B (token=43) writes → accepted, last_seen=43
Client A wakes, tries to write with token=42 → REJECTED (42 < 43)
```

**Raft-Based Lock Service (Consensus Approach):**

*How It Works:*
```
                    ┌─────────────┐
    Clients ───────▶│   Leader    │◀──── All writes go through leader
                    │   (Node 1)  │
                    └──────┬──────┘
                           │ Replicates via Raft
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐   ┌────────┐   ┌────────┐
         │Follower│   │Follower│   │Follower│
         │(Node 2)│   │(Node 3)│   │(Node 4)│
         └────────┘   └────────┘   └────────┘
```

*Acquire via Raft:*
```
1. IF not leader: redirect client to leader

2. CREATE log entry: {type: ACQUIRE, session_id, lock_name, ttl_ms}

3. REPLICATE through Raft consensus (waits for majority)

4. APPLY to state machine:
   IF lock held by another session: return failure
   IF lock held by same session: extend TTL
   IF lock available: create lock, assign token
```

*Benefits over Redlock:* Linearizable (strongest consistency), survives up to N/2 failures

**Lock Client with Auto-Renewal:**

```
ON acquire(lock_name, ttl=30s, blocking=true):
    WHILE true:
        TRY acquire lock from service
        IF success:
            START background thread: renewal_loop(lock_name, token, ttl)
            RETURN lock handle
        IF not blocking: return null
        IF timeout reached: throw error
        SLEEP 100ms

RENEWAL LOOP (runs in background):
    EVERY 10 seconds (before 30s TTL expires):
        TRY extend lock TTL
        IF failed: lock was lost, notify application

ON release:
    STOP renewal thread
    CALL service.release(lock_name, token)
```

*Context Manager Pattern:*
```
WITH lock_client.acquire("resource-123") as lock:
    // do critical section work
    // lock automatically released when block exits
    // (even if exception thrown)
```
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

**How Geohash Works:**
- Divides Earth into grid cells with hierarchical precision
- Nearby points share common prefix in their geohash string
- Precision levels: 1 char = ±2500 km, 4 chars = ±20 km, 6 chars = ±0.6 km, 8 chars = ±19 m

**Encoding Algorithm:**
```
To encode (latitude, longitude) to geohash string:
  1. Start with full lat range [-90, 90] and lng range [-180, 180]
  2. Alternate between longitude and latitude bits
  3. For each bit:
     - Calculate midpoint of current range
     - If coordinate >= midpoint: set bit to 1, use upper half
     - Otherwise: set bit to 0, use lower half
  4. Every 5 bits, convert to Base32 character
  5. Repeat until reaching desired precision

Get neighbors: Return 8 adjacent cells (N, NE, E, SE, S, SW, W, NW)
              Handle wraparound at date line and poles
```

**Geohash Proximity Search:**
```
ADD BUSINESS:
  1. Encode lat/lng to geohash (precision 6 = ~600m cells)
  2. Store in Redis:
     - GEOADD for Redis native geo queries
     - SADD to "businesses:geohash:{hash}" for fast cell lookup
     - HSET business data (lat, lng, details)

SEARCH NEARBY:
  1. Choose precision based on radius:
     - >100 km → precision 3 (~78 km cells)
     - >10 km  → precision 4 (~20 km cells)
     - >1 km   → precision 5 (~2.4 km cells)
     - else    → precision 6 (~0.6 km cells)
  2. Encode search center to geohash
  3. Get center cell + 8 neighbors (9 cells total)
  4. Collect all businesses from these cells (candidates)
  5. Filter candidates by exact haversine distance
  6. Sort by distance, return top N

HAVERSINE DISTANCE:
  - Uses spherical Earth model (radius = 6371 km)
  - Accounts for Earth's curvature
  - Formula: distance = 2 * R * arcsin(sqrt(a))
    where a depends on lat/lng differences
```

*Approach 2: QuadTree (In-Memory):*

**QuadTree Concept:**
- Recursively divides 2D space into 4 quadrants (NW, NE, SW, SE)
- Each node holds points until capacity reached, then splits
- Good for: non-uniform distribution, dynamic updates
- Query time: O(log n) average

**QuadTree Structure:**
```
Each node contains:
  - boundary: rectangle (x, y, width, height)
  - capacity: max points before splitting (e.g., 4-100)
  - points: list of (id, x, y, data) tuples
  - children: NW, NE, SW, SE (null until split)

INSERT:
  1. If point outside this node's boundary → reject
  2. If room in this node and not yet split → add point here
  3. Otherwise:
     a. If not split yet → subdivide into 4 children
        (re-insert existing points into appropriate children)
     b. Insert into whichever child contains the point

SUBDIVIDE:
  Split boundary into 4 equal rectangles:
  - NW: upper-left quarter
  - NE: upper-right quarter
  - SW: lower-left quarter
  - SE: lower-right quarter
  Move all points from parent to appropriate children

RADIUS QUERY:
  1. If this node's boundary doesn't intersect search circle → skip entirely
  2. Check all points in this node, add those within radius
  3. Recursively query all children (if split)

  Circle-rectangle intersection: find closest point on rectangle to circle center,
  check if distance to that point ≤ radius
```

**QuadTree Proximity Service:**
```
SETUP:
  - Create tree covering world: lng [-180, 180], lat [-90, 90]
  - Maintain separate map of id → full business data

ADD BUSINESS:
  - Store full data in map
  - Insert (id, lng, lat) into quadtree

SEARCH NEARBY:
  1. Convert radius from km to degrees (~111 km per degree)
  2. Query tree for candidates within radius
  3. Apply business filters (category, rating, etc.)
  4. Calculate exact distance using haversine formula
  5. Filter to those truly within radius
  6. Sort by distance, return top N
```

*Approach 3: Google S2 Cells:*

**S2 Geometry Concept:**
- Projects Earth onto a cube, then uses Hilbert curve for 1D ordering
- Provides tight covering of arbitrary regions with variable-size cells
- Advantages over geohash: no discontinuities at edges, better polar coverage

**S2 Proximity Search:**
```
SEARCH NEARBY:
  1. Create spherical cap (circle on sphere) from center + radius
     - Convert radius from km to radians: radius / 6371 (Earth's radius)
  2. Get covering cells using S2 Region Coverer:
     - Set max cells (e.g., 20) to limit query count
     - Set min level (e.g., 10 = ~10 km) and max level (e.g., 16 = ~150 m)
     - Coverer returns minimal set of cells that fully cover the circle
  3. For each covering cell, do database range query:
     - "SELECT * FROM businesses WHERE s2_cell BETWEEN cell_min AND cell_max"
     - S2 cells are hierarchical: all children share parent prefix
  4. Filter candidates by exact haversine distance
  5. Sort by distance, return top N

ADD BUSINESS:
  - Calculate S2 cell at leaf level (level 30 = finest granularity)
  - Store business with cell ID in database
  - Index on s2_cell column for efficient range queries
```

**Sharding Strategy:**
```
CONCEPT:
  - Shard businesses by geographic region for horizontal scaling
  - Each shard handles a contiguous region (e.g., city, country, continent)
  - Shards map to geohash prefixes (precision 2 = ~600 km regions)

SEARCH NEARBY:
  1. Encode search center to low-precision geohash (precision 2)
  2. Identify which shards cover this region
  3. If radius is large (>50 km), include neighboring regions too
  4. Query all relevant shards in PARALLEL
  5. Merge results from all shards
  6. Sort merged results by distance, return top N

FIND RELEVANT SHARDS:
  - Start with shard for center geohash
  - If search radius might cross region boundaries:
    - Add shards for all 8 neighboring geohash cells
  - Return deduplicated list of shards to query
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

**Core Algorithm:**
```
CONFIGURATION:
  - EPOCH: Custom start time (e.g., 2020-01-01) to maximize timestamp range
  - Bit allocation: 1 sign + 41 timestamp + 10 node + 12 sequence = 64 bits
  - Max values: node_id 0-1023, sequence 0-4095 per millisecond

STATE:
  - node_id: Unique identifier for this generator instance
  - sequence: Counter within current millisecond
  - last_timestamp: Previous generation time
  - lock: Mutex for thread safety

GENERATE ID:
  1. Acquire lock (thread-safe)
  2. Get current timestamp in milliseconds
  3. Check for clock going backwards:
     - If current < last → ERROR (clock moved backwards!)
  4. Handle same-millisecond case:
     - Increment sequence (0 → 1 → 2 ... → 4095)
     - If sequence overflows (wraps to 0):
       - Spin-wait until next millisecond
  5. Handle new-millisecond case:
     - Reset sequence to 0
  6. Compose 64-bit ID:
     - ID = (timestamp - EPOCH) << 22  |  node_id << 12  |  sequence
  7. Return ID

PARSE ID (extract components):
  - timestamp = (ID >> 22) + EPOCH
  - node_id = (ID >> 12) & 0x3FF  (10 bits)
  - sequence = ID & 0xFFF  (12 bits)
```

**Handling Clock Skew:**
```
ROBUST GENERATOR (tolerates small clock drift):
  On clock backward detection:
    - Calculate skew = last_timestamp - current_time
    - If skew ≤ max_allowed (e.g., 5 seconds):
      - Sleep for skew duration, then retry
    - If skew > max_allowed:
      - ERROR: Clock skew too large (system time may be misconfigured)

LOGICAL CLOCK APPROACH (alternative):
  - Maintain logical_time = max(wall_time, last_logical_time)
  - Never goes backwards by definition
  - Trade-off: IDs may drift from wall clock during skew periods
  - On sequence overflow: increment logical_time by 1
```

**Node ID Assignment Strategies:**
```
STRATEGY 1: STATIC CONFIGURATION (simplest)
  - Set node ID via config file or environment variable
  - Pros: Simple, no external dependencies
  - Cons: Manual management, risk of duplicates if misconfigured

STRATEGY 2: ZOOKEEPER (automatic, survives restarts)
  - Create ephemeral sequential node: /snowflake/service/nodes/node-
  - ZooKeeper auto-appends sequence number: node-0000000042
  - Extract sequence number as node ID (42)
  - Ephemeral: node deleted when service disconnects → ID reusable
  - Pros: Automatic, handles restarts
  - Cons: Requires ZooKeeper cluster

STRATEGY 3: DATABASE WITH LEASE (simple coordination)
  1. Try to claim an expired lease:
     - UPDATE node_leases SET hostname=me, lease_until=now+5min
       WHERE lease_until < NOW() LIMIT 1
  2. If no expired lease, create new one:
     - INSERT INTO node_leases (hostname, lease_until)
       WHERE (SELECT COUNT(*) FROM node_leases) < 1024
  3. Background thread: renew lease before expiry
  - Pros: Uses existing database, no new infrastructure
  - Cons: Slightly slower, lease renewal overhead
```

**Datacenter-Aware Snowflake:**
```
Bit allocation (splits 10-bit node ID):
  - 41 bits: Timestamp
  - 5 bits:  Datacenter ID (0-31)
  - 5 bits:  Machine ID (0-31 per datacenter)
  - 12 bits: Sequence

Total capacity: 32 datacenters × 32 machines = 1024 nodes

ID Composition:
  ID = (timestamp - EPOCH) << 22  |  datacenter_id << 17  |  machine_id << 12  |  sequence

Use case: Multi-region deployments where you want datacenter encoded in ID
```

**Alternative: ULID (Lexicographically Sortable):**
```
ULID: Universally Unique Lexicographically Sortable Identifier

Format: 26 characters, Crockford Base32 encoded
  - 48 bits: Timestamp (milliseconds, good for 10889 years)
  - 80 bits: Randomness
  - Total: 128 bits (same as UUID)

Properties:
  - Lexicographically sortable (string comparison works)
  - Case insensitive, URL safe (no special characters)
  - Example: 01ARZ3NDEKTSV4RRFFQ69G5FAV

GENERATION:
  1. Get current timestamp in milliseconds
  2. If same millisecond as last ID:
     - Increment the random portion by 1 (monotonic within ms)
     - On overflow: wait for next millisecond
  3. If new millisecond:
     - Generate fresh 80 random bits
  4. Encode to Crockford Base32:
     - First 10 chars: timestamp (48 bits)
     - Last 16 chars: randomness (80 bits)

Trade-off vs Snowflake:
  - ULID: No node ID management, works anywhere, tiny collision risk
  - Snowflake: Guaranteed unique, requires node ID coordination
```

**ID Generator Service:**
```
HTTP SERVICE WRAPPER:
  - Wraps Snowflake generator for network access
  - Supports batch generation for efficiency

PRE-GENERATION (reduces latency):
  - Maintain cache of ~1000 pre-generated IDs
  - Background thread continuously refills cache
  - When cache drops below 500, generate 100 more

GET SINGLE ID:
  1. Try to get from cache (instant, no lock contention)
  2. If cache empty: generate on-demand (slightly slower)

GET BATCH:
  - Return requested count of IDs
  - Draws from cache when available, generates when not
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
```
STATE:
  - max_out_of_order: allowed lateness (e.g., 5000 ms)
  - max_timestamp_seen: highest event time observed so far

ON EACH EVENT:
  - Update max_timestamp_seen = max(current, event_time)

CURRENT WATERMARK:
  - watermark = max_timestamp_seen - max_out_of_order
  - Meaning: "All events with time < watermark have arrived"

Example timeline (5 second lateness):
  Event times:  [10:00:01, 10:00:05, 10:00:03, 10:00:08]
  max_seen:     [10:00:01, 10:00:05, 10:00:05, 10:00:08]
  watermark:    [09:59:56, 10:00:00, 10:00:00, 10:00:03]
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
```
If partition has no events for > idle_timeout:
  → Artificially advance its watermark to current processing time
  → Prevents one idle partition from blocking global watermark progress
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
```
CONCEPT: Interleave bits of two coordinates to create single Z-value
  - Points close in 2D space have similar Z-values
  - Creates space-filling curve (Morton curve)

2D EXAMPLE:
  x = 5 (binary: 0101)
  y = 3 (binary: 0011)

  Interleave bits: take alternating bits from x and y
    y3 x3 y2 x2 y1 x1 y0 x0
     0  0  0  1  1  1  0  1  = 29 (0x1D)

  Result: Z-value = 29

MULTI-COLUMN:
  For N columns, interleave bits from all columns
  For each bit position (0 to bits_per_col):
    For each column:
      If that bit is set in column value, set corresponding bit in Z-value
  Result: single integer encoding all column values
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
```
STATE:
  - dag_id: which DAG to backfill
  - dates: full list of dates to process (start_date to end_date)
  - max_parallel: how many dates to run concurrently (e.g., 10)
  - completed: set of successfully completed dates
  - failed: set of dates that failed

GET NEXT BATCH:
  1. Filter out completed and failed dates → pending list
  2. Sort pending dates (oldest first - dependencies may exist)
  3. Return up to max_parallel dates to run next

ON DATE COMPLETE:
  - If success: add to completed set
  - If failure: add to failed set
  - Then call get_next_batch for more work
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
```
SAVE PROGRESS (after each date completes):
  - INSERT or UPDATE backfill_state table with (dag_id, date, status, completed_at)
  - Use UPSERT (ON CONFLICT UPDATE) for idempotent saves

RESUME BACKFILL (on restart):
  1. Query database for all dates with status='success'
  2. Return remaining dates = all_dates - completed_dates
  3. Continue processing only unfinished dates
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
```
CALCULATE FAIR SHARE:
  1. Sum weights of all queues
  2. For each queue:
     - fair_share = (queue.weight / total_weight) × total_resources
     - Constrain: fair_share = min(fair_share, queue.demand)
       (don't allocate more than queue actually needs)
  3. Redistribute unused share to queues with unmet demand

Example:
  Queue A: weight=2, demand=40%  → fair_share = 40% (capped by demand)
  Queue B: weight=3, demand=100% → fair_share = 60% (gets A's unused share)
```

*Preemption Decision Algorithm:*
```
SHOULD PREEMPT?
  1. Cooldown check: If preempted recently (e.g., within 30 sec) → NO
  2. Calculate shortfall: fair_share - current_allocated
  3. Significance check: If shortfall < 10% of fair_share → NO (not worth it)
  4. Find victims: Check if any queue is using >110% of its fair_share
     - If yes → YES, preempt from over-users
     - If no → NO (no one to preempt from)

SELECT VICTIMS:
  1. Sort candidate containers by:
     - Priority (low priority first - preempt least important)
     - Runtime (shorter runtime first - minimize wasted work)
  2. Greedily select containers until freed resources >= needed
  3. Return victim list
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
