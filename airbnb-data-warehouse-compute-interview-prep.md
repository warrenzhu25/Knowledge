# Airbnb Staff Software Engineer, Data Warehouse Compute - Interview Preparation Guide

## Position Overview

- **Role:** Staff Software Engineer, Data Warehouse Compute
- **Location:** United States (Remote Eligible, excludes AK, MS, ND)
- **Compensation:** $204,000–$255,000 base + bonus + equity + Employee Travel Credits
- **Requirements:** 10+ years in data infrastructure, big data technologies expertise

---

## Interview Process (4 Stages)

| Stage | Duration | Focus |
|-------|----------|-------|
| 1. Recruiter Screen | 30 min | Background, motivation, role expectations |
| 2. Technical Phone Screen | 1 hour | Live coding on CoderPad (working code required) |
| 3. Onsite | 5-7 hours | Coding, system design, behavioral, culture fit |
| 4. Team Matching | Variable | 1-4 hiring manager conversations |

**Timeline:** 2-5 weeks typical, up to 8+ weeks possible

### Onsite Breakdown
- **Coding (1-3 hours):** Must write working, runnable code—no pseudocode
- **System Design (1 hour):** Large-scale distributed systems
- **Behavioral (1 hour):** Past projects, impact, teamwork
- **Host Interviews (2 hours):** Cultural fit with non-engineers

---

## Part 1: Airbnb Core Values & Cultural Fit

### The Four Core Values

**1. Champion the Mission**
> "Create a world where anyone can belong anywhere"

**2. Be a Host**
> Be caring, open, and encouraging to everyone you work with

**3. Embrace the Adventure**
> Be curious, optimistic, and driven to grow

**4. Be a Cereal Entrepreneur**
> Bring bold ideas; reference to founders selling cereal boxes to fund Airbnb

---

### Cultural Fit Questions (Host Interviews)

**Q: Why Airbnb?**

Sample Answer:
> "I'm drawn to Airbnb because of the unique intersection of engineering challenge and human impact. The data infrastructure at Airbnb's scale—millions of listings, hundreds of millions of guests—requires solving genuinely hard distributed systems problems. But what makes it meaningful is that every optimization directly improves someone's travel experience or helps a host succeed. I also appreciate Airbnb's engineering culture of ownership—engineers here don't just write code, they own outcomes. That's the environment where I do my best work."

**Q: Tell me about a time you went above and beyond to help a teammate or user.**

Sample Answer (STAR format):
> **Situation:** A junior engineer on my team was struggling to debug a Spark job that kept failing in production with OOM errors.
>
> **Task:** It wasn't my direct responsibility, but they'd been stuck for two days and the pipeline was business-critical.
>
> **Action:** I spent an afternoon pair-programming with them. We traced the issue to a broadcast join on a table that had grown 10x since the job was written. I didn't just fix it—I walked them through how to analyze Spark execution plans and identify memory issues. I also created a runbook for the team on common Spark memory problems.
>
> **Result:** The job was fixed, and more importantly, that engineer went on to debug similar issues independently. They told me later it was a turning point in their confidence with distributed systems.

**Q: Describe a time you embraced an adventure or took a risk professionally.**

Sample Answer:
> "When my previous company decided to migrate from on-prem Hadoop to cloud-native architecture, I volunteered to lead the technical design despite never having done a migration at that scale. It was a calculated risk—I knew distributed systems fundamentals, but cloud-native patterns were new to me. I spent nights learning, made some mistakes early (like underestimating data transfer costs), but ultimately delivered a system that was 40% cheaper and 3x faster. The adventure taught me that growth comes from being uncomfortable, and that thorough preparation can de-risk bold moves."

**Q: Give an example of a bold idea you championed that others initially doubted.**

