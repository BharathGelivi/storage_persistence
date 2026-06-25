import json
import os
import time
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import Dict
from threading import Lock

STORAGE_FILE = "state.json"
state: Dict[str, int] = {}
state_lock = Lock()

def load_state():
    global state
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                state = json.load(f)
        except json.JSONDecodeError:
            state = {"counter": 0}
    else:
        state = {"counter": 0}

def save_state():
    # Simple write, not atomic, prone to corruption if crash happens during write
    # We will use this simple version to measure baseline JSON metrics
    with open(STORAGE_FILE, 'w') as f:
        json.dump(state, f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    load_state()
    yield
    # Shutdown
    # We can save on shutdown, but if we crash we lose data.
    # For persistence, we should save on every mutation.

app = FastAPI(lifespan=lifespan)

@app.post("/increment")
def increment():
    with state_lock:
        start_time = time.time()
        state["counter"] = state.get("counter", 0) + 1
        save_state() # Save synchronously on every request
        latency = (time.time() - start_time) * 1000
    return {"counter": state["counter"], "latency_ms": latency}

@app.get("/state")
def get_state():
    with state_lock:
        return {"counter": state.get("counter", 0)}
