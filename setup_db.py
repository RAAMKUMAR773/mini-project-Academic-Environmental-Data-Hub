import mysql.connector
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv('backend/.env')

host = os.getenv("DB_HOST", "localhost")
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME", "environment_db")

try:
    # Connect without database to create it
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
    print(f"Database {database} created or already exists.")
    cursor.execute(f"USE {database}")

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'student'
        )
    """)
    print("Table 'users' verified.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environment_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            temperature FLOAT NOT NULL,
            humidity FLOAT NOT NULL,
            aqi INT NOT NULL,
            pollution_level VARCHAR(50) NOT NULL,
            location VARCHAR(255) NOT NULL,
            created_by VARCHAR(255),
            FOREIGN KEY (created_by) REFERENCES users(username) ON DELETE SET NULL
        )
    """)
    print("Table 'environment_data' verified.")

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password = pwd_context.hash("admin123")
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES ('admin', 'admin@example.com', %s, 'admin')
        """, (hashed_password,))
        conn.commit()
        print("Default admin user created with hashed password.")
    else:
        print("Admin user already exists.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