Sample Answer:
> "I proposed replacing our batch ETL pipelines with a streaming-first architecture using Kafka and Spark Structured Streaming. The team was skeptical—batch had worked for years, and streaming seemed like over-engineering. I built a proof-of-concept showing we could reduce data latency from 4 hours to 5 minutes while actually simplifying the codebase by eliminating complex backfill logic. I presented the ROI: faster data meant faster business decisions. After seeing the prototype, the team bought in. We rolled it out over 6 months and it's now the standard pattern for new pipelines."

---

## Part 2: Technical Questions - Big Data & Distributed Systems

### Apache Spark

**Q: Explain RDDs, DataFrames, and Datasets. When would you use each?**

Sample Answer:
> "**RDDs (Resilient Distributed Datasets)** are the foundational abstraction—immutable, distributed collections with explicit control over partitioning and transformations. Use RDDs when you need fine-grained control or are working with unstructured data.
>
> **DataFrames** add a schema and columnar storage, enabling Catalyst optimizer to generate efficient execution plans. They're best for structured data and SQL-like operations—most production workloads should use DataFrames.
>
> **Datasets** combine RDD type-safety with DataFrame optimization. They're useful in Scala/Java when you want compile-time type checking on domain objects.
>
> For this role at Airbnb, I'd default to DataFrames (or Spark SQL) for most batch processing, dropping to RDDs only for specific optimization needs or complex custom logic that doesn't map well to SQL."

**Q: What causes Spark shuffle operations and how do you optimize them?**

Sample Answer:
> "Shuffles occur when data must be redistributed across partitions—triggered by operations like `groupByKey`, `reduceByKey`, `join`, `distinct`, and `repartition`. They're expensive because they involve serialization, network I/O, and disk writes.
>
> **Optimization strategies:**
> 1. **Reduce data before shuffle:** Use `reduceByKey` instead of `groupByKey`—it combines locally before shuffling
> 2. **Broadcast small tables:** For joins where one side is small (<10MB default), use broadcast joins to avoid shuffle entirely
> 3. **Partition alignment:** If joining repeatedly on the same key, pre-partition both datasets identically
> 4. **Bucketing:** For Hive tables, bucket by join keys to eliminate shuffle at query time
> 5. **Tune parallelism:** Set `spark.sql.shuffle.partitions` appropriately—default 200 is often too low for large datasets
> 6. **Salting:** For skewed keys, add a random prefix to spread load, then aggregate in two stages"

**Q: How does Spark achieve fault tolerance?**

Sample Answer:
> "Spark achieves fault tolerance through **lineage**. Each RDD (or DataFrame) tracks the sequence of transformations that created it. If a partition is lost (worker failure), Spark can recompute just that partition from the parent data using the lineage graph.
>
> This is more efficient than replication because:
> - No storage overhead during normal operation
> - Only failed partitions are recomputed, not entire datasets
>
> For narrow transformations (map, filter), recomputation is local. For wide transformations (shuffle), Spark writes shuffle files to disk as checkpoints—if a post-shuffle partition fails, it can read from shuffle files rather than recomputing everything upstream.
>
> Additionally, you can explicitly checkpoint RDDs to reliable storage (HDFS/S3) to truncate lineage for very long pipelines."

**Q: Explain the difference between `coalesce()` and `repartition()`.**

Sample Answer:
> "Both change the number of partitions, but they work differently:
>
> **`coalesce(n)`:** Decreases partitions by combining existing ones without a full shuffle. It's optimized for reducing partitions—you can't increase partitions with coalesce. Use it when writing output to fewer files or after filtering reduces data significantly.
>
> **`repartition(n)`:** Performs a full shuffle to create exactly n partitions with roughly equal data distribution. Can increase or decrease partitions. Use when you need better parallelism or when data is skewed.
>
> **Practical example:** After filtering a 1000-partition dataset down to 1% of records, use `coalesce(10)` to avoid writing 1000 tiny files. If you then need to join this with another large dataset, `repartition()` on the join key to ensure even distribution."

---

### Hadoop & YARN

