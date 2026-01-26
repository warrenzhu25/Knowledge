# Databricks Staff Software Engineer - Interview Preparation Guide

## Position Overview

- **Role:** Staff Software Engineer (Data Platform / Backend / Infrastructure)
- **Location:** San Francisco, Seattle, or Remote (US)
- **Compensation:** $400K-$700K+ total compensation (base + equity + bonus)
  - Base salary: ~$200K-$295K
  - Significant equity component at Staff level
- **Requirements:** 6+ years experience with technical leadership on large-scale data systems

### Key Teams Hiring Staff Engineers
- **Data Platform:** Metrics store, Data Intelligence Platform, CI/CD infrastructure
- **Core Infrastructure:** Multi-cloud Kubernetes, VM orchestration at scale
- **Runtime:** Spark optimization, query execution, performance

---

## Interview Process (4 Stages)

| Stage | Duration | Focus |
|-------|----------|-------|
| 1. Recruiter Screen | 30 min | Background, motivation, salary expectations |
| 2. Technical Phone Screen | 1 hour | LeetCode medium-hard on CoderPad |
| 3. Hiring Manager Call | 1 hour | Behavioral, past projects, team fit |
| 4. Onsite | 4-5 hours | 5 rounds (see breakdown below) |

**Timeline:** Average 27 days from application to offer

### Onsite Breakdown (5 Rounds)
1. **Coding 1 - Algorithms** (1 hour): Hash maps, binary search, graphs
2. **Coding 2 - Data Structures** (1 hour): Custom implementations, optimization
3. **Coding 3 - Concurrency** (1 hour): Multithreading, synchronization
4. **System Design** (1 hour): Distributed systems, often via Google Docs
5. **Cross-functional/Behavioral** (1 hour): Culture fit, collaboration

### Post-Interview
- **Reference checks:** 1 manager + 2 senior peers (heavily weighted)
- **Hiring committee review**
- **VP Engineering approval** (final decision)

---

## Part 1: Databricks Core Values & Culture

### The Six Core Values

**1. Customer Obsessed**
> The customer is at the center of everything. What's best for customers is best for the company.

**2. Raise the Bar**
> Maintain high standards in hiring, code quality, and product excellence.

**3. Truth Seeking**
> Value data and evidence over opinions. Embrace intellectual honesty.

**4. First Principles Thinking**
> Question assumptions. Solve problems from fundamentals, not by analogy.

**5. Bias for Action**
> Speed matters. Debate fast, plan fast, drive alignment, execute.

**6. Put the Company First**
> Prioritize collective success over individual or team wins.

---

### Behavioral Questions

**Q: Why Databricks?**

Sample Answer:
> "I'm drawn to Databricks because you're not just building tools—you're defining the future of data infrastructure. The Lakehouse architecture fundamentally changes how organizations think about data, eliminating the false choice between data lakes and warehouses. As someone who's spent years wrestling with the complexity of maintaining separate systems for batch and streaming, I find Databricks' unified approach compelling.
>
> What excites me most is the scale of impact. Databricks processes exabytes of data for over 10,000 organizations. The engineering challenges—making Spark faster, Delta Lake more reliable, infrastructure work across three cloud providers—these are problems I want to solve. And the open-source DNA means the work benefits the broader community, not just Databricks customers."

**Q: Tell me about a time you raised the bar on a project.**

Sample Answer (STAR):
> **Situation:** Our team had a data pipeline that worked but was fragile—it failed weekly and required manual intervention.
>
> **Task:** I wasn't the owner, but I saw an opportunity to establish better practices across the team.
>
> **Action:** I proposed and led an initiative to add comprehensive testing and monitoring. I created a testing framework that could simulate pipeline failures, wrote documentation on our new standards, and pair-programmed with each team member to refactor their pipelines. I also set up automated alerts and runbooks for common failure modes.
>
> **Result:** Pipeline failures dropped from weekly to quarterly. More importantly, the practices spread to other teams. What started as fixing one pipeline became an engineering-wide improvement in reliability culture. The framework I built is now used by 8 teams.

**Q: Describe a time you used first principles thinking to solve a problem.**

