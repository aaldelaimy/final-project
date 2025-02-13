import mysql.connector
import pandas as pd
import os
from datetime import datetime
import time
from dotenv import load_dotenv
import sys

# Print current working directory
print("Current working directory:", os.getcwd())

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    # Debug prints
    print("Environment variables:")
    print("MYSQL_HOST:", os.getenv("MYSQL_HOST"))
    print("MYSQL_USER:", os.getenv("MYSQL_USER"))
    print("MYSQL_PASSWORD:", os.getenv("MYSQL_PASSWORD"))
    print("MYSQL_DATABASE:", os.getenv("MYSQL_DATABASE"))
    
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        sys.exit(1)

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables for each sensor type
    tables = {
        'temperature': 'CREATE TABLE IF NOT EXISTS temperature (id INT AUTO_INCREMENT PRIMARY KEY, value FLOAT, unit VARCHAR(10), timestamp DATETIME)',
        'humidity': 'CREATE TABLE IF NOT EXISTS humidity (id INT AUTO_INCREMENT PRIMARY KEY, value FLOAT, unit VARCHAR(10), timestamp DATETIME)',
        'light': 'CREATE TABLE IF NOT EXISTS light (id INT AUTO_INCREMENT PRIMARY KEY, value FLOAT, unit VARCHAR(10), timestamp DATETIME)'
    }
    
    for table_query in tables.values():
        cursor.execute(table_query)
    
    conn.commit()
    return seed_tables(cursor, conn)

def seed_tables(cursor, conn):
    sensor_files = {
        'temperature': './sample/temperature.csv',
        'humidity': './sample/humidity.csv',
        'light': './sample/light.csv'
    }
    
    for sensor_type, file_path in sensor_files.items():
        if os.path.exists(file_path):
            # Check if table is empty before seeding
            cursor.execute(f"SELECT COUNT(*) FROM {sensor_type}")
            if cursor.fetchone()[0] == 0:
                df = pd.read_csv(file_path)
                
                # Prepare data for insertion
                insert_query = f"INSERT INTO {sensor_type} (value, unit, timestamp) VALUES (%s, %s, %s)"
                values = [(row['value'], row['unit'], row['timestamp']) for _, row in df.iterrows()]
                
                # Insert in batches
                cursor.executemany(insert_query, values)
                conn.commit()
    
    cursor.close()
    conn.close()