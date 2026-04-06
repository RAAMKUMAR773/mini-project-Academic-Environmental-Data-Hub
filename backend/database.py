import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection pool for PostgreSQL
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    print("PostgreSQL connection pool created successfully")
except Exception as e:
    print(f"Error creating PostgreSQL connection pool: {e}")
    db_pool = None

def get_connection():
    if db_pool:
        # For psycopg2, we need to return a connection that works like the MySQL one
        # but the way we close it will change in main.py
        return db_pool.getconn()
    return None

def release_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)