**Q: Explain YARN architecture and how it manages resources.**

Sample Answer:
> "YARN (Yet Another Resource Negotiator) separates resource management from job scheduling:
>
> **Components:**
> - **ResourceManager (RM):** Cluster-wide master that allocates resources. Has a Scheduler (allocates containers) and ApplicationManager (accepts job submissions)
> - **NodeManager (NM):** Per-node agent that manages containers, monitors resource usage, reports to RM
> - **ApplicationMaster (AM):** Per-application process that negotiates resources and coordinates task execution
>
> **Flow:**
> 1. Client submits application to RM
> 2. RM allocates container for AM
> 3. AM requests containers from RM for tasks
> 4. AM coordinates task execution on allocated containers
> 5. NMs report container status to RM
>
> YARN enables multiple frameworks (Spark, MapReduce, Flink) to share cluster resources, with pluggable schedulers (Fair, Capacity) for multi-tenant allocation."

**Q: What's the difference between HDFS block size and Spark partition size?**

Sample Answer:
> "**HDFS block size** (default 128MB) is a storage concept—it determines how files are split and replicated across DataNodes. It's set at file write time and affects data locality.
>
> **Spark partition** is a processing concept—it determines parallelism. When Spark reads from HDFS, it typically creates one partition per block (or per split). But partitions can be changed via `repartition`/`coalesce` and are affected by operations throughout the job.
>
> **Key insight:** They're related but independent. A 1GB file with 128MB blocks creates ~8 HDFS blocks. Spark might read this as 8 partitions initially, but after a shuffle with `spark.sql.shuffle.partitions=200`, you'd have 200 partitions regardless of original block count.
>
> For optimal performance, align them—if your Spark executors have 4 cores, aim for partitions sized so each task processes reasonable data (100MB-1GB typically)."

---

### Presto/Trino

**Q: When would you choose Presto/Trino over Spark?**

Sample Answer:
> "**Choose Presto/Trino for:**
> - Interactive, ad-hoc queries where latency matters (seconds to minutes)
> - SQL-only workloads—Presto's MPP architecture is optimized for SQL
> - Federated queries across multiple data sources (Hive, MySQL, Cassandra in one query)
> - BI tool integration—better JDBC/ODBC support for Tableau, Looker, etc.
>
> **Choose Spark for:**
> - Complex ETL with programmatic logic (Python/Scala UDFs)
> - Iterative algorithms (ML training)
> - Long-running batch jobs
> - Streaming workloads
> - When you need to write results back to storage
>
> At Airbnb's scale, both have their place: Presto for analyst queries and dashboards, Spark for data pipelines and heavy transformations. The Data Warehouse Compute team likely optimizes both—Presto for query latency, Spark for throughput."

**Q: How does Presto's architecture differ from Spark?**

Sample Answer:
> "**Presto** uses a pure MPP (Massively Parallel Processing) architecture:
> - Single coordinator parses, plans, and schedules queries
> - Workers execute query fragments in parallel
> - All processing is in-memory with streaming between stages
> - No built-in fault tolerance—if a worker dies, query fails
> - Optimized for low-latency, short-running queries
>
> **Spark** uses a DAG-based batch architecture:
> - Driver creates execution plan as a DAG of stages
> - Executors run tasks within stages
> - Intermediate results can spill to disk
> - Fault tolerant via lineage-based recomputation
> - Optimized for throughput on long-running jobs
>
> The key difference: Presto sacrifices fault tolerance for latency, Spark sacrifices latency for reliability and flexibility. For a 10-second dashboard query, Presto wins. For a 2-hour ETL job, Spark's fault tolerance is essential."

---

### Distributed Systems Fundamentals

**Q: Explain the CAP theorem and how it applies to data infrastructure.**

