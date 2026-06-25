import sqlite3
import time
from fastapi import FastAPI
from contextlib import asynccontextmanager

DB_FILE = "state.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    # Initialize counter if not exists
    cursor.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('counter', 0)")
    conn.commit()
    conn.close()

def get_db_connection():
    # In SQLite, concurrent writes lock the DB. 
    # timeout=5.0 handles small waits during locks.
    return sqlite3.connect(DB_FILE, timeout=5.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/increment")
def increment():
    start_time = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Use a transaction to safely increment
        cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
        cursor.execute("SELECT value FROM state WHERE key='counter'")
        current_val = cursor.fetchone()[0]
        new_val = current_val + 1
        cursor.execute("UPDATE state SET value=? WHERE key='counter'", (new_val,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()
    
    latency = (time.time() - start_time) * 1000
    return {"counter": new_val, "latency_ms": latency}

@app.get("/state")
def get_state():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM state WHERE key='counter'")
    current_val = cursor.fetchone()[0]
    conn.close()
    return {"counter": current_val}
