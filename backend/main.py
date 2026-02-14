from fastapi import FastAPI
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
import csv


app = FastAPI()

# Enable CORS (important for frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Environmental Data Hub Running"}

# POST API to add environmental data
@app.post("/add-data")
def add_data(date: str, temperature: float, humidity: float, aqi: int, pollution_level: str):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO environment_data (date, temperature, humidity, aqi, pollution_level)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (date, temperature, humidity, aqi, pollution_level))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "Data inserted successfully"}

# GET API to view environmental data
@app.get("/view-data")
def view_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM environment_data")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data
@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    conn = get_connection()
    cursor = conn.cursor()

    contents = await file.read()
    lines = contents.decode().splitlines()
    reader = csv.reader(lines)

    next(reader)  # skip header row

    for row in reader:
        cursor.execute("""
            INSERT INTO environment_data (date, temperature, humidity, aqi, pollution_level)
            VALUES (%s, %s, %s, %s, %s)
        """, row)

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "CSV data uploaded successfully"}
@app.get("/download-csv")
def download_csv():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM environment_data")
    rows = cursor.fetchall()

    file_path = "environment_data.csv"

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID","Date","Temperature","Humidity","AQI","Pollution Level"])
        writer.writerows(rows)

    cursor.close()
    conn.close()

    return FileResponse(file_path, filename="environment_data.csv")