Sample Answer:
> "CAP theorem states that in a distributed system, you can only guarantee two of three properties:
> - **Consistency:** Every read receives the most recent write
> - **Availability:** Every request receives a response
> - **Partition Tolerance:** System operates despite network partitions
>
> Since network partitions are inevitable, the real choice is between CP (consistent but may reject requests during partitions) and AP (available but may return stale data).
>
> **Practical applications:**
> - **HDFS:** CP—NameNode ensures consistency, unavailable during failover
> - **Cassandra:** AP by default—always accepts writes, eventual consistency
> - **HBase:** CP—strong consistency, may block during region server failures
> - **Data warehouses (BigQuery, Redshift):** CP—prioritize query consistency
>
> For data warehouse compute at Airbnb, we'd typically want CP behavior—analysts expect consistent query results. But for real-time event ingestion, AP might be acceptable with eventual consistency."

**Q: How would you design a system to handle data skew in distributed processing?**

Sample Answer:
> "Data skew—where some partitions have disproportionately more data—causes stragglers and underutilized parallelism.
>
> **Detection:**
> - Monitor task duration variance in Spark UI
> - Check partition sizes via `df.groupBy(spark_partition_id()).count()`
> - Look for specific keys dominating (e.g., null values, popular users)
>
> **Solutions:**
>
> 1. **Salting:** Add random prefix to skewed keys
>    ```scala
>    // Instead of: df.groupBy(\"user_id\")
>    df.withColumn(\"salted_key\", concat(col(\"user_id\"), lit(\"_\"), (rand() * 10).cast(\"int\")))
>      .groupBy(\"salted_key\").agg(...)
>      .withColumn(\"user_id\", split(col(\"salted_key\"), \"_\")(0))
>      .groupBy(\"user_id\").agg(...)  // Second aggregation to combine
>    ```
>
> 2. **Broadcast joins:** If one side is small, broadcast it to avoid shuffle entirely
>
> 3. **Adaptive Query Execution (Spark 3+):** Enable `spark.sql.adaptive.enabled=true` and `spark.sql.adaptive.skewJoin.enabled=true` for automatic skew handling
>
> 4. **Isolate hot keys:** Process skewed keys separately with higher parallelism, union results
>
> 5. **Pre-aggregation:** For repeated aggregations, materialize pre-aggregated tables"

---

## Part 3: System Design Questions

### Q: Design a distributed query engine like Presto

**Framework:** Requirements → High-Level Design → Deep Dive → Trade-offs

**Sample Answer Structure:**

**Requirements Clarification:**
- Query types? (SELECT, aggregations, joins)
- Latency target? (sub-second for simple, minutes for complex)
- Data sources? (HDFS, S3, databases)
- Concurrency? (hundreds of concurrent queries)
- Data size? (petabytes)

**High-Level Architecture:**
```
Clients (JDBC/REST)
       ↓
   Coordinator
   - Query Parser (SQL → AST)
   - Query Planner (logical → physical plan)
   - Query Optimizer (cost-based optimization)
   - Query Scheduler (distribute to workers)
       ↓
   Workers (N nodes)
   - Task Executor (process data splits)
   - Memory Manager (spill to disk if needed)
   - Connector Interface (read from data sources)
       ↓
   Data Sources (HDFS, S3, Hive Metastore, MySQL, etc.)
```

**Key Design Decisions:**

1. **Query Planning:**
   - Parse SQL to AST, convert to logical plan
   - Apply rule-based optimizations (predicate pushdown, projection pruning)
   - Cost-based optimization for join ordering using table statistics
   - Generate distributed physical plan with stages and data exchanges

2. **Execution Model:**
   - Pipeline execution: operators stream data between stages
   - Columnar processing: batch vectors of rows for CPU cache efficiency
   - Memory management: reservation system with spill-to-disk fallback

3. **Data Distribution:**
   - Splits: divide data sources into parallel units of work
   - Shuffles: hash-partition data for joins and aggregations
   - Broadcast: replicate small tables to all workers