Sample Answer:
> "We had a Spark job that was taking 6 hours despite throwing more resources at it. The conventional wisdom was 'add more executors.' Instead, I went back to first principles: What is this job actually doing? Where is time spent?
>
> I analyzed the execution plan and found that 90% of time was in a single shuffle stage with severe data skew—one partition had 100x more data than others due to a popular key. More executors couldn't help because one task was the bottleneck.
>
> The solution wasn't more resources but smarter partitioning: I implemented salted keys to spread the hot partition across multiple tasks. The job went from 6 hours to 40 minutes with *fewer* resources. First principles revealed the real problem; conventional thinking would have just burned more money."

**Q: Give an example of when you put the company first over your team's interests.**

Sample Answer:
> "My team had built a custom orchestration system we were proud of. When the platform team proposed standardizing on Airflow company-wide, my initial reaction was defensive—our system had features Airflow lacked.
>
> But I stepped back and evaluated it from the company's perspective. Maintaining multiple orchestration systems meant duplicated effort, harder cross-team collaboration, and higher onboarding costs. The features we'd lose were nice-to-haves, not essentials.
>
> I advocated to my team for adopting Airflow, contributed our best features back to the platform team's implementation, and led the migration. It was hard to let go of something we'd built, but the company benefited from standardization, and our engineers could now collaborate more easily with other teams."

---

## Part 2: Technical Questions - Databricks Stack

### Delta Lake

**Q: What is Delta Lake and how does it differ from Parquet?**

Sample Answer:
> "Parquet is a columnar file format—it defines how data is serialized to disk. Delta Lake is a storage *layer* built on top of Parquet that adds:
>
> 1. **ACID transactions:** Atomic commits, consistent reads, isolated writes, durable storage
> 2. **Schema enforcement:** Rejects writes that don't match the table schema
> 3. **Schema evolution:** Safely add/modify columns over time
> 4. **Time travel:** Query previous versions of data using version numbers or timestamps
> 5. **Audit history:** Full log of all changes to the table
> 6. **Unified batch/streaming:** Same table works for both batch reads and streaming writes
>
> The magic is the transaction log (`_delta_log/`). Every operation writes a JSON commit file describing what changed. Reads use the log to construct a consistent snapshot, enabling ACID semantics on top of cloud object storage."

**Q: Explain Delta Lake's transaction log and how it enables ACID transactions.**

Sample Answer:
> "The transaction log is a series of JSON files (and periodic checkpoint Parquet files) in the `_delta_log/` directory. Each commit creates a new JSON file with a monotonically increasing version number.
>
> **How it works:**
> 1. **Write path:** Writer creates new data files, then atomically writes a commit JSON listing those files. The atomic rename is the commit point.
> 2. **Read path:** Reader lists the log, finds the latest checkpoint, replays subsequent commits to build the current table state (list of valid files).
> 3. **Conflict resolution:** Optimistic concurrency—if two writers commit simultaneously, one will fail the atomic rename and must retry after re-reading the log.
>
> **ACID properties:**
> - **Atomicity:** Commit JSON is written atomically; partial commits are impossible
> - **Consistency:** Schema enforcement validated before commit
> - **Isolation:** Snapshot isolation—readers see consistent point-in-time view
> - **Durability:** Once commit JSON is written to cloud storage, it's durable
>
> Checkpoints (every 10 commits by default) compact the log into Parquet for faster reads—otherwise you'd replay potentially thousands of JSON files."

**Q: What is Z-Ordering and when would you use it?**

Sample Answer:
> "Z-Ordering is a technique to co-locate related data in the same files based on multiple columns. It uses a space-filling Z-curve to interleave bits from multiple column values, creating a single sort key that preserves locality across all specified columns.
>
> **When to use:**
> - Tables frequently filtered on multiple columns (e.g., `WHERE country = 'US' AND date = '2024-01-01'`)
> - Large tables where data skipping provides significant benefit
> - Columns with high cardinality that aren't suitable for partitioning
>
> **Example:**
> ```sql
> OPTIMIZE my_table ZORDER BY (country, date, user_id)
> ```
>
> **Trade-offs:**
> - Z-Ordering is expensive—it rewrites data files
> - Diminishing returns beyond 3-4 columns
> - Best combined with OPTIMIZE to compact small files simultaneously
>
> **vs. Partitioning:** Partitioning physically separates data into directories (coarse-grained). Z-Ordering organizes data within files (fine-grained). Use both: partition by high-level dimension (date), Z-Order by query filters within partitions."

