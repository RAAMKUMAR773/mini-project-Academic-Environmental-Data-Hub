from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
import csv
import os
import logging
from dotenv import load_dotenv
from database import get_connection
from passlib.context import CryptContext

# Setup logging (Stdout only for Vercel)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Academic Environmental Data Hub")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend Static Files
# Mount the frontend directory. 'html=True' will automatically serve index.html or login.html if requested
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")


# Models
class DataPoint(BaseModel):
    date: str
    temperature: float = Field(..., ge=-50, le=60)
    humidity: float = Field(..., ge=0, le=100)
    aqi: int = Field(..., ge=0, le=500)
    pollution_level: str
    location: str = Field(..., min_length=1, max_length=255)

class Token(BaseModel):
    access_token: str
    token_type: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/", response_class=HTMLResponse)
def home():
    # Attempt multiple paths for serverless compatibility
    paths = [
        "../frontend/login.html",
        "frontend/login.html",
        "./frontend/login.html"
    ]
    for path in paths:
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            continue
    return HTMLResponse("<h1>404: Frontend not found</h1>", status_code=404)

@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    try:
        with open("../frontend/signup.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        with open("frontend/signup.html", "r") as f:
            return f.read()


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
        if user and verify_password(form_data.password, user["password_hash"]):
            access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
            return {"access_token": access_token, "token_type": "bearer"}
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (user.username, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        hashed_password = get_password_hash(user.password)
        cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'student')",
                       (user.username, user.email, hashed_password))
        conn.commit()
        return {"message": "Registration successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.post("/add-data", status_code=status.HTTP_201_CREATED)
def add_data(data: DataPoint, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO environment_data (date, temperature, humidity, aqi, pollution_level, location, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (data.date, data.temperature, data.humidity, data.aqi, data.pollution_level, data.location, current_user["username"]))
        conn.commit()
        return {"message": "Data inserted successfully"}
    except Exception as e:
        logger.error(f"Add data error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.get("/view-data", response_model=List[dict])
def view_data(current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if current_user["role"] == "admin":
            cursor.execute("SELECT * FROM environment_data")
        else:
            cursor.execute("SELECT * FROM environment_data WHERE created_by = %s", (current_user["username"],))
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"View data error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    contents = await file.read()
    lines = contents.decode().splitlines()
    reader = csv.reader(lines)
    next(reader)  # skip header row

    conn = get_connection()
    cursor = conn.cursor()
    try:
        for row in reader:
            # Append created_by to the row if it's not in CSV
            # Expecting CSV columns: date, temp, humidity, aqi, pollution, location
            row_data = list(row) + [current_user["username"]]
            cursor.execute("""
                INSERT INTO environment_data (date, temperature, humidity, aqi, pollution_level, location, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, row_data)
        conn.commit()
        return {"message": "CSV data uploaded successfully"}
    finally:
        cursor.close()
        conn.close()

@app.get("/download-csv")
def download_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT date, temperature, humidity, aqi, pollution_level, location, created_by FROM environment_data")
        rows = cursor.fetchall()
        file_path = "environment_data.csv"
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Temperature","Humidity","AQI","Pollution Level", "Location", "Created By"])
            writer.writerows(rows)
        return FileResponse(file_path, filename="environment_data.csv")
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

# Admin Endpoints
@app.get("/admin/analytics")
def get_analytics(location: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if location:
            query = """
                SELECT 
                    date,
                    temperature as avg_temp,
                    humidity as avg_humidity,
                    aqi as avg_aqi
                FROM environment_data
                WHERE location = %s
                ORDER BY date ASC
            """
            cursor.execute(query, (location,))
        else:
            query = """
                SELECT 
                    date,
                    temperature as avg_temp,
                    humidity as avg_humidity,
                    aqi as avg_aqi
                FROM environment_data
                ORDER BY date ASC
                LIMIT 100
            """
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/location-analytics")
def get_location_analytics(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                location,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity,
                AVG(aqi) as avg_aqi,
                COUNT(*) as record_count
            FROM environment_data
            GROUP BY location
            ORDER BY avg_aqi DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/locations")
def get_locations(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT location FROM environment_data")
        locations = [row[0] for row in cursor.fetchall() if row[0]]
        return locations
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/trends/aqi-monthly")
def get_aqi_monthly_trend(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                DATE_FORMAT(date, '%Y-%m') as month,
                AVG(aqi) as avg_aqi
            FROM environment_data
            GROUP BY month
            ORDER BY month ASC
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/trends/pollution-dist")
def get_pollution_distribution(location: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if location:
            query = "SELECT pollution_level, COUNT(*) as count FROM environment_data WHERE location = %s GROUP BY pollution_level"
            cursor.execute(query, (location,))
        else:
            query = "SELECT pollution_level, COUNT(*) as count FROM environment_data GROUP BY pollution_level"
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/trends/temp-hum-correlation")
def get_temp_hum_correlation(location: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if location:
            query = "SELECT temperature, humidity FROM environment_data WHERE location = %s"
            cursor.execute(query, (location,))
        else:
            query = "SELECT temperature, humidity FROM environment_data"
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/users")
def get_user_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT username, email, role, 
            (SELECT COUNT(*) FROM environment_data WHERE created_by = users.username) as record_count
            FROM users
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.delete("/admin/users/{username}")
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete the primary admin account")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
            
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        return {"message": f"User {username} deleted successfully"}
    finally:
        cursor.close()
        conn.close()

@app.post("/admin/register", status_code=status.HTTP_201_CREATED)
async def admin_register(user: UserRegister, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (user.username, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        hashed_password = get_password_hash(user.password)
        cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'student')",
                       (user.username, user.email, hashed_password))
        conn.commit()
        return {"message": "User registered successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Admin registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.put("/edit-data/{data_id}")
def edit_data(data_id: int, data: DataPoint, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if record exists and if user has permission
        cursor.execute("SELECT created_by FROM environment_data WHERE id = %s", (data_id,))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        if current_user["role"] != "admin" and record[0] != current_user["username"]:
            raise HTTPException(status_code=403, detail="Not authorized to edit this record")
            
        query = """
            UPDATE environment_data 
            SET date=%s, temperature=%s, humidity=%s, aqi=%s, pollution_level=%s, location=%s
            WHERE id=%s
        """
        cursor.execute(query, (data.date, data.temperature, data.humidity, data.aqi, data.pollution_level, data.location, data_id))
        conn.commit()
        return {"message": "Data updated successfully"}
    except Exception as e:
        logger.error(f"Edit data error: {e}")
        raise e if isinstance(e, HTTPException) else HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

@app.delete("/delete-data/{data_id}")
def delete_data(data_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if record exists and if user has permission
        cursor.execute("SELECT created_by FROM environment_data WHERE id = %s", (data_id,))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        if current_user["role"] != "admin" and record[0] != current_user["username"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this record")
            
        cursor.execute("DELETE FROM environment_data WHERE id = %s", (data_id,))
        conn.commit()
        return {"message": "Data deleted successfully"}
    except Exception as e:
        logger.error(f"Delete data error: {e}")
        raise e if isinstance(e, HTTPException) else HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

