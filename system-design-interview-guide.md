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