**Q: Explain the medallion architecture (Bronze/Silver/Gold).**

Sample Answer:
> "The medallion architecture is a data design pattern with three layers of progressive refinement:
>
> **Bronze (Raw):**
> - Ingested data as-is from sources
> - Append-only, preserves original format
> - Added metadata: `_ingest_time`, `_source_file`, `_batch_id`
> - Use Auto Loader for streaming ingestion
> - Purpose: Audit trail, reprocessing capability
>
> **Silver (Cleaned):**
> - Validated, deduplicated, conformed data
> - Schema enforced, data types corrected
> - Business logic applied (joins, transformations)
> - Use Delta MERGE for CDC/upsert patterns
> - Purpose: Single source of truth, reusable across use cases
>
> **Gold (Aggregated):**
> - Business-level aggregations and metrics
> - Optimized for specific use cases (BI, ML features)
> - Heavily indexed, Z-Ordered for query patterns
> - Purpose: Performance, consumption-ready
>
> **Why this pattern:**
> - Separation of concerns (ingestion vs. transformation vs. serving)
> - Reproducibility (can rebuild Silver/Gold from Bronze)
> - Quality gates between layers
> - Different SLAs per layer (Bronze: latency, Gold: query performance)"

---

### Apache Spark (Databricks Runtime)

**Q: What is lazy evaluation in Spark and why does it matter?**

Sample Answer:
> "Lazy evaluation means Spark doesn't execute transformations immediately. Instead, it builds a DAG (Directed Acyclic Graph) of operations and only executes when an *action* is called (collect, count, write, etc.).
>
> **Why it matters:**
>
> 1. **Optimization:** Catalyst optimizer can analyze the entire DAG and optimize across operations—predicate pushdown, projection pruning, join reordering
>
> 2. **Efficiency:** Avoids materializing intermediate results. `df.filter().select().filter()` becomes a single pass over data, not three separate reads/writes
>
> 3. **Fault tolerance:** Since transformations are just descriptions, failed tasks can be recomputed from the lineage without storing intermediate state
>
> **Practical implications:**
> - Transformations (map, filter, join) are lazy
> - Actions (count, collect, save) trigger execution
> - Calling `df.cache()` is lazy too—data is cached on first action
> - Debug by calling `.explain()` to see the physical plan without executing"

**Q: Explain Adaptive Query Execution (AQE) in Spark 3.x.**

Sample Answer:
> "AQE optimizes queries at *runtime* based on actual data statistics, rather than relying solely on pre-execution estimates.
>
> **Key features:**
>
> 1. **Coalescing shuffle partitions:**
>    - Problem: `spark.sql.shuffle.partitions=200` may create many tiny partitions
>    - AQE: Combines small partitions after shuffle based on actual data size
>    - Enable: `spark.sql.adaptive.coalescePartitions.enabled=true`
>
> 2. **Switching join strategies:**
>    - Problem: Optimizer chose sort-merge join based on stale statistics, but one side is actually small
>    - AQE: Converts to broadcast join at runtime if data fits
>    - Enable: `spark.sql.adaptive.enabled=true`
>
> 3. **Skew join optimization:**
>    - Problem: One partition has 100x more data, causing straggler
>    - AQE: Detects skew at runtime, splits large partition into smaller tasks
>    - Enable: `spark.sql.adaptive.skewJoin.enabled=true`
>
> **In Databricks:** AQE is enabled by default in Databricks Runtime. It's especially powerful because it handles real-world data distribution issues that static optimization can't predict."

**Q: How would you debug a slow Spark job?**

