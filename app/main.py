from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from . import database
import uvicorn

app = FastAPI()

class SensorData(BaseModel):
    value: float
    unit: str
    timestamp: Optional[str] = None

class SensorDataUpdate(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    database.create_tables()

@app.get("/api/{sensor_type}/count")
async def get_sensor_count(sensor_type: str):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {sensor_type}")
    count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    return count

@app.get("/api/{sensor_type}")
async def get_sensor_data(
    sensor_type: str,
    order_by: Optional[str] = Query(None, alias="order-by"),
    start_date: Optional[str] = Query(None, alias="start-date"),
    end_date: Optional[str] = Query(None, alias="end-date")
):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = f"SELECT * FROM {sensor_type} WHERE 1=1"
    params = []
    
    if start_date:
        try:
            # Parse the ISO format date
            start_dt = datetime.fromisoformat(start_date.replace('Z', ''))
            query += " AND timestamp >= %s"
            params.append(start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")
    
    if end_date:
        try:
            # Parse the ISO format date
            end_dt = datetime.fromisoformat(end_date.replace('Z', ''))
            query += " AND timestamp <= %s"
            params.append(end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end date format")
    
    if order_by:
        if order_by not in ['value', 'timestamp']:
            raise HTTPException(status_code=400, detail="Invalid order-by parameter")
        query += f" ORDER BY {order_by}"
    
    cursor.execute(query, params)
    result = cursor.fetchall()
    
    # Convert timestamps to ISO format in the response
    for row in result:
        if row.get('timestamp'):
            row['timestamp'] = row['timestamp'].strftime('%Y-%m-%dT%H:%M:%S')
    
    cursor.close()
    conn.close()
    return result

@app.post("/api/{sensor_type}")
async def create_sensor_data(sensor_type: str, data: SensorData):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        if data.timestamp:
            timestamp = datetime.fromisoformat(data.timestamp.replace('Z', ''))
        else:
            timestamp = datetime.now()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")
    
    query = f"INSERT INTO {sensor_type} (value, unit, timestamp) VALUES (%s, %s, %s)"
    cursor.execute(query, (data.value, data.unit, timestamp))
    
    new_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"id": new_id}

@app.get("/api/{sensor_type}/{id}")
async def get_sensor_data_by_id(sensor_type: str, id: int):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(f"SELECT * FROM {sensor_type} WHERE id = %s", (id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Data not found")
    
    # Convert timestamp to ISO format
    if result.get('timestamp'):
        result['timestamp'] = result['timestamp'].strftime('%Y-%m-%dT%H:%M:%S')
    
    cursor.close()
    conn.close()
    return result

@app.put("/api/{sensor_type}/{id}")
async def update_sensor_data(sensor_type: str, id: int, data: SensorDataUpdate):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    if data.value is not None:
        updates.append("value = %s")
        values.append(data.value)
    if data.unit is not None:
        updates.append("unit = %s")
        values.append(data.unit)
    if data.timestamp is not None:
        try:
            timestamp = datetime.fromisoformat(data.timestamp.replace('Z', ''))
            updates.append("timestamp = %s")
            values.append(timestamp)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format")
    
    if not updates:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    values.append(id)
    query = f"UPDATE {sensor_type} SET {', '.join(updates)} WHERE id = %s"
    cursor.execute(query, values)
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Data not found")
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Updated successfully"}

@app.delete("/api/{sensor_type}/{id}")
async def delete_sensor_data(sensor_type: str, id: int):
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"DELETE FROM {sensor_type} WHERE id = %s", (id,))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Data not found")
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=6543, reload=True)