from fastapi import FastAPI, HTTPException, Query, Cookie, Response, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from . import database
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Data Models
class SensorData(BaseModel):
    value: float
    unit: str
    timestamp: Optional[str] = None

class SensorDataUpdate(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[str] = None

class User(BaseModel):
    username: str
    email: str
    password: str
    location: str

class Device(BaseModel):
    device_id: str
    name: str

class WardrobeItem(BaseModel):
    item_name: str
    category: str
    color: str

@app.on_event("startup")
async def startup_event():
    database.create_tables()

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    with open('static/index.html') as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open('static/login.html') as f:
        return f.read()

@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    with open('static/signup.html') as f:
        return f.read()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(session_token: str = Cookie(None)):
    if not database.get_user_by_session(session_token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    with open('static/dashboard.html') as f:
        return f.read()

@app.get("/wardrobe", response_class=HTMLResponse)
async def wardrobe_page(session_token: str = Cookie(None)):
    if not database.get_user_by_session(session_token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    with open('static/wardrobe.html') as f:
        return f.read()

# Authentication Routes
@app.post("/login")
async def login(response: Response, email: str = Form(...), password: str = Form(...)):
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user or not database.verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        session_token = database.create_session(user["id"])
        response.set_cookie(key="session_token", value=session_token, httponly=True)
        
        return {"message": "Logged in successfully"}
    finally:
        cursor.close()
        conn.close()

@app.post("/signup")
async def signup(response: Response, username: str = Form(...), email: str = Form(...),
                password: str = Form(...), location: str = Form(...)):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        hashed_password = database.hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, location) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_password, location)
        )
        conn.commit()
        
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_id = cursor.fetchone()[0]
        
        session_token = database.create_session(user_id)
        response.set_cookie(key="session_token", value=session_token, httponly=True)
        
        return {"message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    finally:
        cursor.close()
        conn.close()

@app.post("/logout")
async def logout(response: Response, session_token: str = Cookie(None)):
    if session_token:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_token = %s", (session_token,))
        conn.commit()
        cursor.close()
        conn.close()
    
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}

# Device Routes
@app.post("/devices")
async def register_device(device: Device, session_token: str = Cookie(None)):
    user = database.get_user_by_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO devices (device_id, name, user_id) VALUES (%s, %s, %s)",
            (device.device_id, device.name, user["id"])
        )
        conn.commit()
        return {"message": "Device registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Device ID already exists")
    finally:
        cursor.close()
        conn.close()

@app.get("/devices")
async def get_devices(session_token: str = Cookie(None)):
    user = database.get_user_by_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM devices WHERE user_id = %s", (user["id"],))
    devices = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return devices

@app.delete("/devices/{device_id}")
async def delete_device(device_id: str, session_token: str = Cookie(None)):
    user = database.get_user_by_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id FROM devices WHERE device_id = %s AND user_id = %s",
            (device_id, user["id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Device not found")
        
        cursor.execute("DELETE FROM devices WHERE device_id = %s", (device_id,))
        conn.commit()
        return {"message": "Device deleted successfully"}
    finally:
        cursor.close()
        conn.close()

# Sensor Data Routes
@app.get("/api/{sensor_type}")
async def get_sensor_data(
    sensor_type: str,
    order_by: Optional[str] = Query(None, alias="order-by"),
    start_date: Optional[str] = Query(None, alias="start-date"),
    end_date: Optional[str] = Query(None, alias="end-date"),
    session_token: str = Cookie(None)
):
    user = database.get_user_by_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = f"SELECT * FROM {sensor_type} WHERE user_id = %s"
    params = [user["id"]]
    
    if start_date:
        query += " AND timestamp >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= %s"
        params.append(end_date)
    
    if order_by:
        if order_by not in ['value', 'timestamp']:
            raise HTTPException(status_code=400, detail="Invalid order-by parameter")
        query += f" ORDER BY {order_by}"
    
    cursor.execute(query, params)
    result = cursor.fetchall()
    
    for row in result:
        if row.get('timestamp'):
            row['timestamp'] = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.close()
    conn.close()
    return result

@app.post("/api/{sensor_type}")
async def add_sensor_data(sensor_type: str, data: SensorData, session_token: str = Cookie(None)):
    user = database.get_user_by_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if sensor_type not in ['temperature', 'humidity', 'light']:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    timestamp = data.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute(
        f"INSERT INTO {sensor_type} (value, unit, timestamp, user_id) VALUES (%s, %s, %s, %s)",
        (data.value, data.unit, timestamp, user["id"])
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Data added successfully"}

if __name__ == "__main__":
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=6543, reload=True)