import mysql.connector
import mysql.connector.pooling
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection pool
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "environment_db")
)

def get_connection():
    return db_pool.get_connection()