4. **Fault Tolerance Trade-off:**
   - Option A: No fault tolerance (Presto approach)—query fails, user retries
   - Option B: Checkpoint intermediate results (Spark approach)—higher latency
   - For interactive queries, A is acceptable; for long ETL, need B

**Scalability:**
- Coordinator is single point—scale via query routing to multiple coordinators
- Workers scale horizontally—add nodes, scheduler distributes load
- Separate compute and storage—workers are stateless, data in S3/HDFS

---

### Q: Design a real-time data warehouse with sub-second query latency

**Sample Answer:**

"Let me clarify the requirements:
- What's the data ingestion rate? (Let's assume 1M events/second)
- Query patterns? (Dashboard metrics, ad-hoc exploration)
- Freshness requirement? (Data available within 1 second of event)
- Query latency target? (p99 < 1 second for dashboard queries)

**Architecture:**

```
Event Sources → Kafka → Stream Processor (Flink/Spark Streaming)
                              ↓
                        Real-time Layer (Druid/Pinot/ClickHouse)
                              ↓
                        Query Router ← API/Dashboard
                              ↓
                        Batch Layer (BigQuery/Presto) ← Historical queries
```

**Layer Details:**

1. **Ingestion (Kafka):**
   - Partitioned by entity ID for ordering guarantees
   - Retention: 7 days for replay capability
   - Schema registry for evolution

2. **Stream Processing:**
   - Flink for exactly-once processing
   - Pre-aggregations: compute minutely/hourly rollups in stream
   - Late data handling: watermarks + allowed lateness window

3. **Real-time OLAP (Druid/Pinot):**
   - Column-oriented, optimized for aggregations
   - Segments partitioned by time, replicated for availability
   - Indexes: bitmap indexes for dimensions, roaring bitmaps for high cardinality
   - Query: sub-second for time-bounded aggregations

4. **Batch Layer:**
   - Full historical data in Parquet on S3
   - Presto/BigQuery for ad-hoc queries
   - Used when freshness isn't critical or query spans years

5. **Query Routing:**
   - Route based on time range and query complexity
   - Recent data (< 7 days) → real-time layer
   - Historical or complex → batch layer
   - Federate when necessary

**Trade-offs:**
- Complexity: Two systems to maintain
- Cost: Real-time OLAP is expensive per-GB vs. S3
- Consistency: Potential for temporary inconsistency between layers

For Airbnb's scale, I'd recommend this hybrid approach—real-time for operational dashboards (host earnings, booking rates), batch for deep analytics (yearly trends, ML features)."

---

## Part 4: Coding Questions

### Common Patterns at Airbnb

Airbnb coding interviews require **working, runnable code**—no pseudocode. Practice in Java or Scala for this role.

### Example 1: Two Sum (Warm-up)

```java
public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (seen.containsKey(complement)) {
            return new int[] { seen.get(complement), i };
        }
        seen.put(nums[i], i);
    }
    return new int[] {};
}
```

### Example 2: LRU Cache (Common for infra roles)

```java
class LRUCache {
    private final int capacity;
    private final Map<Integer, Node> cache;
    private final Node head, tail;

    class Node {
        int key, value;
        Node prev, next;
        Node(int k, int v) { key = k; value = v; }
    }

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.cache = new HashMap<>();
        head = new Node(0, 0);
        tail = new Node(0, 0);
        head.next = tail;
        tail.prev = head;
    }

    public int get(int key) {
        if (!cache.containsKey(key)) return -1;
        Node node = cache.get(key);
        moveToFront(node);
        return node.value;
    }

    public void put(int key, int value) {
        if (cache.containsKey(key)) {
            Node node = cache.get(key);
            node.value = value;
            moveToFront(node);
        } else {
            if (cache.size() >= capacity) {
                cache.remove(tail.prev.key);
                remove(tail.prev);
            }
            Node node = new Node(key, value);
            cache.put(key, node);
            addToFront(node);
        }
    }

    private void moveToFront(Node node) {
        remove(node);
        addToFront(node);
    }

    private void remove(Node node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void addToFront(Node node) {
        node.next = head.next;
        node.prev = head;
        head.next.prev = node;
        head.next = node;
    }
}
```

