import time
from fastapi import FastAPI
import redis
from contextlib import asynccontextmanager

# Requires redis server running locally
# e.g., docker run --name some-redis -p 6379:6379 -d redis
# And pip install redis
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    # Initialize if not exists
    if not redis_client.exists("counter"):
        redis_client.set("counter", 0)
    yield
    redis_client.close()

app = FastAPI(lifespan=lifespan)

@app.post("/increment")
def increment():
    start_time = time.time()
    # Redis INCR is atomic
    new_val = redis_client.incr("counter")
    latency = (time.time() - start_time) * 1000
    return {"counter": new_val, "latency_ms": latency}

@app.get("/state")
def get_state():
    val = redis_client.get("counter")
    return {"counter": int(val) if val else 0}
