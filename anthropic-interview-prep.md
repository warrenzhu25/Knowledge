# Anthropic Data Infrastructure Interview Preparation

A comprehensive guide covering coding challenges, system design, and distributed computing problems commonly asked in Anthropic technical interviews.

---

## Table of Contents

1. [LRU Cache with Disk Persistence](#1-lru-cache-with-disk-persistence)
2. [Stack Trace Parsing](#2-stack-trace-parsing)
3. [Task Management System (CodeSignal 4-Level)](#3-task-management-system)
4. [Bank System (CodeSignal 4-Level)](#4-bank-system)
5. [Web Crawler](#5-web-crawler)
6. [Prompt Engineering Playground (System Design)](#6-prompt-engineering-playground)
7. [Distributed Mode and Median](#7-distributed-mode-and-median)

---

# 1. LRU Cache with Disk Persistence

## Problem Statement

Implement an LRU (Least Recently Used) cache that supports disk persistence, so cached entries can be restored after a process restart.

### Option A: Class-based Interface

Implement `LRUCache(capacity, persist_path)` with:

| Method | Description |
|--------|-------------|
| `get(key)` | Return value if exists and mark as most-recently used; otherwise return `None` |
| `set(key, value)` | Insert/update entry, mark as most-recently used, evict LRU if over capacity |
| `load()` | Restore cache state from disk |
| `flush()` | Persist current state to disk |

### Option B: Decorator-based Interface

Implement `@persistent_lru_cache(maxsize, persist_path)`:

- Cache results of decorated function `f(*args, **kwargs)`
- On hit: return cached result, update LRU order
- On miss: compute, cache, evict by LRU if needed
- Persist to disk and restore on restart

### Constraints

- `1 <= capacity <= 10^5`
- Keys/values are serializable
- Target O(1) average get/set (excluding disk IO)

## Core Data Structure Design

```
┌─────────────────────────────────────────────────────────────┐
│                        LRU Cache                            │
├─────────────────────────────────────────────────────────────┤
│  HashMap: key -> Node                                       │
│  ┌─────┬─────┬─────┬─────┐                                 │
│  │  a  │  b  │  c  │  d  │  O(1) lookup                    │
│  └──┬──┴──┬──┴──┬──┴──┬──┘                                 │
│     │     │     │     │                                     │
│     ▼     ▼     ▼     ▼                                     │
│  Doubly Linked List (LRU order):                           │
│  HEAD <-> [d] <-> [c] <-> [b] <-> [a] <-> TAIL             │
│   ↑                                         ↑               │
│  MRU                                       LRU              │
│  (most recent)                        (least recent)        │
└─────────────────────────────────────────────────────────────┘
```

**Why this structure?**
- HashMap provides O(1) key lookup
- Doubly linked list provides O(1) insertion/deletion at any position
- Combined: O(1) for get, set, and eviction

## Solution: OrderedDict Implementation

```python
from collections import OrderedDict
import json
import os
import tempfile
import time
from typing import Any
from threading import Lock


class LRUCache:
    def __init__(self, capacity: int, persist_path: str):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.capacity = capacity
        self.persist_path = persist_path
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = Lock()
        self._write_count = 0
        self._flush_threshold = 100

    def get(self, key: str) -> Any | None:
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
                self.cache[key] = value

            self._write_count += 1
            if self._write_count >= self._flush_threshold:
                self._flush_internal()

    def flush(self) -> None:
        with self.lock:
            self._flush_internal()

    def _flush_internal(self) -> None:
        data = {
            "version": 1,
            "capacity": self.capacity,
            "entries": list(self.cache.items()),
            "timestamp": time.time()
        }

        dir_name = os.path.dirname(self.persist_path) or "."
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', dir=dir_name, delete=False, suffix='.tmp'
            ) as tmp_file:
                json.dump(data, tmp_file)
                tmp_path = tmp_file.name

            os.replace(tmp_path, self.persist_path)
            self._write_count = 0
        except Exception as e:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise IOError(f"Failed to flush cache: {e}")

    def load(self) -> bool:
        with self.lock:
            if not os.path.exists(self.persist_path):
                return False

            with open(self.persist_path, 'r') as f:
                data = json.load(f)

            self.cache = OrderedDict(data["entries"])
            while len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

            return True
```

## Manual Doubly-Linked List Implementation

```python
class Node:
    __slots__ = ['key', 'value', 'prev', 'next']

    def __init__(self, key: str = "", value: Any = None):
        self.key = key
        self.value = value
        self.prev: Node | None = None
        self.next: Node | None = None


class LRUCacheManual:
    def __init__(self, capacity: int, persist_path: str):
        self.capacity = capacity
        self.persist_path = persist_path
        self.cache: dict[str, Node] = {}
        self.head = Node()
        self.tail = Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _add_to_head(self, node: Node) -> None:
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def _remove_node(self, node: Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _move_to_head(self, node: Node) -> None:
        self._remove_node(node)
        self._add_to_head(node)

    def _pop_tail(self) -> Node:
        lru = self.tail.prev
        self._remove_node(lru)
        return lru

    def get(self, key: str) -> Any | None:
        if key not in self.cache:
            return None
        node = self.cache[key]
        self._move_to_head(node)
        return node.value

    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            if len(self.cache) >= self.capacity:
                lru = self._pop_tail()
                del self.cache[lru.key]

            node = Node(key, value)
            self.cache[key] = node
            self._add_to_head(node)
```

## Persistence Strategies

| Strategy | Pros | Cons | Best For |
|----------|------|------|----------|
| **Write-through** | Simple, durable | Heavy I/O, slow writes | Critical data, low write volume |
| **Buffered flush** | Balanced I/O | Complexity, some data loss risk | General use |
| **Periodic flush** | Predictable I/O | Timer complexity | Background caches |

## Key Interview Points

1. **Data structure choice**: HashMap + Doubly-linked list (or OrderedDict) for O(1) operations
2. **Persistence strategy**: Trade-off between durability and performance
3. **Crash safety**: Atomic writes via temp file + rename
4. **LRU order restoration**: Store entries in order or with timestamps
5. **Thread safety**: Locking strategy for concurrent access

---

# 2. Stack Trace Parsing

## Problem Overview

Given stack trace samples as text or structured input, parse and analyze them. Common variations:

1. Parse raw stack trace text into structured frames
2. Aggregate multiple samples to find hot functions
3. Reconstruct execution timeline from samples
4. Detect recursion and cycles
5. Group and deduplicate similar traces
6. **Convert stack samples to trace events** (Anthropic classic)

## Variation 1: Parse Raw Stack Trace

```python
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Frame:
    file: str
    line: int
    function: str
    code: Optional[str] = None


@dataclass
class ParsedStackTrace:
    frames: list[Frame]
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None


def parse_python_stacktrace(text: str) -> ParsedStackTrace:
    lines = text.strip().split('\n')
    frames = []
    exception_type = None
    exception_message = None

    frame_pattern = re.compile(r'^\s*File "([^"]+)", line (\d+), in (\S+)')
    exception_pattern = re.compile(r'^(\w+(?:\.\w+)*(?:Error|Exception)?): (.*)$')

    i = 0
    while i < len(lines):
        line = lines[i]
        match = frame_pattern.match(line)
        if match:
            file_path, line_num, func_name = match.groups()
            code = None
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith('    ') and not frame_pattern.match(next_line):
                    code = next_line.strip()
                    i += 1

            frames.append(Frame(file=file_path, line=int(line_num), function=func_name, code=code))

        exc_match = exception_pattern.match(line)
        if exc_match:
            exception_type, exception_message = exc_match.groups()

        i += 1

    return ParsedStackTrace(frames=frames, exception_type=exception_type, exception_message=exception_message)
```

## Variation 6: Convert Stack Samples to Trace Events (Anthropic Classic)

Sampling profilers periodically capture the entire call stack. Convert these samples into start/end events.

```python
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    START = "start"
    END = "end"


@dataclass
class Sample:
    timestamp: float
    stack: list[str]


@dataclass
class TraceEvent:
    timestamp: float
    event_type: EventType
    function: str
    depth: int


def samples_to_trace_events(samples: list[Sample]) -> list[TraceEvent]:
    """
    Convert stack samples to trace events.

    Algorithm:
    1. For first sample: emit START for all functions (outer to inner)
    2. For each subsequent sample:
       a. Find common prefix with previous sample
       b. Emit END events for removed functions (inner to outer)
       c. Emit START events for new functions (outer to inner)
    """
    if not samples:
        return []

    events: list[TraceEvent] = []
    prev_stack: list[str] = []

    for sample in samples:
        curr_stack = sample.stack
        timestamp = sample.timestamp

        # Find common prefix length
        common_len = 0
        for i in range(min(len(prev_stack), len(curr_stack))):
            if prev_stack[i] == curr_stack[i]:
                common_len = i + 1
            else:
                break

        # Emit END events (inner to outer)
        for depth in range(len(prev_stack) - 1, common_len - 1, -1):
            events.append(TraceEvent(timestamp, EventType.END, prev_stack[depth], depth))

        # Emit START events (outer to inner)
        for depth in range(common_len, len(curr_stack)):
            events.append(TraceEvent(timestamp, EventType.START, curr_stack[depth], depth))

        prev_stack = curr_stack.copy()

    return events
```

## Debouncing: Filter Short-Lived Functions

```python
@dataclass
class FrameTracker:
    first_seen: float = 0.0
    consecutive_count: int = 0
    emitted: bool = False


def samples_to_debounced_events(samples: list[Sample], min_consecutive: int = 2) -> list[TraceEvent]:
    """Only emit events if a frame appears in N consecutive samples."""
    if not samples or min_consecutive < 1:
        return []

    events: list[TraceEvent] = []
    active_trackers: dict[tuple[int, tuple[str, ...]], FrameTracker] = {}

    for sample in samples:
        curr_stack = sample.stack
        timestamp = sample.timestamp

        current_frames: set[tuple[int, tuple[str, ...]]] = set()
        for depth in range(len(curr_stack)):
            path = tuple(curr_stack[:depth + 1])
            frame_key = (depth, path)
            current_frames.add(frame_key)

        # Check frames no longer present
        frames_to_remove = []
        for frame_key, tracker in active_trackers.items():
            if frame_key not in current_frames:
                if tracker.emitted:
                    depth, path = frame_key
                    events.append(TraceEvent(timestamp, EventType.END, path[-1], depth))
                frames_to_remove.append(frame_key)

        for key in frames_to_remove:
            del active_trackers[key]

        # Update trackers for current frames
        for frame_key in current_frames:
            depth, path = frame_key

            if frame_key in active_trackers:
                active_trackers[frame_key].consecutive_count += 1
                tracker = active_trackers[frame_key]
                if not tracker.emitted and tracker.consecutive_count >= min_consecutive:
                    events.append(TraceEvent(tracker.first_seen, EventType.START, path[-1], depth))
                    tracker.emitted = True
            else:
                active_trackers[frame_key] = FrameTracker(first_seen=timestamp, consecutive_count=1)

    return events
```

## Key Interview Insights

1. **Position matters**: Due to recursion, same function can appear multiple times. Compare by position.
2. **Order of events matters**: END events inner-to-outer, START events outer-to-inner
3. **Common prefix optimization**: Only emit events for what changed

---

# 3. Task Management System

## Problem Overview

A classic Anthropic CodeSignal assessment with 4 progressive levels.

**Time limit:** 90 minutes for all 4 levels
**Target:** Complete at least Level 3 with all tests passing

## Level 1: Basic CRUD

| Method | Description |
|--------|-------------|
| `addTask(timestamp, name, priority) → String` | Create task, return unique ID |
| `updateTask(timestamp, taskId, name, priority) → boolean` | Update task, return false if not found |
| `getTask(timestamp, taskId) → Optional<String>` | Return JSON string or empty if not found |

## Level 2: Search & Sort

| Method | Description |
|--------|-------------|
| `searchTasks(timestamp, nameFilter, maxResults) → List<String>` | Find tasks containing nameFilter |
| `listTasksSorted(timestamp, limit) → List<String>` | List all task IDs up to limit |

**Sorting Rules:**
1. Priority (High → Low, descending)
2. Creation order (Low IDs first, ascending)

## Level 3: Users & Assignments

| Method | Description |
|--------|-------------|
| `addUser(timestamp, userId, quota) → boolean` | Add user with task limit |
| `assignTask(timestamp, taskId, userId, finishTime) → boolean` | Assign task to user |
| `getUserTasks(timestamp, userId) → List<String>` | Get user's active tasks |

**Active window:** `start_time <= timestamp < finish_time`

## Level 4: Completion & History

| Method | Description |
|--------|-------------|
| `completeTask(timestamp, taskId, userId) → boolean` | Mark active task as done |
| `getOverdueAssignments(timestamp, userId) → List<String>` | List expired incomplete tasks |

## Complete Solution

```python
from typing import Optional
from dataclasses import dataclass


@dataclass
class Assignment:
    task_id: str
    user_id: str
    start_time: int
    finish_time: int
    completed: bool = False


class Task:
    def __init__(self, task_id: str, name: str, priority: int):
        self.task_id = task_id
        self.name = name
        self.priority = priority


class User:
    def __init__(self, user_id: str, quota: int):
        self.user_id = user_id
        self.quota = quota
        self.assignments: list[Assignment] = []


class TaskManagementSystem:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.task_counter = 0
        self.creation_order: dict[str, int] = {}
        self.users: dict[str, User] = {}

    def add_task(self, timestamp: int, name: str, priority: int) -> str:
        self.task_counter += 1
        task_id = f"task_id_{self.task_counter}"
        self.tasks[task_id] = Task(task_id, name, priority)
        self.creation_order[task_id] = self.task_counter
        return task_id

    def update_task(self, timestamp: int, task_id: str, name: str, priority: int) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].name = name
        self.tasks[task_id].priority = priority
        return True

    def get_task(self, timestamp: int, task_id: str) -> Optional[str]:
        if task_id not in self.tasks:
            return None
        task = self.tasks[task_id]
        return f'{{"name":"{task.name}","priority":{task.priority}}}'

    def search_tasks(self, timestamp: int, name_filter: str, max_results: int) -> list[str]:
        if max_results <= 0:
            return []
        matching = [tid for tid, task in self.tasks.items() if name_filter in task.name]
        matching.sort(key=lambda tid: (-self.tasks[tid].priority, self.creation_order[tid]))
        return matching[:max_results]

    def list_tasks_sorted(self, timestamp: int, limit: int) -> list[str]:
        if limit <= 0:
            return []
        task_ids = list(self.tasks.keys())
        task_ids.sort(key=lambda tid: (-self.tasks[tid].priority, self.creation_order[tid]))
        return task_ids[:limit]

    def add_user(self, timestamp: int, user_id: str, quota: int) -> bool:
        if user_id in self.users:
            return False
        self.users[user_id] = User(user_id, quota)
        return True

    def _get_active_count(self, user: User, timestamp: int) -> int:
        return sum(1 for a in user.assignments
                   if a.start_time <= timestamp < a.finish_time and not a.completed)

    def assign_task(self, timestamp: int, task_id: str, user_id: str, finish_time: int) -> bool:
        if task_id not in self.tasks or user_id not in self.users:
            return False
        user = self.users[user_id]
        if self._get_active_count(user, timestamp) >= user.quota:
            return False
        user.assignments.append(Assignment(task_id, user_id, timestamp, finish_time))
        return True

    def get_user_tasks(self, timestamp: int, user_id: str) -> list[str]:
        if user_id not in self.users:
            return []
        user = self.users[user_id]
        active = [a for a in user.assignments
                  if a.start_time <= timestamp < a.finish_time and not a.completed]
        active.sort(key=lambda a: (a.finish_time, a.start_time))
        return [a.task_id for a in active]

    def complete_task(self, timestamp: int, task_id: str, user_id: str) -> bool:
        if task_id not in self.tasks or user_id not in self.users:
            return False
        user = self.users[user_id]
        active = [a for a in user.assignments
                  if a.task_id == task_id and a.start_time <= timestamp < a.finish_time and not a.completed]
        if not active:
            return False
        active.sort(key=lambda a: a.start_time)
        active[0].completed = True
        return True

    def get_overdue_assignments(self, timestamp: int, user_id: str) -> list[str]:
        if user_id not in self.users:
            return []
        user = self.users[user_id]
        overdue = [a for a in user.assignments if a.finish_time <= timestamp and not a.completed]
        overdue.sort(key=lambda a: (a.finish_time, a.start_time))
        return [a.task_id for a in overdue]
```

## Common Pitfalls

1. **Off-by-one in Active Window:** Use `start_time <= timestamp < finish_time` (excludes finish_time)
2. **Forgetting Completed Flag:** Always check `and not a.completed`
3. **Not Tracking Creation Order:** Explicit tracking needed for deterministic sorting

---

# 4. Bank System

## Problem Overview

A classic Anthropic CodeSignal assessment with 4 progressive levels.

**Time limit:** 90 minutes for all 4 levels
**Key constant:** 24 hours = 86,400,000 milliseconds

## Level 1: Basic Operations

| Method | Description |
|--------|-------------|
| `create_account(timestamp, account_id) → bool` | Create new account |
| `deposit(timestamp, account_id, amount) → int \| None` | Add money to account |
| `transfer(timestamp, source_id, target_id, amount) → int \| None` | Move money between accounts |

## Level 2: Ranking Spenders

| Method | Description |
|--------|-------------|
| `top_spenders(timestamp, n) → list[str]` | Top n accounts by spending |

Sort by: Total outgoing DESC, Account ID ASC

## Level 3: Payments and Cashback

| Method | Description |
|--------|-------------|
| `pay(timestamp, account_id, amount) → str \| None` | Make payment, returns payment ID |
| `get_payment_status(timestamp, account_id, payment) → str \| None` | Check payment status |

**Cashback:** `floor(amount * 0.02)` arrives at `timestamp + 86,400,000`

## Level 4: Merging and History

| Method | Description |
|--------|-------------|
| `merge_accounts(timestamp, id_1, id_2) → bool` | Merge account 2 into account 1 |
| `get_balance(timestamp, account_id, time_at) → int \| None` | Get balance at specific time |

## Complete Solution

```python
from dataclasses import dataclass


@dataclass
class Payment:
    payment_id: str
    account_id: str
    amount: int
    timestamp: int
    cashback: int
    cashback_applied: bool = False


class Account:
    def __init__(self, account_id: str, created_at: int):
        self.account_id = account_id
        self.balance = 0
        self.created_at = created_at
        self.total_outgoing = 0
        self.balance_history: list[tuple[int, int]] = []
        self.deleted_at: int | None = None


class BankSystem:
    TWENTY_FOUR_HOURS = 86_400_000

    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.payments: dict[str, Payment] = {}
        self.payment_counter = 0
        self.payment_owner: dict[str, str] = {}
        self.deleted_accounts: dict[str, list[Account]] = {}

    def _process_pending_cashback(self, timestamp: int) -> None:
        for payment in self.payments.values():
            if payment.cashback_applied:
                continue
            cashback_time = payment.timestamp + self.TWENTY_FOUR_HOURS
            if timestamp >= cashback_time:
                owner_id = self.payment_owner.get(payment.payment_id, payment.account_id)
                if owner_id in self.accounts:
                    self.accounts[owner_id].balance += payment.cashback
                    self._record_balance(owner_id, cashback_time)
                payment.cashback_applied = True

    def _record_balance(self, account_id: str, timestamp: int) -> None:
        if account_id in self.accounts:
            account = self.accounts[account_id]
            account.balance_history.append((timestamp, account.balance))

    def create_account(self, timestamp: int, account_id: str) -> bool:
        if account_id in self.accounts:
            return False
        self.accounts[account_id] = Account(account_id, timestamp)
        self._record_balance(account_id, timestamp)
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        self._process_pending_cashback(timestamp)
        if account_id not in self.accounts:
            return None
        account = self.accounts[account_id]
        account.balance += amount
        self._record_balance(account_id, timestamp)
        return account.balance

    def transfer(self, timestamp: int, source_id: str, target_id: str, amount: int) -> int | None:
        self._process_pending_cashback(timestamp)
        if source_id not in self.accounts or target_id not in self.accounts:
            return None
        if source_id == target_id:
            return None
        source = self.accounts[source_id]
        target = self.accounts[target_id]
        if source.balance < amount:
            return None
        source.balance -= amount
        target.balance += amount
        source.total_outgoing += amount
        self._record_balance(source_id, timestamp)
        self._record_balance(target_id, timestamp)
        return source.balance

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        self._process_pending_cashback(timestamp)
        spenders = [(acc.account_id, acc.total_outgoing) for acc in self.accounts.values()]
        spenders.sort(key=lambda x: (-x[1], x[0]))
        return [f"{acc_id}({amount})" for acc_id, amount in spenders[:n]]

    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
        self._process_pending_cashback(timestamp)
        if account_id not in self.accounts:
            return None
        account = self.accounts[account_id]
        if account.balance < amount:
            return None
        account.balance -= amount
        account.total_outgoing += amount
        cashback = amount * 2 // 100
        self.payment_counter += 1
        payment_id = f"payment{self.payment_counter}"
        self.payments[payment_id] = Payment(payment_id, account_id, amount, timestamp, cashback)
        self.payment_owner[payment_id] = account_id
        self._record_balance(account_id, timestamp)
        return payment_id

    def get_payment_status(self, timestamp: int, account_id: str, payment_id: str) -> str | None:
        self._process_pending_cashback(timestamp)
        if account_id not in self.accounts or payment_id not in self.payments:
            return None
        if self.payment_owner.get(payment_id) != account_id:
            return None
        payment = self.payments[payment_id]
        if timestamp >= payment.timestamp + self.TWENTY_FOUR_HOURS:
            return "CASHBACK_RECEIVED"
        return "IN_PROGRESS"

    def merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str) -> bool:
        self._process_pending_cashback(timestamp)
        if account_id_1 == account_id_2:
            return False
        if account_id_1 not in self.accounts or account_id_2 not in self.accounts:
            return False
        acc1 = self.accounts[account_id_1]
        acc2 = self.accounts[account_id_2]
        acc1.balance += acc2.balance
        acc1.total_outgoing += acc2.total_outgoing
        for payment_id, owner in self.payment_owner.items():
            if owner == account_id_2:
                self.payment_owner[payment_id] = account_id_1
        acc1.balance_history.extend(acc2.balance_history)
        acc1.balance_history.sort(key=lambda x: x[0])
        self._record_balance(account_id_1, timestamp)
        acc2.deleted_at = timestamp
        if account_id_2 not in self.deleted_accounts:
            self.deleted_accounts[account_id_2] = []
        self.deleted_accounts[account_id_2].append(acc2)
        del self.accounts[account_id_2]
        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        self._process_pending_cashback(timestamp)
        if account_id in self.accounts:
            return self._get_balance_at_time(self.accounts[account_id], time_at)
        if account_id in self.deleted_accounts:
            for deleted_acc in self.deleted_accounts[account_id]:
                if deleted_acc.created_at <= time_at:
                    if deleted_acc.deleted_at is None or time_at < deleted_acc.deleted_at:
                        return self._get_balance_at_time(deleted_acc, time_at)
        return None

    def _get_balance_at_time(self, account: Account, time_at: int) -> int | None:
        if time_at < account.created_at:
            return None
        if account.deleted_at is not None and time_at >= account.deleted_at:
            return None
        history = account.balance_history
        if not history:
            return 0
        left, right = 0, len(history) - 1
        result = 0
        while left <= right:
            mid = (left + right) // 2
            if history[mid][0] <= time_at:
                result = history[mid][1]
                left = mid + 1
            else:
                right = mid - 1
        return result
```

## Critical Tip

**Process cashback at the start of every public method!**

---

# 5. Web Crawler

## Problem Statement

Build a web crawler that finds all URLs reachable from a `startUrl`, staying within the same hostname.

## Single-Threaded BFS Solution

```python
from collections import deque
from urllib.parse import urlparse


def crawl(startUrl: str, htmlParser: 'HtmlParser') -> list[str]:
    def get_hostname(url: str) -> str:
        return urlparse(url).hostname

    start_host = get_hostname(startUrl)
    visited = {startUrl}
    queue = deque([startUrl])
    result = [startUrl]

    while queue:
        url = queue.popleft()
        try:
            for next_url in htmlParser.getUrls(url):
                if next_url in visited:
                    continue
                if get_hostname(next_url) != start_host:
                    continue
                visited.add(next_url)
                queue.append(next_url)
                result.append(next_url)
        except Exception:
            pass

    return result
```

## Multi-Threaded Solution

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from threading import Lock


def crawl_concurrent(startUrl: str, htmlParser: 'HtmlParser', max_workers: int = 10) -> list[str]:
    def get_hostname(url: str) -> str:
        return urlparse(url).hostname

    start_host = get_hostname(startUrl)
    visited = {startUrl}
    visited_lock = Lock()
    result = [startUrl]
    result_lock = Lock()

    def fetch_urls(url: str) -> list[str]:
        try:
            return htmlParser.getUrls(url)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_urls, startUrl)}

        while futures:
            done_futures = set()
            for future in as_completed(futures):
                done_futures.add(future)
                new_urls = future.result()

                for next_url in new_urls:
                    with visited_lock:
                        if next_url in visited:
                            continue
                        if get_hostname(next_url) != start_host:
                            continue
                        visited.add(next_url)

                    with result_lock:
                        result.append(next_url)

                    futures.add(executor.submit(fetch_urls, next_url))

            futures -= done_futures

    return result
```

## URL Normalization

```python
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = host
    if port:
        netloc += f":{port}"

    path = parsed.path.rstrip("/") or "/"

    tracking_params = {"utm_source", "utm_medium", "utm_campaign", "ref", "fbclid"}
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items() if k not in tracking_params}
        query = urlencode(sorted(filtered.items()), doseq=True)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))
```

## Common Pitfalls

1. **Not Handling Cycles:** Track visited URLs
2. **Hostname Comparison:** Parse and compare hostnames, not string prefix
3. **Subdomain Handling:** `sub.example.com != example.com`
4. **Thread Safety:** Atomic check-and-add with lock

---

# 6. Prompt Engineering Playground

## Problem Statement

Design a "playground" tool for Prompt Engineering, similar to OpenAI Playground or Anthropic Console. This is a full-stack system design question.

## Requirements

### Functional Requirements

| Feature | Description |
|---------|-------------|
| **Editor** | Handle large text (up to 10MB) without lag |
| **Execution** | Send prompts to LLM APIs, stream responses |
| **Version History** | Auto-save versions, revert to previous drafts |
| **Library** | Organize prompts with folders, tags, search |
| **Sharing** | Create shareable links with optional edit permissions |
| **Multi-model** | Support different providers (OpenAI, Anthropic, etc.) |

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Latency | < 100ms for editor operations |
| Reliability | No data loss on browser crash |
| Scalability | 10,000+ concurrent users |

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
├─────────────────────────────────────────────────────────────────────┤
│  Monaco Editor (Large files)  │  IndexedDB (Local draft)  │  WebSocket │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Load Balancer                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   API Server    │  │   API Server    │  │   API Server    │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Redis       │  │   PostgreSQL    │  │       S3        │
│  - Sessions     │  │  - Users        │  │  - Large files  │
│  - Cache        │  │  - Prompts      │  │                 │
│  - Pub/Sub      │  │  - Versions     │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Job Queue (Bull/BullMQ)                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM Provider APIs                             │
│      OpenAI (GPT-4)  │  Anthropic (Claude)  │  Google (Gemini)      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Challenges

### Handling 10MB Prompts

```typescript
const editor = monaco.editor.create(container, {
  largeFileOptimizations: true,
  scrollBeyondLastLine: false,
  folding: content.length < 1_000_000,
  wordWrap: content.length < 500_000 ? 'on' : 'off',
  minimap: { enabled: content.length < 1_000_000 },
});
```

### Version Control with Diffs

**Strategy:** Snapshots every 10 versions, diffs in between.

```typescript
const SNAPSHOT_INTERVAL = 10;
const MAX_DIFF_SIZE_RATIO = 0.5;

async function saveVersion(promptId: string, newContent: string, previousVersion: number): Promise<VersionData> {
  const newVersionNumber = previousVersion + 1;

  if (newVersionNumber % SNAPSHOT_INTERVAL === 1 || previousVersion === 0) {
    return { versionNumber: newVersionNumber, isSnapshot: true, content: newContent };
  }

  const previousContent = await getVersionContent(promptId, previousVersion);
  const diff = Diff.createPatch('prompt', previousContent, newContent, '', '');

  if (diff.length > newContent.length * MAX_DIFF_SIZE_RATIO) {
    return { versionNumber: newVersionNumber, isSnapshot: true, content: newContent };
  }

  return { versionNumber: newVersionNumber, isSnapshot: false, diff: diff };
}
```

### LLM API Cost Reduction

```typescript
async function executeWithCache(promptContent: string, model: string, params: ModelParams): Promise<ExecutionResult> {
  const cacheKey = crypto.createHash('sha256')
    .update(JSON.stringify({ promptContent, model, params }))
    .digest('hex');

  const cached = await redis.get(`exec:${cacheKey}`);
  if (cached) {
    return { ...JSON.parse(cached), fromCache: true, cost: 0 };
  }

  const result = await callLLMAPI(promptContent, model, params);
  await redis.setex(`exec:${cacheKey}`, 3600, JSON.stringify(result));
  return { ...result, fromCache: false };
}
```

## Trade-off Analysis

| Decision | Choice | Reason |
|----------|--------|--------|
| Version Control | Hybrid (Snapshots + Diffs) | Balance storage vs reconstruction speed |
| Streaming | WebSocket | Need bidirectional for stop/cancel |
| Storage | PostgreSQL + S3 | Metadata in DB, large files in S3 |

## Key Points to Emphasize

1. **Not a chatbot** - Each execution is stateless
2. **Storage vs Execution** - 10MB can be stored, but can't run on most models
3. **Cost awareness** - LLM API costs dominate, caching is critical

---

# 7. Distributed Mode and Median

## Problem Statement

Design a distributed system to find the **mode** (most frequent value) and **median** (middle value) of a large dataset spread across multiple machines.

**Constraints:**
- Data spread across ~10 worker machines
- Network bandwidth is the bottleneck
- Must balance load evenly across workers

## Finding the Mode

### Algorithm Overview

```
Phase 1: Local Count     → Each worker counts its local data
Phase 2: Shuffle         → Redistribute by key (key % num_workers)
Phase 3: Local Aggregate → Each worker finds its local winner
Phase 4: Global Reduce   → Worker 0 collects winners, picks global mode
```

### Key Insight: Shuffle by Modulo

```
Key 1:  1 % 10 = 1  → goes to Worker 1
Key 10: 10 % 10 = 0 → goes to Worker 0
Key 11: 11 % 10 = 1 → goes to Worker 1
```

This ensures all counts for the same key end up on ONE worker.

### Complete Solution

```python
from collections import Counter


def phase1_local_count(local_data: list[int]) -> Counter:
    return Counter(local_data)


def phase2_shuffle_counts(local_counter: Counter, worker_id: int, num_workers: int) -> list[tuple[int, int]]:
    buckets: list[list[tuple[int, int]]] = [[] for _ in range(num_workers)]

    for key, count in local_counter.items():
        target_worker = key % num_workers
        buckets[target_worker].append((key, count))

    for target_id in range(num_workers):
        if target_id != worker_id:
            send(target_id, buckets[target_id])

    received_data: list[tuple[int, int]] = []
    for _ in range(num_workers - 1):
        data = recv()
        received_data.extend(data)

    received_data.extend(buckets[worker_id])
    return received_data


def phase3_aggregate_local(received_data: list[tuple[int, int]]) -> tuple[Counter, tuple[int, int]]:
    aggregated = Counter()
    for key, count in received_data:
        aggregated[key] += count

    if aggregated:
        top_1 = aggregated.most_common(1)[0]
    else:
        top_1 = (None, 0)

    return aggregated, top_1


def phase4_global_reduction(local_top_1: tuple[int, int], worker_id: int, num_workers: int) -> int | None:
    if worker_id == 0:
        best_key, best_count = local_top_1
        for _ in range(num_workers - 1):
            remote_key, remote_count = recv()
            if remote_count > best_count:
                best_key, best_count = remote_key, remote_count
            elif remote_count == best_count:
                if remote_key is not None and (best_key is None or remote_key < best_key):
                    best_key = remote_key
        return best_key
    else:
        send(0, local_top_1)
        return None


def find_mode_distributed(local_data: list[int], worker_id: int, num_workers: int) -> int | None:
    local_counter = phase1_local_count(local_data)
    received_data = phase2_shuffle_counts(local_counter, worker_id, num_workers)
    aggregated, local_top_1 = phase3_aggregate_local(received_data)
    return phase4_global_reduction(local_top_1, worker_id, num_workers)
```

## Finding the Median

### Algorithm: Distributed Quickselect

```
Step 1: Build distributed histogram (reuse shuffle from mode)
Step 2: Calculate total count
Step 3: Binary search for the median position using pivot counting
```

```python
def distributed_quickselect(
    local_histogram: Counter,
    worker_id: int,
    num_workers: int,
    target_position: int
) -> int:
    # Find global min/max
    if local_histogram:
        local_min = min(local_histogram.keys())
        local_max = max(local_histogram.keys())
    else:
        local_min, local_max = float('inf'), float('-inf')

    if worker_id == 0:
        global_min, global_max = local_min, local_max
        for _ in range(num_workers - 1):
            remote_min, remote_max = recv()
            global_min = min(global_min, remote_min)
            global_max = max(global_max, remote_max)
        for i in range(1, num_workers):
            send(i, (global_min, global_max))
    else:
        send(0, (local_min, local_max))
        global_min, global_max = recv()

    low, high = global_min, global_max

    while low < high:
        if worker_id == 0:
            pivot = (low + high) // 2
            for i in range(1, num_workers):
                send(i, pivot)
        else:
            pivot = recv()

        count_less = sum(c for v, c in local_histogram.items() if v < pivot)
        count_equal = local_histogram.get(pivot, 0)
        count_greater = sum(c for v, c in local_histogram.items() if v > pivot)

        if worker_id == 0:
            total_less, total_equal = count_less, count_equal
            for _ in range(num_workers - 1):
                r_less, r_equal, _ = recv()
                total_less += r_less
                total_equal += r_equal

            if target_position < total_less:
                new_low, new_high = low, pivot - 1
            elif target_position < total_less + total_equal:
                new_low, new_high = pivot, pivot
            else:
                new_low, new_high = pivot + 1, high

            for i in range(1, num_workers):
                send(i, (new_low, new_high))
            low, high = new_low, new_high
        else:
            send(0, (count_less, count_equal, count_greater))
            low, high = recv()

    return low
```

## Key Interview Points

1. **Why modulo for partitioning?** Simple, deterministic, no coordination needed
2. **Why not send all data to one machine?** Network and memory bottleneck
3. **MapReduce comparison:** Phase 1 = Map, Phase 2 = Shuffle, Phase 3-4 = Reduce

## Complexity Summary

| Operation | Communication | Time |
|-----------|---------------|------|
| Mode | O(k + W) messages | O(n + k) |
| Median | O(W × log(range)) | O(k/W × log(range)) |

Where k = unique keys, W = workers, n = local data size

---

# Interview Tips Summary

## CodeSignal (90 minutes, 4 levels)

1. **Time budget:** ~15-20 min per level
2. **Test incrementally:** Verify each level before moving on
3. **Watch the sorting:** Multi-key sorts are common error sources
4. **Edge cases:** Empty lists, zero limits, non-existent IDs

## System Design

1. **Clarify requirements first:** Features, constraints, scale
2. **Start high-level:** Architecture diagram, then deep dive
3. **Discuss trade-offs:** Always explain why you chose approach A over B
4. **Consider costs:** LLM API costs dominate in AI systems

## Distributed Systems

1. **Avoid bottlenecks:** Don't send all data to one machine
2. **Use partitioning:** Modulo, consistent hashing
3. **Think about failures:** Checkpointing, retries
4. **Balance load:** Ensure even distribution across workers

---

## References

- [LeetCode 146: LRU Cache](https://leetcode.com/problems/lru-cache/)
- [LeetCode 1236: Web Crawler](https://leetcode.com/problems/web-crawler/)
- [LeetCode 1242: Web Crawler Multithreaded](https://leetcode.com/problems/web-crawler-multithreaded/)
- [Anthropic CodeSignal Assessment Guide](https://www.linkjob.ai/interview-questions/codesignal-anthropic-practice/)
- [PracHub - Anthropic Coding Questions](https://prachub.com/companies/anthropic/categories/coding-and-algorithms)
- [MapReduce Paper](https://research.google/pubs/pub62/)
