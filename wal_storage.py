import os
import time
from fastapi import FastAPI
from contextlib import asynccontextmanager
from threading import Lock

WAL_FILE = "state.wal"
state = {"counter": 0}
wal_lock = Lock()
wal_fd = None

def load_from_wal():
    global state
    if os.path.exists(WAL_FILE):
        with open(WAL_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(":")
                    if len(parts) == 2 and parts[0] == "increment":
                        try:
                            # Replay the increment
                            # The log entry just says "increment:1", we rebuild state
                            state["counter"] += int(parts[1])
                        except ValueError:
                            pass

def append_to_wal(action: str, value: str):
    global wal_fd
    if wal_fd is not None:
        wal_fd.write(f"{action}:{value}\n")
        wal_fd.flush()
        os.fsync(wal_fd.fileno()) # Force write to disk for durability

@asynccontextmanager
async def lifespan(app: FastAPI):
    global wal_fd
    load_from_wal()
    # Open for append
    wal_fd = open(WAL_FILE, 'a')
    yield
    if wal_fd:
        wal_fd.close()

app = FastAPI(lifespan=lifespan)

@app.post("/increment")
def increment():
    with wal_lock:
        start_time = time.time()
        state["counter"] += 1
        append_to_wal("increment", "1")
        latency = (time.time() - start_time) * 1000
    return {"counter": state["counter"], "latency_ms": latency}

@app.get("/state")
def get_state():
    with wal_lock:
        return {"counter": state["counter"]}
