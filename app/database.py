import mysql.connector
import pandas as pd
import os
from datetime import datetime
import time

def get_db_connection():
    # Add retry logic
    max_retries = 30
    for attempt in range(max_retries):
        try:
            return mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DATABASE")
            )
        except mysql.connector.Error:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait 1 second before retrying
                continue
            raise

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