import psycopg2
import time
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Use environment variables with defaults
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "mysecretpassword")
DB_NAME = os.environ.get("DB_NAME", "postgres")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )

def init_db():
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            key VARCHAR(255) PRIMARY KEY,
            value INTEGER
        )
    ''')
    # Initialize counter if not exists
    cursor.execute("INSERT INTO state (key, value) VALUES ('counter', 0) ON CONFLICT (key) DO NOTHING")
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database. Is Postgres running? {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/increment")
def increment():
    start_time = time.time()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Postgres can do this atomically with UPDATE ... RETURNING
        cursor.execute("UPDATE state SET value = value + 1 WHERE key = 'counter' RETURNING value")
        result = cursor.fetchone()
        
        if result:
            new_val = result[0]
        else:
            # If for some reason it wasn't there
            cursor.execute("INSERT INTO state (key, value) VALUES ('counter', 1) ON CONFLICT (key) DO UPDATE SET value = state.value + 1 RETURNING value")
            new_val = cursor.fetchone()[0]

        conn.commit()
    except psycopg2.Error as e:
        if 'conn' in locals():
            conn.rollback()
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()
    
    latency = (time.time() - start_time) * 1000
    return {"counter": new_val, "latency_ms": latency}

@app.get("/state")
def get_state():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM state WHERE key='counter'")
        result = cursor.fetchone()
        current_val = result[0] if result else 0
    except psycopg2.Error as e:
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()
    return {"counter": current_val}



#docker run --name local-postgres -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres
#Host: localhost

#Port: 5432

#User: postgres

#Password: mysecretpassword