Sample Answer:
> "Systematic approach:
>
> **1. Check Spark UI stages:**
> - Which stage is slowest? (Usually shuffle or skewed stage)
> - Are tasks evenly distributed? (Check task duration variance)
> - Is there spill to disk? (Memory pressure)
>
> **2. Examine the query plan:**
> ```python
> df.explain(True)  # Shows parsed, analyzed, optimized, physical plans
> ```
> - Look for: BroadcastHashJoin vs SortMergeJoin, Filter pushdown, Partition pruning
>
> **3. Common culprits and fixes:**
>
> | Symptom | Likely Cause | Fix |
> |---------|--------------|-----|
> | One task much slower | Data skew | Salt keys, AQE skew handling |
> | High shuffle read time | Too many partitions | Coalesce, adjust shuffle partitions |
> | Spill to disk | Insufficient memory | Increase executor memory, reduce partition size |
> | Full table scan | Missing partition filter | Add partition predicate, check column stats |
> | Slow joins | Wrong join strategy | Force broadcast for small tables |
>
> **4. Databricks-specific tools:**
> - Query profile in SQL warehouses
> - Ganglia metrics for cluster resource utilization
> - Spark UI storage tab for cache effectiveness
>
> **5. Profile before optimizing:**
> Don't guess. Measure where time is actually spent, then target that specifically."

---

### Concurrency & Multithreading

**Q: Implement a thread-safe bounded blocking queue.**

```java
import java.util.LinkedList;
import java.util.Queue;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

public class BoundedBlockingQueue<T> {
    private final Queue<T> queue;
    private final int capacity;
    private final Lock lock;
    private final Condition notFull;
    private final Condition notEmpty;

    public BoundedBlockingQueue(int capacity) {
        this.capacity = capacity;
        this.queue = new LinkedList<>();
        this.lock = new ReentrantLock();
        this.notFull = lock.newCondition();
        this.notEmpty = lock.newCondition();
    }

    public void put(T item) throws InterruptedException {
        lock.lock();
        try {
            while (queue.size() == capacity) {
                notFull.await();  // Wait until space available
            }
            queue.offer(item);
            notEmpty.signal();  // Signal waiting consumers
        } finally {
            lock.unlock();
        }
    }

    public T take() throws InterruptedException {
        lock.lock();
        try {
            while (queue.isEmpty()) {
                notEmpty.await();  // Wait until item available
            }
            T item = queue.poll();
            notFull.signal();  // Signal waiting producers
            return item;
        } finally {
            lock.unlock();
        }
    }

    public int size() {
        lock.lock();
        try {
            return queue.size();
        } finally {
            lock.unlock();
        }
    }
}
```

**Q: Explain the difference between `synchronized`, `ReentrantLock`, and `ReadWriteLock`.**

