# FastAPI State Persistence Methods

This directory explores different methods to persist state in a FastAPI application, ensuring data survives server shutdowns. We focus on a simple state (a counter) and examine how different backends handle mutations and durability.

## 1. JSON File Storage (`json_storage.py`)
State is serialized and written to a `state.json` file on every request.

*   **Pros**: Trivial to implement, human-readable, requires no extra services.
*   **Cons**: Prone to corruption (if power is lost mid-write), very slow for high throughput (entire state is serialized and written on every change).
*   **Metrics**:
    *   **Throughput**: Low (disk I/O bound).
    *   **Latency**: High (serialization + full file write).
    *   **Concurrency**: Poor (requires a strict thread lock to prevent concurrent writes mangling the file).

## 2. Write-Ahead Log (WAL) (`wal_storage.py`)
State mutations are appended as events to a `state.wal` file. On startup, the log is replayed to rebuild the state.

*   **Pros**: Blazing fast writes (append-only is the fastest disk operation), very durable, immune to partial-write corruption (incomplete lines are ignored on replay).
*   **Cons**: Log file grows indefinitely (requires a compaction/snapshotting strategy for long-running apps), startup time increases linearly with the number of events.
*   **Metrics**:
    *   **Throughput**: High (append-only disk I/O).
    *   **Latency**: Very Low (just flushing a buffer).
    *   **Recovery Time**: Depends on log size (O(N) where N is number of events).

## 3. SQLite (`sqlite_storage.py`)
State is stored in a local SQLite database (`state.db`), utilizing SQL transactions.

*   **Pros**: Full ACID compliance, robust against corruption, allows complex querying, built-in to Python.
*   **Cons**: SQLite locks the *entire database* for writes. Concurrent writes will block and queue up.
*   **Metrics**:
    *   **Throughput**: Medium (transactions have overhead).
    *   **Latency**: Medium (B-Tree updates and journal syncs).
    *   **Concurrency**: Write concurrency is a bottleneck due to database-level locking.

## 4. Redis (`redis_storage.py`)
State is pushed to an external Redis instance (in-memory key-value store).

*   **Pros**: Extreme throughput, atomic operations (like `INCR`), designed for heavy concurrency, allows sharing state across multiple FastAPI worker processes.
*   **Cons**: Requires running an external service, data must fit in RAM (though Redis has RDB/AOF persistence).
*   **Metrics**:
    *   **Throughput**: Extremely High.
    *   **Latency**: Very Low (network roundtrip is usually <1ms locally).
    *   **Durability**: Configurable (AOF for durability, RDB for snapshots).

## 5. PostgreSQL (`postgres_storage.py`)
State is stored in an external PostgreSQL database, utilizing atomic `UPDATE ... RETURNING` for increments.

*   **Pros**: Full ACID compliance, robust against corruption, handles concurrent connections well, standard for relational data.
*   **Cons**: Requires running an external service, write latency includes network overhead.
*   **Metrics**:
    *   **Throughput**: High.
    *   **Latency**: Medium-Low (network roundtrip + database commit).
    *   **Concurrency**: Excellent concurrency handling compared to SQLite.

## Running Benchmarks
Use the provided `benchmark.py` to test the throughput and latency of these methods:
```bash
# Start an app (e.g., WAL)
uvicorn wal_storage:app --workers 1

# In another terminal, run the benchmark
python benchmark.py --url http://127.0.0.1:8000/increment --requests 10000 --concurrency 50
```
