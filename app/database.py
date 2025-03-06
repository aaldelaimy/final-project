import mysql.connector
import os
from dotenv import load_dotenv
import bcrypt
from datetime import datetime, timedelta
import uuid

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            location VARCHAR(255)
        )
    """)
    
    # Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create devices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_id VARCHAR(255) UNIQUE NOT NULL,
            user_id INT,
            name VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create wardrobe table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wardrobe (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            item_name VARCHAR(255) NOT NULL,
            category VARCHAR(255),
            color VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_session(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    session_token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=1)
    
    cursor.execute(
        "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
        (user_id, session_token, expires_at)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return session_token

def get_user_by_session(session_token: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT users.* FROM users 
        JOIN sessions ON users.id = sessions.user_id 
        WHERE sessions.session_token = %s AND sessions.expires_at > NOW()
    """, (session_token,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return user