Sample Answer:
> "**`synchronized`:**
> - Built-in Java keyword, implicit lock/unlock
> - Simple to use, less error-prone (can't forget to unlock)
> - Limited: no timeout, no try-lock, can't interrupt waiting thread
> - Use for: Simple mutual exclusion where advanced features aren't needed
>
> **`ReentrantLock`:**
> - Explicit lock/unlock (must use try-finally)
> - Advanced features: `tryLock()`, `tryLock(timeout)`, `lockInterruptibly()`
> - Can create multiple `Condition` objects for fine-grained waiting
> - Fairness option (FIFO ordering of waiting threads)
> - Use for: Complex synchronization, need timeout/interruption, multiple conditions
>
> **`ReadWriteLock`:**
> - Two locks: read lock (shared) and write lock (exclusive)
> - Multiple readers can hold read lock simultaneously
> - Writer needs exclusive access (no readers or other writers)
> - Use for: Read-heavy workloads where writes are infrequent
>
> **Example scenario:**
> A cache with frequent reads and rare updates would benefit from `ReadWriteLock`—readers don't block each other. A simple counter would use `synchronized` or `AtomicInteger`. A complex workflow with multiple wait conditions would use `ReentrantLock` with multiple `Condition` objects."

**Q: What is a deadlock? How do you prevent it?**

Sample Answer:
> "Deadlock occurs when two or more threads are blocked forever, each waiting for a resource held by another.
>
> **Four necessary conditions (all must be true):**
> 1. **Mutual exclusion:** Resources can't be shared
> 2. **Hold and wait:** Thread holds one resource while waiting for another
> 3. **No preemption:** Resources can't be forcibly taken
> 4. **Circular wait:** Thread A waits for B, B waits for A
>
> **Prevention strategies:**
>
> 1. **Lock ordering:** Always acquire locks in the same global order
>    ```java
>    // Always lock lower ID first
>    if (account1.id < account2.id) {
>        synchronized(account1) { synchronized(account2) { transfer(); }}
>    } else {
>        synchronized(account2) { synchronized(account1) { transfer(); }}
>    }
>    ```
>
> 2. **Lock timeout:** Use `tryLock(timeout)` instead of blocking forever
>    ```java
>    if (lock1.tryLock(1, TimeUnit.SECONDS)) {
>        try {
>            if (lock2.tryLock(1, TimeUnit.SECONDS)) {
>                try { /* work */ } finally { lock2.unlock(); }
>            }
>        } finally { lock1.unlock(); }
>    }
>    ```
>
> 3. **Single lock:** Use one coarse-grained lock instead of multiple fine-grained locks (trade-off: less concurrency)
>
> 4. **Lock-free algorithms:** Use atomic operations (CAS) where possible
>
> **Detection:** Thread dumps (`jstack`), monitoring tools, or programmatic detection via `ThreadMXBean.findDeadlockedThreads()`"

---

## Part 3: System Design Questions

### Q: Design a distributed query engine (like Spark SQL / Presto)

**Sample Answer Framework:**

**Requirements:**
- SQL queries over petabyte-scale data
- Sub-minute latency for most queries
- Support for multiple data sources (S3, HDFS, Delta Lake)
- Concurrent queries from hundreds of users

**High-Level Architecture:**
```
Clients (JDBC/REST/Notebooks)
           ↓
     Query Gateway (Load Balancer)
           ↓
     Coordinator Nodes
     ├── Parser (SQL → AST)
     ├── Analyzer (resolve tables, columns)
     ├── Optimizer (logical → physical plan)
     └── Scheduler (distribute tasks)
           ↓
     Worker Nodes (N instances)
     ├── Task Executor
     ├── Memory Manager
     ├── Shuffle Service
     └── Connector Interface
           ↓
     Storage (S3, HDFS, Delta Lake)
```

**Key Components:**

1. **Query Planning:**
   - Parse SQL to AST
   - Resolve table/column references against metastore
   - Apply rule-based optimizations (predicate pushdown, column pruning)
   - Cost-based optimization for join ordering using statistics
   - Generate distributed execution plan

2. **Execution Model:**
   - **Volcano model:** Pull-based iteration through operators
   - **Vectorized execution:** Process batches of rows for CPU efficiency
   - **Code generation:** Compile hot paths to JVM bytecode

3. **Shuffle:**
   - Hash partition data for joins/aggregations
   - External shuffle service for fault tolerance
   - Compression and encryption in transit

4. **Memory Management:**
   - Memory pools for execution vs. storage
   - Spill to disk when memory exhausted
   - Off-heap memory for large aggregations

5. **Fault Tolerance:**
   - Task retry on worker failure
   - Lineage-based recomputation (Spark) vs. query retry (Presto)
   - Checkpointing for very long queries

**Databricks-Specific Optimizations:**
- Photon engine (C++ native execution)
- Delta Lake integration (data skipping, Z-Order)
- Adaptive Query Execution
- Dynamic cluster scaling

---

### Q: Design a real-time feature store for ML

**Sample Answer:**

**Requirements Clarification:**
- Feature freshness? (milliseconds to hours)
- Query pattern? (point lookups by entity ID)
- Scale? (millions of entities, thousands of features)
- Consistency? (eventual OK for most features)

**Architecture:**
```
Feature Sources
├── Streaming (Kafka) → Spark Streaming → Online Store (Redis/DynamoDB)
├── Batch (Delta Lake) → Spark Batch → Offline Store (Delta Lake)
└── Real-time (API) → Direct Write → Online Store

Feature Registry (Metadata)
├── Feature definitions
├── Data sources
├── Transformations
└── Lineage

Serving Layer
├── Online: Low-latency point lookups (p99 < 10ms)
├── Offline: Batch retrieval for training (Delta Lake)
└── Streaming: Feature vectors for real-time inference
```

**Key Design Decisions:**

1. **Online vs. Offline Stores:**
   - **Online (Redis/DynamoDB):** Latest feature values, optimized for point lookups
   - **Offline (Delta Lake):** Historical features, optimized for batch reads with time travel

2. **Feature Computation:**
   - **Batch features:** Computed on schedule (hourly/daily), written to both stores
   - **Streaming features:** Computed continuously, written to online store, periodically synced to offline
   - **On-demand features:** Computed at request time (use sparingly)

3. **Point-in-Time Correctness:**
   - For training, must retrieve features as they were at prediction time
   - Use Delta Lake time travel or explicit timestamp columns
   - Prevent data leakage from future features

4. **Feature Registry:**
   - Central catalog of all features with metadata
   - Versioning for feature definitions
   - Lineage tracking for debugging and compliance

**Trade-offs:**
- Consistency: Eventual consistency between online/offline acceptable?
- Freshness vs. cost: Real-time features expensive, batch features cheap
- Flexibility vs. performance: Generic schema vs. denormalized per-model tables

---

## Part 4: Coding Questions

### Example 1: IP to CIDR (Databricks Classic)

```python
def ip_to_cidr(ip: str, n: int) -> list[str]:
    """Convert IP range starting at ip covering n addresses to minimal CIDR blocks."""
    def ip_to_int(ip: str) -> int:
        parts = list(map(int, ip.split('.')))
        return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

    def int_to_ip(num: int) -> str:
        return f"{(num >> 24) & 255}.{(num >> 16) & 255}.{(num >> 8) & 255}.{num & 255}"

    result = []
    start = ip_to_int(ip)

    while n > 0:
        # Find the lowest set bit in start (determines max block size from this IP)
        lowest_bit = start & (-start) if start else (1 << 32)

        # Find largest power of 2 <= n
        max_size = 1
        while max_size * 2 <= n:
            max_size *= 2

        # Block size is minimum of what alignment allows and what we need
        block_size = min(lowest_bit, max_size)

        # Calculate prefix length: 32 - log2(block_size)
        prefix = 32
        temp = block_size
        while temp > 1:
            prefix -= 1
            temp //= 2

        result.append(f"{int_to_ip(start)}/{prefix}")
        start += block_size
        n -= block_size

    return result
```

### Example 2: Rate Limiter (Concurrency)

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class RateLimiter {
    private final int maxRequests;
    private final long windowMs;
    private final ConcurrentHashMap<String, TokenBucket> buckets;

    public RateLimiter(int maxRequests, long windowMs) {
        this.maxRequests = maxRequests;
        this.windowMs = windowMs;
        this.buckets = new ConcurrentHashMap<>();
    }

    public boolean allowRequest(String clientId) {
        TokenBucket bucket = buckets.computeIfAbsent(clientId,
            k -> new TokenBucket(maxRequests, windowMs));
        return bucket.tryConsume();
    }

    private static class TokenBucket {
        private final int maxTokens;
        private final long refillIntervalMs;
        private final AtomicLong tokens;
        private final AtomicLong lastRefillTime;

        TokenBucket(int maxTokens, long windowMs) {
            this.maxTokens = maxTokens;
            this.refillIntervalMs = windowMs / maxTokens;
            this.tokens = new AtomicLong(maxTokens);
            this.lastRefillTime = new AtomicLong(System.currentTimeMillis());
        }

        boolean tryConsume() {
            refill();
            while (true) {
                long current = tokens.get();
                if (current <= 0) return false;
                if (tokens.compareAndSet(current, current - 1)) return true;
            }
        }

        private void refill() {
            long now = System.currentTimeMillis();
            long last = lastRefillTime.get();
            long elapsed = now - last;
            long tokensToAdd = elapsed / refillIntervalMs;

            if (tokensToAdd > 0 && lastRefillTime.compareAndSet(last, last + tokensToAdd * refillIntervalMs)) {
                long current = tokens.get();
                long newTokens = Math.min(maxTokens, current + tokensToAdd);
                tokens.set(newTokens);
            }
        }
    }
}
```

### Example 3: Variable-Size Tic-Tac-Toe

```python
class TicTacToe:
    def __init__(self, n: int):
        self.n = n
        self.rows = [0] * n
        self.cols = [0] * n
        self.diag = 0
        self.anti_diag = 0

    def move(self, row: int, col: int, player: int) -> int:
        """
        Player makes a move. Returns winner (1 or 2) or 0 if no winner yet.
        Player 1 adds +1, Player 2 adds -1.
        """
        delta = 1 if player == 1 else -1
        target = self.n if player == 1 else -self.n

        self.rows[row] += delta
        self.cols[col] += delta

        if row == col:
            self.diag += delta
        if row + col == self.n - 1:
            self.anti_diag += delta

        if (self.rows[row] == target or
            self.cols[col] == target or
            self.diag == target or
            self.anti_diag == target):
            return player

        return 0
```

### Example 4: Merge K Sorted Iterators (Data Platform Relevant)

```python
import heapq
from typing import Iterator, List, TypeVar

T = TypeVar('T')

def merge_k_sorted_iterators(iterators: List[Iterator[T]]) -> Iterator[T]:
    """
    Merge K sorted iterators into a single sorted iterator.
    Memory efficient - only holds K elements at a time.
    """
    heap = []

    # Initialize heap with first element from each iterator
    for i, it in enumerate(iterators):
        try:
            val = next(it)
            heapq.heappush(heap, (val, i))
        except StopIteration:
            pass

    while heap:
        val, idx = heapq.heappop(heap)
        yield val

        try:
            next_val = next(iterators[idx])
            heapq.heappush(heap, (next_val, idx))
        except StopIteration:
            pass

# Usage: merge sorted files without loading all into memory
# iterators = [iter(open(f)) for f in sorted_files]
# for line in merge_k_sorted_iterators(iterators):
#     process(line)
```

---

## Part 5: Questions to Ask Your Interviewers

### For Engineers:
- "What's the most interesting technical challenge the team has tackled recently?"
- "How does the team balance open-source contributions with proprietary development?"
- "What does on-call look like? How are incidents handled?"

### For Hiring Manager:
- "What does success look like in the first 6 months for this role?"
- "How does the team prioritize between reliability, performance, and new features?"
- "What's the team's biggest technical bet for the next year?"

### About Culture:
- "Can you give an example of 'first principles thinking' in action at Databricks?"
- "How does Databricks maintain startup speed at its current scale?"

---

## Key Preparation Reminders

1. **Concurrency is critical:** Practice multithreading problems (unique to Databricks interviews)
2. **Know Delta Lake deeply:** ACID transactions, time travel, optimization (ZORDER, OPTIMIZE)
3. **Spark internals matter:** Catalyst optimizer, shuffle, AQE, memory management
4. **References are heavily weighted:** Prepare 1 manager + 2 senior peers
5. **System design via Google Docs:** Practice designing without a whiteboard
6. **First principles:** Be ready to explain *why*, not just *how*

---

## Sources

- [Databricks Interview Process - interviewing.io](https://interviewing.io/databricks-interview-questions)
- [Databricks Interview Guide - Prepfully](https://prepfully.com/interview-guides/databricks-software-engineer)
- [Databricks Interview Process - Exponent](https://www.tryexponent.com/blog/databricks-interview-process)
- [Databricks Interview Questions - DataCamp](https://www.datacamp.com/blog/databricks-interview-questions)
- [Databricks Culture & Values](https://www.databricks.com/company/careers/culture)
- [Databricks Values Blog](https://www.databricks.com/blog/2022/11/15/values-define-databricks-culture.html)
- [Databricks Salaries - Levels.fyi](https://www.levels.fyi/companies/databricks/salaries/software-engineer)
- [Databricks Interview Questions - InterviewQuery](https://www.interviewquery.com/interview-guides/databricks)
- [50 Databricks Interview Questions - Medium](https://medium.com/tech-with-abhishek/50-databricks-interview-questions-answers-the-ultimate-guide-2ccf8f25cde8)
