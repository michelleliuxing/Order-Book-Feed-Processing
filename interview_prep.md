# VivCourt Trading — Graduate Software Engineer Interview Preparation

---

## Table of Contents

1. [Python Core Knowledge](#1-python-core-knowledge)
2. [Algorithms & Data Structures](#2-algorithms--data-structures)
3. [Order Book & Market Microstructure](#3-order-book--market-microstructure)
4. [Questions About Your Submitted Code](#4-questions-about-your-submitted-code)
5. [Performance & Optimisation](#5-performance--optimisation)
6. [System Design for Trading](#6-system-design-for-trading)
7. [Concurrency & Networking](#7-concurrency--networking)
8. [Real-World Trading Scenarios](#8-real-world-trading-scenarios)
9. [Testing & Reliability](#9-testing--reliability)
10. [Behavioural / Culture Fit](#10-behavioural--culture-fit)

---

## 1. Python Core Knowledge

### Q1.1: What is the difference between a list, a tuple, and a set in Python? When would you choose each?

**Answer:**

| Structure | Mutable | Ordered | Duplicates | Lookup |
|-----------|---------|---------|------------|--------|
| `list`    | Yes     | Yes     | Yes        | O(n)   |
| `tuple`   | No      | Yes     | Yes        | O(n)   |
| `set`     | Yes     | No      | No         | O(1) average |

- **list** — General purpose ordered collection. Use when you need to maintain insertion order, allow duplicates, and mutate elements. Good for sequences of homogeneous items (e.g., a list of trade prices).
- **tuple** — Immutable ordered sequence. Use when the data shouldn't change after creation (e.g., a `(price, volume)` pair). Being immutable makes tuples hashable, so they can be dict keys or set members. They also have slightly lower memory overhead than lists.
- **set** — Unordered unique collection backed by a hash table. Use when you need fast membership testing (e.g., "is this order_id active?") or deduplication. Lookup is O(1) average.

**Trading context:** In the order book code, `(price, volume)` is stored as a tuple because it represents a fixed record for a given order at a point in time. The order dictionaries use dict (hash map) for O(1) order lookup by ID.

---

### Q1.2: Explain Python's dictionary implementation. What is the average and worst-case time complexity for lookups?

**Answer:**

Python's `dict` is implemented as a hash table with open addressing (since CPython 3.6+, it uses a compact layout that preserves insertion order).

- **Average case:** O(1) for get, set, and delete.
- **Worst case:** O(n) — this happens when many keys hash to the same slot (hash collision). In practice, Python's hash function distributes keys well, so this is rare.

**How it works internally:**
1. Python calls `hash(key)` to get an integer.
2. It computes `hash(key) % table_size` to find the slot index.
3. If the slot is empty, insert. If occupied, it probes (using a perturbation scheme) to find the next open slot.
4. When the load factor exceeds ~2/3, the table is resized (typically doubled), and all entries are rehashed.

**Trading context:** The order book uses `dict[int, tuple[int, int]]` to map `order_id -> (price, volume)`. This gives O(1) add, update, delete, and trade operations — critical for processing high-throughput market data feeds where microseconds matter.

---

### Q1.3: What are Python generators and why are they useful?

**Answer:**

A generator is a function that uses `yield` instead of `return`. It produces values lazily — one at a time — rather than building an entire collection in memory.

```python
def gen_from(bin: BinaryIO):
    while True:
        buf = bin.read(header_size)
        if not buf:
            return
        header = Header.unpack(buf)
        # ... parse body ...
        yield header, unpack(buf)
```

**Key properties:**
- **Lazy evaluation** — values are computed on demand, not all at once.
- **Memory efficient** — only one item is in memory at a time. Essential when processing gigabytes of market data.
- **Maintains state** — the generator remembers where it left off between `yield` calls.
- **Iterable** — works with `for` loops, `next()`, list comprehensions, etc.

**Why this matters in trading:** A market data feed can have millions of messages. Loading them all into a list would consume enormous memory. A generator processes one message at a time with O(1) memory overhead.

---

### Q1.4: Explain the difference between `__init__`, `__new__`, `__repr__`, and `__str__`.

**Answer:**

- `__new__(cls)` — Called *before* `__init__`. It is the actual constructor that creates and returns the new instance. Rarely overridden except for immutable types or singletons.
- `__init__(self)` — Initializer. Called after `__new__` to set up the instance's attributes.
- `__repr__(self)` — Returns an unambiguous string representation, ideally one that could recreate the object. Used by `repr()` and in the REPL. Should be developer-facing.
- `__str__(self)` — Returns a human-readable string. Used by `print()` and `str()`. Falls back to `__repr__` if not defined.

```python
class Order:
    def __init__(self, order_id, price, volume):
        self.order_id = order_id
        self.price = price
        self.volume = volume

    def __repr__(self):
        return f"Order(id={self.order_id}, price={self.price}, vol={self.volume})"

    def __str__(self):
        return f"Order #{self.order_id}: {self.volume}@{self.price}"
```

---

### Q1.5: What is the Global Interpreter Lock (GIL)? How does it affect performance?

**Answer:**

The GIL is a mutex in CPython that allows only one thread to execute Python bytecode at a time, even on multi-core machines.

**Implications:**
- **CPU-bound work** — Multi-threading does NOT give parallel execution. You won't get speedup from `threading` for number crunching. Use `multiprocessing` or C extensions instead.
- **I/O-bound work** — Threading is still effective because the GIL is released during I/O operations (network calls, file reads). While one thread waits on I/O, another can run.

**Trading relevance:** A trading system receiving market data (I/O-bound) while running pricing models (CPU-bound) might use `asyncio` or threading for I/O and `multiprocessing` for computation. Some firms move latency-sensitive code to C/C++ extensions that release the GIL.

**Note:** CPython 3.13+ introduced experimental "free-threaded" builds (PEP 703) that can disable the GIL, but this is not yet production-standard.

---

### Q1.6: What are `@classmethod`, `@staticmethod`, and `@property`? When do you use each?

**Answer:**

```python
class OrderBook:
    _instance = None

    def __init__(self, symbol):
        self.symbol = symbol
        self._orders = {}

    @classmethod
    def from_snapshot(cls, data: dict):
        """Alternative constructor — receives cls (the class itself)."""
        book = cls(data["symbol"])
        for order in data["orders"]:
            book.add(order)
        return book

    @staticmethod
    def validate_price(price: int) -> bool:
        """Utility that doesn't need self or cls — pure function."""
        return price > 0

    @property
    def spread(self):
        """Computed attribute — accessed like book.spread, not book.spread()."""
        return self.best_ask - self.best_bid
```

- **`@classmethod`** — Receives the class as first arg. Used for factory/alternative constructors (like `Header.unpack` in your code).
- **`@staticmethod`** — No implicit first arg. A regular function scoped to the class for organisational purposes.
- **`@property`** — Turns a method into a read-only attribute. Good for computed values.

---

### Q1.7: Explain Python's `struct` module. Why is it used in trading systems?

**Answer:**

`struct` packs and unpacks Python values into/from C-style binary data according to a format string.

```python
import struct

# '<' = little-endian, 'L' = unsigned 32-bit int, 'c' = char
header_format = "<LLc"
header_size = struct.calcsize(header_format)  # 9 bytes

data = struct.pack(header_format, 42, 31, b'A')
seq_num, msg_size, msg_type = struct.unpack(header_format, data)
```

**Why it matters for trading:**
- Exchange feeds (e.g., ASX ITCH, CME MDP3) deliver data as raw binary — not JSON or XML — because binary is smaller and faster to parse.
- `struct` gives direct control over byte layout, endianness, and alignment.
- Parsing a binary message with `struct.unpack` is significantly faster than parsing equivalent text/JSON.

---

### Q1.8: What is the difference between deep copy and shallow copy?

**Answer:**

```python
import copy

original = [[1, 2], [3, 4]]

shallow = copy.copy(original)      # New outer list, same inner lists
deep = copy.deepcopy(original)     # New outer list AND new inner lists

original[0].append(99)
print(shallow[0])  # [1, 2, 99] — inner list is shared
print(deep[0])     # [1, 2]     — completely independent
```

- **Shallow copy** — Creates a new object but references the same nested objects. Fast but can cause subtle bugs with mutable nested structures.
- **Deep copy** — Recursively copies everything. Safe but slower and uses more memory.

**Trading context:** When snapshotting an order book's state (e.g., for logging or backtesting comparison), you need a deep copy if the book will continue mutating. A shallow copy would silently break when the original changes.

---

### Q1.9: How does Python handle memory management and garbage collection?

**Answer:**

Python uses two mechanisms:

1. **Reference counting** — Every object has a counter tracking how many names point to it. When the count drops to zero, memory is freed immediately. This is fast and deterministic.

2. **Cycle-detecting garbage collector** — Reference counting alone can't handle circular references (A→B→A). Python's `gc` module periodically scans for unreachable reference cycles and collects them. It uses a generational scheme (gen 0, 1, 2) — newly created objects are checked more frequently.

**Implications for trading:**
- Avoid creating circular references in hot paths (market data processing loops).
- Be careful with large temporary objects — they can cause GC pauses. In latency-sensitive paths, consider reusing buffers (e.g., pre-allocated `bytearray`) rather than creating new objects every iteration.
- You can tune or disable GC with `gc.disable()` in ultra-low-latency sections (and manually trigger it during quiet periods).

---

### Q1.10: What are type hints in Python? Do they affect runtime?

**Answer:**

Type hints are annotations that document expected types. They do NOT affect runtime behavior — Python remains dynamically typed.

```python
def add(self, order_id: int, side: str, price: int, volume: int) -> None:
    self._side(side)[order_id] = (price, volume)
```

**Benefits:**
- **Readability** — immediately clear what a function expects and returns.
- **Static analysis** — tools like `mypy`, `pyright` catch type errors before runtime.
- **IDE support** — better autocompletion, refactoring, and inline documentation.

**Trading context:** In a large codebase with many engineers, type hints dramatically reduce bugs. A function expecting `price: int` (fixed-point cents) vs `price: float` (dollars) is a critical distinction that type hints make explicit.

---

## 2. Algorithms & Data Structures

### Q2.1: What is the time complexity of your order book operations? Can you do better?

**Answer:**

**Current implementation:**

| Operation | Complexity | Why |
|-----------|-----------|-----|
| `add`     | O(1)      | Dict insertion |
| `update`  | O(1)      | Dict update |
| `delete`  | O(1)      | Dict removal |
| `trade`   | O(1)      | Dict lookup + update/delete |
| `depth(N)`| O(M log M)| Aggregate all M orders, sort, take top N |

Where M = total number of orders on one side.

**How to improve `depth()`:**

The bottleneck is `depth()`. Currently it aggregates and sorts ALL orders every time. Better approaches:

1. **Maintain a sorted price-level map** — Use a `SortedDict` (from `sortedcontainers`) keyed by price, with aggregated volume as the value. Then `depth(N)` is O(N) — just iterate the first N entries. The trade-off is that `add`/`delete`/`trade` become O(log P) where P = number of distinct price levels (still fast since P is typically small).

2. **Use a heap** — Maintain a min-heap (asks) or max-heap (bids) of price levels. Getting top N is O(N log N) but avoids re-sorting everything.

3. **Cache the depth snapshot** — Store the last computed depth and invalidate/update it incrementally when orders change. Only recompute levels that were actually affected.

```python
from sortedcontainers import SortedDict

class OptimisedSide:
    def __init__(self):
        self.orders = {}              # order_id -> (price, volume)
        self.price_levels = SortedDict()  # price -> total_volume

    def add(self, order_id, price, volume):
        self.orders[order_id] = (price, volume)
        self.price_levels[price] = self.price_levels.get(price, 0) + volume

    def depth(self, n):
        # O(N) — just take first/last N items from sorted structure
        return list(self.price_levels.items()[:n])
```

---

### Q2.2: Explain the difference between a hash map and a balanced BST. When would you use each?

**Answer:**

| Feature | Hash Map (dict) | Balanced BST (e.g., Red-Black Tree) |
|---------|----------------|--------------------------------------|
| Lookup  | O(1) average    | O(log n)                            |
| Insert  | O(1) average    | O(log n)                            |
| Delete  | O(1) average    | O(log n)                            |
| Ordered iteration | No (insertion order in Python 3.7+) | Yes — sorted by key |
| Range queries | O(n) | O(log n + k) where k = results |
| Worst case | O(n) collisions | O(log n) guaranteed |

**When to use which:**
- **Hash map** — When you need fast key-value lookups and don't need sorted order. E.g., `order_id -> order_details`.
- **Balanced BST / SortedDict** — When you need sorted iteration or range queries. E.g., "give me all price levels between 100 and 110" or "give me the top 5 bid prices."

**Trading context:** A production order book often uses both:
- Hash map for O(1) order lookup by ID (needed for update/delete/trade).
- BST or sorted structure for price levels (needed for fast depth queries and best-bid/best-ask).

---

### Q2.3: Implement a function that finds the k-th largest element in an unsorted array. What's the optimal approach?

**Answer:**

Three approaches, in order of sophistication:

**Approach 1: Sort — O(n log n)**
```python
def kth_largest_sort(arr, k):
    arr.sort(reverse=True)
    return arr[k - 1]
```

**Approach 2: Min-heap of size k — O(n log k)**
```python
import heapq

def kth_largest_heap(arr, k):
    return heapq.nlargest(k, arr)[-1]
```

**Approach 3: Quickselect — O(n) average, O(n²) worst**
```python
import random

def kth_largest_quickselect(arr, k):
    target = len(arr) - k

    def partition(left, right, pivot_idx):
        pivot = arr[pivot_idx]
        arr[pivot_idx], arr[right] = arr[right], arr[pivot_idx]
        store = left
        for i in range(left, right):
            if arr[i] < pivot:
                arr[i], arr[store] = arr[store], arr[i]
                store += 1
        arr[store], arr[right] = arr[right], arr[store]
        return store

    left, right = 0, len(arr) - 1
    while left <= right:
        pivot_idx = random.randint(left, right)
        pos = partition(left, right, pivot_idx)
        if pos == target:
            return arr[pos]
        elif pos < target:
            left = pos + 1
        else:
            right = pos - 1
```

**Trading context:** "Find the 5th best price level" is essentially a k-th element problem. With a sorted structure you get this for free; with an unsorted dict of orders, quickselect is optimal.

---

### Q2.4: What is a priority queue / heap? How would it apply to a trading system?

**Answer:**

A priority queue is an abstract data type where each element has a priority, and the element with the highest (or lowest) priority is served first.

A **binary heap** is the most common implementation:
- **Min-heap:** Parent ≤ children. Root is the minimum.
- **Max-heap:** Parent ≥ children. Root is the maximum.

| Operation | Complexity |
|-----------|-----------|
| Insert    | O(log n)  |
| Get min/max | O(1)   |
| Extract min/max | O(log n) |

Python's `heapq` module provides a min-heap.

```python
import heapq

# Simulate a priority order queue
orders = []
heapq.heappush(orders, (100.50, "limit_buy_1"))   # (price, order_id)
heapq.heappush(orders, (99.75, "limit_buy_2"))
heapq.heappush(orders, (101.00, "limit_buy_3"))

best_price, order_id = heapq.heappop(orders)  # (99.75, "limit_buy_2")
```

**Trading applications:**
- **Order matching engine** — A max-heap for bids (highest bid first) and min-heap for asks (lowest ask first). When the top of the bid heap >= top of the ask heap, a trade occurs.
- **Event scheduling** — Priority queue of timed events (e.g., order expirations, scheduled snapshots) processed in timestamp order.
- **Top-K queries** — Maintain a heap of size K for the K best price levels.

---

### Q2.5: Explain Big-O notation. What is amortised complexity?

**Answer:**

**Big-O** describes the upper bound of an algorithm's growth rate as input size increases:
- O(1) — constant (dict lookup)
- O(log n) — logarithmic (binary search, BST operations)
- O(n) — linear (scanning all orders)
- O(n log n) — linearithmic (sorting)
- O(n²) — quadratic (nested loops)

**Amortised complexity** is the average cost per operation over a worst-case sequence of operations.

**Classic example — Python `list.append()`:**
- Most appends are O(1) — just write to the next slot.
- Occasionally the internal array is full and must be resized (copy all elements) — O(n).
- But resizing doubles capacity, so the next n/2 appends are O(1).
- Amortised: O(1) per append.

**Trading example:** A hash map (dict) resize during high-volume market activity could cause a brief latency spike. Understanding amortised cost helps predict and mitigate such spikes (e.g., pre-allocating capacity).

---

### Q2.6: How does binary search work? Implement it and state its complexity.

**Answer:**

Binary search finds a target value in a **sorted** array by repeatedly halving the search space.

```python
def binary_search(arr: list[int], target: int) -> int:
    """Returns the index of target, or -1 if not found."""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

- **Time:** O(log n)
- **Space:** O(1)
- **Prerequisite:** Array must be sorted.

**Trading variant — `bisect` for price level insertion:**
```python
import bisect

price_levels = [95, 100, 105, 110]  # sorted
new_price = 102
idx = bisect.bisect_left(price_levels, new_price)
price_levels.insert(idx, new_price)
# [95, 100, 102, 105, 110]
```

This is used when maintaining a sorted list of price levels — `bisect` finds the insertion point in O(log n), though `list.insert` is O(n) due to shifting. For truly efficient sorted insertion, use a balanced BST or `SortedList`.

---

## 3. Order Book & Market Microstructure

### Q3.1: What is an order book? Explain bids, asks, and the spread.

**Answer:**

An **order book** is a record of all outstanding buy and sell orders for a financial instrument, organised by price level.

- **Bid** — A buy order. "I want to buy 100 shares at $50." Bids are sorted highest price first (best bid = highest).
- **Ask (Offer)** — A sell order. "I want to sell 100 shares at $51." Asks are sorted lowest price first (best ask = lowest).
- **Spread** — The difference between the best ask and best bid: `spread = best_ask - best_bid`. A narrow spread indicates high liquidity; a wide spread indicates low liquidity.
- **Depth** — The number of price levels shown. "Top-5 depth" means the 5 best bid and 5 best ask price levels.

```
          Asks (sell orders)
Price  | Volume
$51.05 | 200    ← best ask
$51.10 | 150
$51.20 | 300
----- spread = $0.05 -----
$51.00 | 100    ← best bid
$50.95 | 250
$50.90 | 400
          Bids (buy orders)
```

**Mid-price** = (best_bid + best_ask) / 2 — a common estimate of the "fair" price.

---

### Q3.2: What are the different order types in financial markets?

**Answer:**

| Order Type | Description | When Used |
|-----------|-------------|-----------|
| **Market order** | Execute immediately at the best available price | When speed matters more than price |
| **Limit order** | Execute at a specific price or better; sits in the book if not immediately fillable | When price matters more than speed |
| **Stop order** | Becomes a market order once a trigger price is reached | Risk management / stop-loss |
| **Stop-limit** | Becomes a limit order once a trigger price is reached | Controlled stop-loss |
| **IOC (Immediate or Cancel)** | Execute as much as possible immediately, cancel the rest | When partial fills are acceptable |
| **FOK (Fill or Kill)** | Execute the entire order immediately, or cancel completely | All-or-nothing |
| **GTC (Good Till Cancel)** | Remains in the book until filled or explicitly cancelled | Passive limit strategies |

In your order book code, the messages represent limit orders sitting on the book (Add/Update/Delete) and trades that occur when orders are matched (Execute/Trade).

---

### Q3.3: What is price-time priority? How does an exchange matching engine work?

**Answer:**

**Price-time priority (FIFO)** is the most common matching algorithm:
1. **Price priority** — Better-priced orders are matched first (higher bid, lower ask).
2. **Time priority** — Among orders at the same price, the earliest order is matched first.

**Matching engine flow:**
1. An incoming buy order arrives at price P.
2. The engine checks the ask side: is there any ask ≤ P?
3. If yes, match with the best (lowest) ask. If multiple asks at that price, match with the oldest.
4. If the incoming order is not fully filled, continue matching at the next price level.
5. If no more asks ≤ P, the remaining quantity rests on the bid side of the book.

**Example:**
```
Book state:
  Ask: $100 (200 units, arrived 10:01), $100 (100 units, arrived 10:02), $101 (500 units)

Incoming: Buy 250 @ $101

Match 1: Buy 200 from ask at $100 (10:01 — time priority)
Match 2: Buy 50 from ask at $100 (10:02 — time priority)
Remaining ask at $100: 50 units
```

---

### Q3.4: What is market data? What formats are commonly used?

**Answer:**

**Market data** is the real-time stream of prices, volumes, and order events broadcast by exchanges.

**Types:**
- **Level 1 (Top of book)** — Best bid, best ask, last trade. Simplest and most common.
- **Level 2 (Depth of book)** — Multiple price levels of bids and asks (e.g., top 5 or top 10 levels).
- **Level 3 (Full order book)** — Every individual order, including order IDs. This is what your code processes.

**Common protocols/formats:**
- **FIX (Financial Information eXchange)** — Text-based, tag-value pairs. Widely used but relatively slow to parse.
- **ITCH** — Binary, optimised for speed. Used by NASDAQ, ASX, etc. Your code's binary format is similar to ITCH.
- **SBE (Simple Binary Encoding)** — Schema-based binary. Used by CME.
- **Multicast UDP** — Market data is often broadcast via UDP multicast for lowest latency (one packet reaches all subscribers).

Your `message.py` implements an ITCH-like binary parser — fixed-size header, variable body decoded by message type.

---

### Q3.5: What is latency and why does it matter in trading?

**Answer:**

**Latency** = the time delay between an event occurring and the system reacting to it.

In trading, common latency measurements:
- **Tick-to-trade** — Time from receiving a market data update to sending an order. Quant firms target microseconds to low milliseconds.
- **Wire latency** — Physical network delay (speed of light in fiber). ~5 μs per km.
- **Processing latency** — Time your software takes to process data and make decisions.

**Why it matters:**
- In competitive markets, the fastest participant captures the best prices.
- A 1ms advantage can mean the difference between getting a fill and missing it.
- Stale data = wrong decisions. If your system is slow, your view of the market is outdated.

**Reducing latency in Python:**
- Use binary protocols (like your `struct` parsing) instead of text parsing.
- Avoid unnecessary object creation in hot paths.
- Use generators to avoid buffering.
- Consider C extensions or Cython for critical loops.
- Pre-allocate data structures to avoid resize pauses.

---

## 4. Questions About Your Submitted Code

*These are questions an interviewer would likely ask about the order book code you submitted.*

### Q4.1: Walk me through your architecture. Why did you choose this design?

**Answer:**

"I separated the code into three modules following the single-responsibility principle:

1. **`message.py`** — Handles binary parsing. Each message type is a class with a `@classmethod unpack()` factory. The `gen_from()` generator streams messages lazily from the binary input, so we never load the entire file into memory.

2. **`orderbook.py`** — Manages a single symbol's order book. Stores orders in two flat dictionaries (bids, asks) keyed by `order_id`. This gives O(1) for all mutations. The `depth()` method aggregates orders by price level.

3. **`main.py`** — Orchestrates everything. Maintains a dictionary of `symbol → OrderBook`, dispatches messages to the correct book, and only prints output when the depth snapshot actually changes (deduplication via `last_snapshots`).

This separation means I can unit test the order book without touching I/O, swap the message format without changing the order book, and extend to multiple symbols trivially."

---

### Q4.2: Your `depth()` method is O(M log M). How would you optimise it for a production system?

**Answer:**

"The current design prioritises simplicity and correctness for the assessment, but in production I'd maintain a price-level aggregation alongside the order-level dictionary:

```python
class Side:
    def __init__(self):
        self.orders = {}                   # order_id -> (price, volume)
        self.levels = SortedDict()         # price -> aggregated_volume

    def add(self, order_id, price, volume):
        self.orders[order_id] = (price, volume)
        self.levels[price] = self.levels.get(price, 0) + volume

    def delete(self, order_id):
        price, volume = self.orders.pop(order_id)
        self.levels[price] -= volume
        if self.levels[price] <= 0:
            del self.levels[price]
```

Now `depth(N)` is O(N) — just slice the first/last N entries from the sorted structure. Add/delete/trade become O(log P) where P = number of distinct price levels (typically a few hundred at most, so log P ≈ 8).

I could also cache the depth result and only invalidate it when an order within the top-N levels changes."

---

### Q4.3: Why did you use `dict.pop(order_id, None)` instead of `del dict[order_id]` in `delete()`?

**Answer:**

"`pop(key, default)` is defensive — if the `order_id` doesn't exist (e.g., duplicate delete message, or a delete for an already-traded order), it returns `None` silently instead of raising a `KeyError`.

In a real-world market data feed, you can receive unexpected or duplicate messages due to:
- Retransmissions after packet loss.
- Sequence gaps that get replayed.
- Exchange-side bugs.

Using `pop` with a default makes the system resilient to these edge cases without crashing."

---

### Q4.4: What happens if you receive messages out of order? How would you handle sequence gaps?

**Answer:**

"Currently, the code assumes messages arrive in sequence order. In production, I'd add sequence number tracking:

```python
expected_seq = 1
for header, msg in message.gen_from(sys.stdin.buffer):
    if header.seq_num != expected_seq:
        if header.seq_num > expected_seq:
            # Gap detected — request retransmission
            request_retransmit(expected_seq, header.seq_num - 1)
            # Buffer this message until gap is filled
        elif header.seq_num < expected_seq:
            # Duplicate — skip
            continue
    expected_seq = header.seq_num + 1
    # ... process normally
```

Strategies for handling gaps:
1. **Buffer and wait** — Hold out-of-order messages until the gap is filled.
2. **Request retransmission** — Ask the exchange for missed messages.
3. **Snapshot recovery** — Request a full book snapshot and rebuild from there.
4. **Mark book as stale** — Flag the book as unreliable until recovery completes."

---

### Q4.5: Why do you compare snapshots to detect changes rather than using a dirty flag?

**Answer:**

"Comparing snapshots is simpler and more correct:

- A **dirty flag** would need to be set on every mutation and cleared after printing. But an order book mutation doesn't always change the top-N depth — e.g., adding an order at a price well below the top 5 bids doesn't affect the visible depth. A dirty flag would cause unnecessary output.

- **Snapshot comparison** only triggers output when the actual visible depth changes. This reduces output volume and downstream processing.

The cost is computing the snapshot every time (O(M log M) currently). With the sorted price-level structure I described, this becomes O(N), making the comparison very cheap."

---

### Q4.6: How would you add unit tests for the OrderBook class?

**Answer:**

```python
import pytest
from orderbook import OrderBook

class TestOrderBook:
    def setup_method(self):
        self.book = OrderBook()

    def test_add_and_depth(self):
        self.book.add(1, "B", 100, 50)
        self.book.add(2, "B", 101, 30)
        self.book.add(3, "S", 105, 20)
        bids, asks = self.book.depth(5)
        assert bids == [(101, 30), (100, 50)]
        assert asks == [(105, 20)]

    def test_aggregation_same_price(self):
        self.book.add(1, "B", 100, 50)
        self.book.add(2, "B", 100, 30)
        bids, _ = self.book.depth(5)
        assert bids == [(100, 80)]  # Aggregated

    def test_trade_partial_fill(self):
        self.book.add(1, "B", 100, 50)
        self.book.trade(1, "B", 20)
        bids, _ = self.book.depth(5)
        assert bids == [(100, 30)]

    def test_trade_full_fill_removes_order(self):
        self.book.add(1, "B", 100, 50)
        self.book.trade(1, "B", 50)
        bids, _ = self.book.depth(5)
        assert bids == []

    def test_delete_nonexistent_order(self):
        self.book.delete(999, "B")  # Should not raise

    def test_depth_limit(self):
        for i in range(10):
            self.book.add(i, "B", 100 + i, 10)
        bids, _ = self.book.depth(3)
        assert len(bids) == 3
        assert bids[0][0] == 109  # Highest price first

    def test_update_changes_price(self):
        self.book.add(1, "B", 100, 50)
        self.book.update(1, "B", 105, 50)
        bids, _ = self.book.depth(5)
        assert bids == [(105, 50)]
```

---

## 5. Performance & Optimisation

### Q5.1: How would you profile a Python application to find bottlenecks?

**Answer:**

**Profiling tools (from lightweight to comprehensive):**

1. **`time.perf_counter()`** — Manual timing of specific sections.
   ```python
   import time
   start = time.perf_counter()
   book.depth(5)
   elapsed = time.perf_counter() - start
   print(f"depth() took {elapsed*1e6:.1f} μs")
   ```

2. **`cProfile`** — Built-in deterministic profiler. Shows call counts and cumulative time per function.
   ```bash
   python -m cProfile -s cumtime main.py < input.stream
   ```

3. **`line_profiler`** — Line-by-line timing within functions. Invaluable for finding the hot lines.
   ```python
   @profile
   def depth(self, levels):
       ...
   ```

4. **`memory_profiler`** — Tracks memory usage line by line.

5. **`py-spy`** — Sampling profiler that attaches to a running process without modifying code. Zero overhead. Generates flame graphs.

**Trading context:** In a live system, you'd use `py-spy` or a similar sampling profiler to avoid impacting production performance. For development, `cProfile` + `line_profiler` to find and fix the top bottlenecks.

---

### Q5.2: What are some Python-specific performance tips?

**Answer:**

1. **Use built-in types** — `dict`, `list`, `set` are implemented in C. Avoid reinventing them.
2. **Avoid attribute lookups in tight loops** — Cache `self._bids` as a local variable.
   ```python
   def process(self):
       bids = self._bids  # one lookup instead of N
       for order_id in ids:
           price, vol = bids[order_id]
   ```
3. **Use `__slots__`** — Prevents dynamic attribute creation, reduces memory, speeds up attribute access.
   ```python
   class Order:
       __slots__ = ('order_id', 'price', 'volume')
   ```
4. **List comprehensions over loops** — They execute in C internally.
   ```python
   # Slower
   result = []
   for price, vol in totals.items():
       if vol != 0:
           result.append((price, vol))

   # Faster
   result = [(p, v) for p, v in totals.items() if v != 0]
   ```
5. **`collections.defaultdict`** — Avoids repeated `dict.get(key, 0)` patterns.
6. **Avoid global variables in hot paths** — Local variable access is faster than global.
7. **Use `struct.Struct`** — Pre-compile the format string for repeated unpacking.
   ```python
   _header_struct = struct.Struct("<LLc")  # compiled once
   _header_struct.unpack(buf)              # faster than struct.unpack("<LLc", buf)
   ```

---

### Q5.3: When would you choose Python vs C++ for a trading system component?

**Answer:**

| Aspect | Python | C++ |
|--------|--------|-----|
| Development speed | Very fast | Slower |
| Runtime performance | ~50-100x slower than C++ | Near hardware speed |
| Memory control | Managed (GC) | Manual / RAII |
| Latency determinism | Poor (GC pauses, GIL) | Excellent |
| Libraries | Rich ecosystem (numpy, pandas, scipy) | Less convenient for data science |

**When to use Python:**
- Research, prototyping, backtesting, strategy development.
- Data analysis and visualisation.
- Operational tools, monitoring, configuration.
- Connecting to slower I/O-bound services (databases, REST APIs).
- Any system where development velocity matters more than nanosecond latency.

**When to use C++:**
- Ultra-low-latency order execution path.
- Market data feed handlers processing millions of messages per second.
- Matching engines.
- Anything where predictable, sub-microsecond performance is required.

**Common hybrid approach:** Many quant firms write strategy logic and research tools in Python, but deploy critical execution infrastructure in C++. Python calls C++ via bindings (pybind11, ctypes, Cython).

---

## 6. System Design for Trading

### Q6.1: Design a real-time market data distribution system.

**Answer:**

**Requirements:**
- Receive raw market data from exchanges.
- Normalise it into a common format.
- Distribute it to multiple consumers (trading strategies, risk systems, UI).
- Minimise latency.

**Architecture:**

```
Exchange Feed  →  Feed Handler  →  Normaliser  →  Message Bus  →  Consumers
  (binary)       (C++/Python)     (common fmt)    (shared mem    (strategies,
                                                   / ZeroMQ /     risk, UI)
                                                   Kafka)
```

**Key components:**

1. **Feed Handler** — Connects to exchange, handles reconnection, sequence gap detection, and raw message parsing. Similar to your `message.py` + `gen_from()`.

2. **Normaliser** — Converts exchange-specific formats (ITCH, FIX, SBE) into a common internal format. Allows strategies to be exchange-agnostic.

3. **Message Bus** — Distributes normalised data to subscribers.
   - **Low latency:** Shared memory or lock-free ring buffers (e.g., Aeron, LMAX Disruptor pattern).
   - **Medium latency:** ZeroMQ (pub/sub). Fast, no broker.
   - **High throughput (not latency-sensitive):** Kafka. Durable, replayable. Good for analytics and logging.

4. **Book Builder** — Each consumer maintains its own order book (like your `OrderBook` class) from the message stream.

**Fault tolerance:**
- Sequence number tracking and gap detection.
- Snapshot recovery mechanism.
- Heartbeat monitoring for feed health.
- Redundant feed connections (primary/secondary).

---

### Q6.2: How would you store and replay historical market data?

**Answer:**

**Storage requirements:**
- Full order book feeds can generate 10-50 GB/day per exchange.
- Need to replay in exact sequence order for backtesting.
- Need fast random access by time range and symbol.

**Storage options:**

1. **Flat binary files** — Store raw binary messages as received. Fast I/O, compact. Tag with timestamp and sequence number. Good for replay at original speed.

2. **Columnar formats (Parquet, HDF5)** — Good for analytical queries (e.g., "what was the VWAP of symbol X between 10:00 and 11:00?"). Efficient compression and column pruning.

3. **Time-series databases (Arctic, TimescaleDB, InfluxDB)** — Purpose-built for time-indexed data. Good for aggregated data (OHLCV bars, snapshots).

4. **Object storage (S3) + metadata index** — Store raw data in S3, index metadata (date, symbol, exchange) in a database. Cost-effective for large archives.

**Replay design:**
```python
class MarketDataReplayer:
    def __init__(self, data_path: str, start_time: datetime, end_time: datetime):
        self.reader = open(data_path, 'rb')
        self.start_time = start_time
        self.end_time = end_time

    def replay(self, speed: float = 1.0):
        """Replay messages at given speed multiplier (1.0 = real-time)."""
        for timestamp, header, msg in self._read_messages():
            if timestamp < self.start_time:
                continue
            if timestamp > self.end_time:
                break
            # Simulate real-time delay
            time.sleep(delay / speed)
            yield header, msg
```

---

### Q6.3: How would you design a risk management system?

**Answer:**

**Pre-trade risk checks (must be fast, synchronous):**
- **Position limits** — Reject orders that would exceed max position per symbol.
- **Order size limits** — Reject abnormally large orders.
- **Price band checks** — Reject orders far from current market (likely errors).
- **Rate limiting** — Max orders per second to prevent runaway algorithms.
- **Kill switch** — Emergency halt of all trading.

**Post-trade risk monitoring (can be asynchronous):**
- **P&L tracking** — Real-time profit and loss per strategy, symbol, portfolio.
- **Exposure monitoring** — Net and gross exposure by asset class, currency, market.
- **Drawdown alerts** — Alert if losses exceed thresholds.

**Implementation:**
```python
class PreTradeRiskCheck:
    def __init__(self, max_position: int, max_order_size: int, max_orders_per_sec: int):
        self.max_position = max_position
        self.max_order_size = max_order_size
        self.max_orders_per_sec = max_orders_per_sec
        self.positions = defaultdict(int)
        self.order_timestamps = deque()

    def check(self, symbol: str, side: str, quantity: int, price: int) -> bool:
        if quantity > self.max_order_size:
            return False

        projected = self.positions[symbol] + (quantity if side == 'B' else -quantity)
        if abs(projected) > self.max_position:
            return False

        now = time.monotonic()
        self.order_timestamps.append(now)
        while self.order_timestamps and self.order_timestamps[0] < now - 1.0:
            self.order_timestamps.popleft()
        if len(self.order_timestamps) > self.max_orders_per_sec:
            return False

        return True
```

---

## 7. Concurrency & Networking

### Q7.1: Explain threading vs multiprocessing vs asyncio in Python.

**Answer:**

| Approach | Best for | GIL impact | Communication |
|----------|----------|-----------|---------------|
| `threading` | I/O-bound tasks | Blocked for CPU work | Shared memory (need locks) |
| `multiprocessing` | CPU-bound tasks | Each process has its own GIL | IPC (pipes, queues, shared memory) |
| `asyncio` | High-concurrency I/O | Single-threaded, event loop | Coroutines + await |

**`threading`** — Good for tasks that wait on I/O (network, disk). Multiple threads can overlap I/O waits. But the GIL prevents true CPU parallelism.

**`multiprocessing`** — Spawns separate processes, each with its own Python interpreter and GIL. True parallelism for CPU work. Higher overhead (process creation, IPC serialisation).

**`asyncio`** — Single thread, event loop. Uses `async/await` to switch between tasks at I/O boundaries. Very efficient for many concurrent I/O operations (e.g., connecting to 100 exchange feeds simultaneously). No thread-safety issues since it's single-threaded.

**Trading example:**
```python
import asyncio

async def subscribe_to_feed(exchange: str):
    reader, writer = await asyncio.open_connection(exchange, 9000)
    while True:
        data = await reader.read(1024)
        process_market_data(data)

async def main():
    await asyncio.gather(
        subscribe_to_feed("exchange_a"),
        subscribe_to_feed("exchange_b"),
        subscribe_to_feed("exchange_c"),
    )
```

---

### Q7.2: What is TCP vs UDP? Why do exchanges use multicast UDP for market data?

**Answer:**

| Feature | TCP | UDP |
|---------|-----|-----|
| Reliable | Yes (retransmission) | No |
| Ordered | Yes | No |
| Connection | Connection-oriented | Connectionless |
| Overhead | Higher (handshake, ACKs) | Lower (just send) |
| Latency | Higher | Lower |

**Why exchanges use multicast UDP:**
- **One-to-many** — The exchange sends one packet, and every subscriber receives it simultaneously. TCP would require a separate connection per subscriber.
- **Lowest latency** — No connection setup, no ACK waiting, no head-of-line blocking.
- **Fairness** — All participants receive the data at the same time (within network topology limits).

**The trade-off:** UDP can drop packets. Exchanges handle this by:
- Including sequence numbers so consumers detect gaps.
- Providing a TCP retransmission channel for missed messages.
- Publishing periodic snapshots for recovery.

This is exactly the pattern in your code — each message has a `seq_num` in the header for gap detection.

---

### Q7.3: What are race conditions? How do you prevent them?

**Answer:**

A **race condition** occurs when the behavior of a program depends on the relative timing of events (e.g., two threads accessing shared data simultaneously).

**Example — broken counter:**
```python
# Thread 1 and Thread 2 both run:
counter += 1

# Under the hood, this is:
# 1. Read counter (e.g., 5)
# 2. Add 1 (6)
# 3. Write back (6)
#
# If both threads read 5 before either writes, both write 6.
# Expected: 7. Actual: 6. Lost update!
```

**Prevention strategies:**

1. **Mutex (Lock)**
   ```python
   import threading
   lock = threading.Lock()
   with lock:
       counter += 1
   ```

2. **Thread-safe data structures** — `queue.Queue`, `collections.deque` (for append/pop).

3. **Avoid shared mutable state** — Use message passing (queues) between threads instead of shared variables.

4. **Atomic operations** — Some operations are inherently atomic in CPython due to the GIL (e.g., `dict[key] = value`), but relying on this is fragile and non-portable.

5. **`asyncio`** — Single-threaded concurrency eliminates race conditions entirely.

**Trading context:** If a risk check thread reads position data while a trade execution thread is updating it, you could get an incorrect risk assessment. Use locks or separate the concerns with message queues.

---

## 8. Real-World Trading Scenarios

### Q8.1: Scenario — You notice your order book is showing stale prices. How do you diagnose and fix it?

**Answer:**

**Diagnosis steps:**

1. **Check sequence numbers** — Are we receiving all messages? Look for gaps in `seq_num`. If there are gaps, we're missing updates.
   ```python
   if header.seq_num != expected_seq + 1:
       log.warning(f"Gap: expected {expected_seq+1}, got {header.seq_num}")
   ```

2. **Check timestamps** — Compare the timestamp of the last processed message against wall clock time. A large discrepancy means we're falling behind (processing is too slow).

3. **Check the feed connection** — Is the socket still connected? Are we receiving heartbeats? A silent disconnect could mean we're processing buffered data.

4. **Check CPU/memory** — Is the process CPU-bound? Memory thrashing? GC pausing?

**Fixes:**
- If sequence gaps → implement retransmission request or snapshot recovery.
- If processing too slow → profile and optimise the hot path (as discussed in Q5.1).
- If network issue → implement redundant feed connections with automatic failover.
- Add monitoring: log latency metrics (time from message timestamp to processing complete).

---

### Q8.2: Scenario — Your trading strategy is sending too many orders and the exchange threatens to disconnect you. What do you do?

**Answer:**

**Immediate action:**
1. **Rate limit orders** — Implement a token bucket or leaky bucket rate limiter.
   ```python
   class RateLimiter:
       def __init__(self, max_per_second: int):
           self.max_per_second = max_per_second
           self.tokens = max_per_second
           self.last_refill = time.monotonic()

       def allow(self) -> bool:
           now = time.monotonic()
           elapsed = now - self.last_refill
           self.tokens = min(self.max_per_second, self.tokens + elapsed * self.max_per_second)
           self.last_refill = now
           if self.tokens >= 1:
               self.tokens -= 1
               return True
           return False
   ```
2. **Kill switch** — Have an emergency mechanism to halt all order sending.

**Root cause analysis:**
- Is the strategy oscillating (sending cancel/replace rapidly)? Fix the signal logic.
- Is it reacting to its own orders? (Feedback loop.) Add self-trade prevention.
- Are multiple instances running accidentally? Check process management.

**Prevention:**
- Pre-trade rate limiting as a mandatory component.
- Monitor order/cancel ratios.
- Implement circuit breakers that pause trading if thresholds are exceeded.
- Exchange-specific limits should be configurable, not hardcoded.

---

### Q8.3: Scenario — Implement a simple VWAP (Volume-Weighted Average Price) calculator.

**Answer:**

**VWAP** = Σ(price × volume) / Σ(volume) — a benchmark that shows the average price a security has traded at, weighted by volume.

```python
class VWAPCalculator:
    def __init__(self):
        self._cum_price_volume = 0.0  # Σ(price * volume)
        self._cum_volume = 0          # Σ(volume)

    def on_trade(self, price: float, volume: int) -> None:
        self._cum_price_volume += price * volume
        self._cum_volume += volume

    @property
    def vwap(self) -> float | None:
        if self._cum_volume == 0:
            return None
        return self._cum_price_volume / self._cum_volume

    def reset(self) -> None:
        self._cum_price_volume = 0.0
        self._cum_volume = 0
```

**Usage in trading:**
- Traders use VWAP as a benchmark — "I want to buy 10,000 shares at VWAP or better."
- **VWAP execution algorithm** splits a large order into small slices throughout the day, sizing each slice proportional to expected volume, to achieve a price close to VWAP.
- If your average execution price < VWAP (for buys), you outperformed.

---

### Q8.4: Scenario — Design a simple moving average crossover signal.

**Answer:**

A **moving average crossover** is a basic trading signal: buy when a fast MA crosses above a slow MA, sell when it crosses below.

```python
from collections import deque

class MovingAverage:
    def __init__(self, period: int):
        self.period = period
        self._window = deque(maxlen=period)
        self._sum = 0.0

    def update(self, value: float) -> float | None:
        if len(self._window) == self.period:
            self._sum -= self._window[0]
        self._window.append(value)
        self._sum += value
        if len(self._window) < self.period:
            return None
        return self._sum / self.period


class CrossoverSignal:
    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        self.fast_ma = MovingAverage(fast_period)
        self.slow_ma = MovingAverage(slow_period)
        self._prev_fast = None
        self._prev_slow = None

    def on_price(self, price: float) -> str | None:
        fast = self.fast_ma.update(price)
        slow = self.slow_ma.update(price)
        if fast is None or slow is None:
            return None

        signal = None
        if self._prev_fast is not None and self._prev_slow is not None:
            if self._prev_fast <= self._prev_slow and fast > slow:
                signal = "BUY"
            elif self._prev_fast >= self._prev_slow and fast < slow:
                signal = "SELL"

        self._prev_fast = fast
        self._prev_slow = slow
        return signal
```

**Why `deque(maxlen=N)` is ideal:** It automatically evicts the oldest element when full — no manual index management. Append and pop from both ends are O(1).

---

### Q8.5: Scenario — You're given a large CSV of historical trades. How would you efficiently compute the top 10 most traded symbols by volume?

**Answer:**

```python
import csv
from collections import Counter
import heapq

def top_traded_symbols(filepath: str, n: int = 10) -> list[tuple[str, int]]:
    volumes = Counter()

    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            volumes[row['symbol']] += int(row['volume'])

    return volumes.most_common(n)
```

**Time:** O(M + S log n) where M = number of rows, S = unique symbols.
- `Counter` accumulation: O(M).
- `most_common(n)`: uses a heap internally — O(S log n).

**For very large files (100GB+):**
```python
import pandas as pd

def top_traded_large(filepath: str, n: int = 10):
    # Process in chunks to avoid loading everything into memory
    chunks = pd.read_csv(filepath, usecols=['symbol', 'volume'], chunksize=1_000_000)
    totals = Counter()
    for chunk in chunks:
        for symbol, volume in chunk.groupby('symbol')['volume'].sum().items():
            totals[symbol] += volume
    return totals.most_common(n)
```

---

### Q8.6: Scenario — Implement an order matching engine for a single symbol.

**Answer:**

```python
import heapq
from dataclasses import dataclass, field
from typing import Generator

@dataclass(order=True)
class Order:
    price: int
    timestamp: int
    order_id: int = field(compare=False)
    volume: int = field(compare=False)

@dataclass
class Trade:
    buy_order_id: int
    sell_order_id: int
    price: int
    volume: int

class MatchingEngine:
    def __init__(self):
        self._bids: list[Order] = []  # max-heap (negate price)
        self._asks: list[Order] = []  # min-heap
        self._timestamp = 0

    def submit_order(self, order_id: int, side: str, price: int, volume: int) -> list[Trade]:
        self._timestamp += 1
        trades = []

        if side == 'B':
            trades = self._match_buy(order_id, price, volume)
        else:
            trades = self._match_sell(order_id, price, volume)

        return trades

    def _match_buy(self, order_id: int, price: int, volume: int) -> list[Trade]:
        trades = []
        remaining = volume

        while remaining > 0 and self._asks and self._asks[0].price <= price:
            best_ask = self._asks[0]
            fill_qty = min(remaining, best_ask.volume)
            trades.append(Trade(order_id, best_ask.order_id, best_ask.price, fill_qty))
            remaining -= fill_qty
            best_ask.volume -= fill_qty
            if best_ask.volume == 0:
                heapq.heappop(self._asks)

        if remaining > 0:
            order = Order(-price, self._timestamp, order_id, remaining)
            heapq.heappush(self._bids, order)

        return trades

    def _match_sell(self, order_id: int, price: int, volume: int) -> list[Trade]:
        trades = []
        remaining = volume

        while remaining > 0 and self._bids and -self._bids[0].price >= price:
            best_bid = self._bids[0]
            fill_qty = min(remaining, best_bid.volume)
            trades.append(Trade(best_bid.order_id, order_id, -best_bid.price, fill_qty))
            remaining -= fill_qty
            best_bid.volume -= fill_qty
            if best_bid.volume == 0:
                heapq.heappop(self._bids)

        if remaining > 0:
            order = Order(price, self._timestamp, order_id, remaining)
            heapq.heappush(self._asks, order)

        return trades
```

**Design decisions:**
- Bids stored with negated price so Python's min-heap acts as a max-heap.
- `@dataclass(order=True)` enables comparison by `(price, timestamp)` — price-time priority.
- Each `submit_order` returns a list of trades generated.

---

## 9. Testing & Reliability

### Q9.1: How would you test a trading system? What kinds of tests are important?

**Answer:**

| Level | What | Example |
|-------|------|---------|
| **Unit tests** | Individual functions/classes in isolation | `OrderBook.add()` correctly inserts |
| **Integration tests** | Components working together | Message parser → OrderBook pipeline produces correct output |
| **Property-based tests** | Invariants hold for random inputs | "Total volume is always non-negative" |
| **Regression tests** | Known-good outputs from known inputs | `diff result1.log output1.log` (exactly what your Makefile does) |
| **Fuzz testing** | Random/malformed binary input | Does the parser crash on corrupted data? |
| **Performance tests** | Latency and throughput benchmarks | "Process 1M messages in < 5 seconds" |
| **End-to-end tests** | Full pipeline with realistic data | Replay a day's market data and verify P&L |

**Property-based testing with Hypothesis:**
```python
from hypothesis import given, strategies as st
from orderbook import OrderBook

@given(
    order_id=st.integers(min_value=1, max_value=1000),
    price=st.integers(min_value=1, max_value=10000),
    volume=st.integers(min_value=1, max_value=10000),
)
def test_add_then_delete_leaves_empty_book(order_id, price, volume):
    book = OrderBook()
    book.add(order_id, "B", price, volume)
    book.delete(order_id, "B")
    bids, _ = book.depth(5)
    assert bids == []
```

---

### Q9.2: What is defensive programming? Give examples relevant to trading.

**Answer:**

Defensive programming assumes things will go wrong and protects against it.

**Examples in trading:**

1. **Validate all inputs:**
   ```python
   def add(self, order_id: int, side: str, price: int, volume: int):
       assert side in ('B', 'S'), f"Invalid side: {side}"
       assert volume > 0, f"Invalid volume: {volume}"
       assert price > 0, f"Invalid price: {price}"
   ```

2. **Handle unknown message types gracefully:**
   ```python
   else:
       log.warning(f"Unknown message type: {header.msg_type}")
       # Don't crash — skip and continue processing
   ```

3. **Idempotent operations:**
   ```python
   self._side(side).pop(order_id, None)  # Safe even if already deleted
   ```

4. **Circuit breakers:**
   ```python
   if abs(new_position) > MAX_POSITION:
       kill_all_orders()
       raise EmergencyHalt("Position limit breached")
   ```

5. **Sanity checks on computed values:**
   ```python
   if spread < 0:
       log.error("Negative spread — book is crossed, likely data error")
   ```

---

## 10. Behavioural / Culture Fit

### Q10.1: "Tell me about a time you solved a complex technical problem."

**Framework: STAR (Situation, Task, Action, Result)**

**Example (tailor to your experience):**
"In my university capstone project, we were building a real-time data pipeline that processed sensor data. The system was dropping 15% of messages under load. [Situation/Task]. I profiled the pipeline and found the bottleneck was JSON parsing in the ingestion layer. I replaced it with a binary protocol using Python's `struct` module, batched messages into chunks, and used `asyncio` to overlap I/O with processing. [Action]. This reduced dropped messages to <0.1% and cut end-to-end latency by 60%. [Result]."

---

### Q10.2: "Why quantitative trading? Why VivCourt?"

**Suggested talking points:**
- "I'm drawn to the intersection of technology and finance — where software quality directly impacts business outcomes."
- "Trading systems demand the highest standards: correctness, performance, and reliability. That's the kind of engineering I want to do."
- "VivCourt's focus on systematic trading means I'd work on technically challenging problems — from low-latency data processing to large-scale analysis systems."
- "I'm excited by the collaborative culture between engineers and traders — understanding the business context makes engineering more meaningful."
- "As a smaller firm, I expect to have broader exposure and take on more responsibility faster than at a larger company."

---

### Q10.3: "How do you handle working under pressure or tight deadlines?"

**Suggested approach:**
- "I prioritise ruthlessly — focus on the highest-impact tasks first."
- "I break large problems into smaller, testable pieces so I can deliver incrementally."
- "I communicate proactively — if something will take longer than expected, I flag it early."
- Give a concrete example from your experience.

---

### Q10.4: "Describe a time you had to collaborate with someone from a different discipline."

**Key points:**
- Emphasise empathy and communication skills.
- Show you can translate technical concepts for non-technical stakeholders (or vice versa).
- In trading, you'll collaborate with traders who think in terms of P&L, risk, and market dynamics — not code abstractions.

---

### Q10.5: "What's a recent technology or concept you've been learning about?"

**Strong answers for a quant trading role:**
- "I've been exploring lock-free data structures and how they enable ultra-low-latency systems."
- "I've been learning about market microstructure — how order flow, latency, and fee structures affect trading strategies."
- "I've been studying async programming patterns in Python and how they compare to event-driven architectures in C++."
- "I've been reading about the LMAX Disruptor pattern for high-performance message passing."

---

## Quick Reference: Key Concepts to Know Cold

| Topic | Must-Know |
|-------|-----------|
| **Python** | dict internals, generators, GIL, `struct`, `collections`, `typing`, list/tuple/set differences |
| **Data Structures** | Hash map, heap, sorted containers, deque, BST |
| **Algorithms** | Sorting (and stability), binary search, quickselect, time complexity analysis |
| **Trading** | Order book, bid/ask/spread, order types, price-time priority, VWAP, market data protocols |
| **Systems** | Latency, throughput, TCP vs UDP, multicast, message queues |
| **Concurrency** | threading, multiprocessing, asyncio, race conditions, locks |
| **Testing** | Unit tests, property-based tests, regression tests, fuzzing |
| **Design** | Modularity, separation of concerns, defensive programming, monitoring/observability |

---

*Good luck with the interview! The fact that you've built a working order book from a binary feed already demonstrates the core skills they're looking for.*