### Example 3: Find All Anagrams in a String (Sliding Window)

```java
public List<Integer> findAnagrams(String s, String p) {
    List<Integer> result = new ArrayList<>();
    if (s.length() < p.length()) return result;

    int[] pCount = new int[26];
    int[] sCount = new int[26];

    for (char c : p.toCharArray()) pCount[c - 'a']++;

    for (int i = 0; i < s.length(); i++) {
        sCount[s.charAt(i) - 'a']++;
        if (i >= p.length()) {
            sCount[s.charAt(i - p.length()) - 'a']--;
        }
        if (Arrays.equals(pCount, sCount)) {
            result.add(i - p.length() + 1);
        }
    }
    return result;
}
```

### Example 4: Merge K Sorted Lists (Heap)

```java
public ListNode mergeKLists(ListNode[] lists) {
    PriorityQueue<ListNode> heap = new PriorityQueue<>(
        (a, b) -> a.val - b.val
    );

    for (ListNode node : lists) {
        if (node != null) heap.offer(node);
    }

    ListNode dummy = new ListNode(0);
    ListNode current = dummy;

    while (!heap.isEmpty()) {
        ListNode smallest = heap.poll();
        current.next = smallest;
        current = current.next;
        if (smallest.next != null) {
            heap.offer(smallest.next);
        }
    }
    return dummy.next;
}
```

---

## Part 5: Questions to Ask Your Interviewers

### For Engineers:
- "What's the most interesting technical challenge the Data Warehouse Compute team has solved recently?"
- "How do you balance reliability improvements vs. new feature development?"
- "What's the on-call rotation like? How are incidents handled?"

### For Hiring Manager:
- "What does success look like for this role in the first 6-12 months?"
- "How does the team decide what to build vs. what to use from open source?"
- "What's the biggest scaling challenge you anticipate in the next year?"

### About Culture:
- "How does Airbnb's 'Be a Host' value show up in day-to-day engineering work?"
- "Can you give an example of a bold bet the data infrastructure team took?"

---

## Key Preparation Reminders

1. **Working code required:** Practice writing complete, runnable code in Java or Scala
2. **Culture fit is critical:** Prepare stories mapped to Airbnb's four core values
3. **Host interviews matter:** Non-engineers evaluate culture fit—fail these and you won't get an offer
4. **System design at scale:** Be ready to discuss petabyte-scale distributed systems
5. **Know your big data stack:** Deep expertise in Hadoop, Spark, Presto/Trino, YARN expected
6. **STAR format:** Structure behavioral answers with Situation, Task, Action, Result

---

## Sources

- [Airbnb Interview Process & Questions - interviewing.io](https://interviewing.io/airbnb-interview-questions)
- [Airbnb Software Engineer Interview Guide - IGotAnOffer](https://igotanoffer.com/blogs/tech/airbnb-software-engineer-interview)
- [Complete Airbnb Interview Guide - Prepfully](https://prepfully.com/interview-guides/airbnb-software-engineer)
- [Airbnb Interview Process - Exponent](https://www.tryexponent.com/blog/airbnb-interview-process)
- [Airbnb Interview Guide - InterviewQuery](https://www.interviewquery.com/interview-guides/airbnb)
- [Top Spark Interview Questions - DataCamp](https://www.datacamp.com/blog/top-spark-interview-questions)
- [Apache Spark Interview Questions - InterviewBit](https://www.interviewbit.com/spark-interview-questions/)
- [Data Engineering Interview Questions - GitHub](https://github.com/OBenner/data-engineering-interview-questions)
- [Presto Introduction - Alluxio](https://www.alluxio.io/learn/presto/introduction)
