import requests
import time
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []

def record_test(name, method, endpoint, expected_status, payload=None, headers=None, files=None):
    start_time = time.time()
    try:
        url = f"{BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            # Check if it's form data (login)
            if payload and "username" in payload and "password" in payload and endpoint == "/login":
                 response = requests.post(url, data=payload, headers=headers, timeout=10)
            elif files:
                 response = requests.post(url, files=files, headers=headers, timeout=10)
            else:
                 response = requests.post(url, json=payload, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=payload, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        try:
            body = response.json()
        except:
            body = response.text[:200] # Capture a snippet for non-JSON

        status_match = response.status_code == expected_status
        RESULTS.append({
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "actual_status": response.status_code,
            "expected_status": expected_status,
            "status_match": status_match,
            "response_time_ms": round(duration_ms, 2),
            "body_shape": str(type(body)),
            "body": body
        })
        return response
    except Exception as e:
        RESULTS.append({
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "error": str(e),
            "status_match": False
        })
        return None

def main():
    print("Starting API Audit Suite...")
    
    # --- 1. SETUP & AUTH ---
    # Register Student A
    record_test("Register Student A", "POST", "/register", 201, 
                {"username": "test_student_a", "email": "a@test.edu", "password": "password123"})
    # Login Student A
    resp_a = record_test("Login Student A", "POST", "/login", 200, 
                         {"username": "test_student_a", "password": "password123"})
    token_a = resp_a.json().get("access_token") if resp_a and resp_a.status_code == 200 else None
    
    # Register Student B
    record_test("Register Student B", "POST", "/register", 201, 
                {"username": "test_student_b", "email": "b@test.edu", "password": "password123"})
    # Login Student B
    resp_b = record_test("Login Student B", "POST", "/login", 200, 
                         {"username": "test_student_b", "password": "password123"})
    token_b = resp_b.json().get("access_token") if resp_b and resp_b.status_code == 200 else None

    # Admin Login
    resp_admin = record_test("Login Admin", "POST", "/login", 200, 
                             {"username": "admin", "password": "admin123"})
    token_admin = resp_admin.json().get("access_token") if resp_admin and resp_admin.status_code == 200 else None

    auth_a = {"Authorization": f"Bearer {token_a}"} if token_a else {}
    auth_b = {"Authorization": f"Bearer {token_b}"} if token_b else {}
    auth_admin = {"Authorization": f"Bearer {token_admin}"} if token_admin else {}

    # --- 2. DATA CRUD ---
    # Student A: Add 3 records
    for i in range(3):
        record_test(f"Add Data A-{i}", "POST", "/add-data", 201, 
                    {"date": "2026-04-01", "temperature": 25.0 + i, "humidity": 60.0, "aqi": 50 + i, 
                     "pollution_level": "Good", "location": "Test Lab A"}, headers=auth_a)
    
    # Student B: Add 2 records
    for i in range(2):
        record_test(f"Add Data B-{i}", "POST", "/add-data", 201, 
                    {"date": "2026-04-02", "temperature": 22.0 + i, "humidity": 55.0, "aqi": 40 + i, 
                     "pollution_level": "Good", "location": "Test Lab B"}, headers=auth_b)

    # View Data isolation check
    resp_view_a = record_test("View Data (Student A Isolation)", "GET", "/view-data", 200, headers=auth_a)
    if resp_view_a and resp_view_a.status_code == 200:
        data = resp_view_a.json()
        b_data = [d for d in data if d.get("created_by") == "test_student_b"]
        if b_data:
            print("ALERT: Student A can see Student B's data!")

    # Admin: View All
    record_test("View Data (Admin Visibility)", "GET", "/view-data", 200, headers=auth_admin)

    # Edit/Delete Logic
    if resp_view_a and resp_view_a.status_code == 200 and len(data) > 0:
        rid = data[0]['id']
        # Owner Update
        record_test("Edit Data (Owner)", "PUT", f"/edit-data/{rid}", 200, 
                    {"date": "2026-04-01", "temperature": 30.0, "humidity": 50.0, "aqi": 60, 
                     "pollution_level": "Moderate", "location": "Updated Lab"}, headers=auth_a)
        # Cross-ownership Update (Student B tries to edit A's record)
        record_test("Edit Data (Forbidden Cross-User)", "PUT", f"/edit-data/{rid}", 403, 
                    {"date": "2026-04-01", "temperature": 0, "humidity": 0, "aqi": 0, 
                     "pollution_level": "Hack", "location": "XSS"}, headers=auth_b)
        # Admin Override
        record_test("Edit Data (Admin Override)", "PUT", f"/edit-data/{rid}", 200, 
                    {"date": "2026-04-01", "temperature": 35.0, "humidity": 45.0, "aqi": 70, 
                     "pollution_level": "Bad", "location": "Admin Fix"}, headers=auth_admin)
        # Owner Delete
        record_test("Delete Data (Owner)", "DELETE", f"/delete-data/{rid}", 200, headers=auth_a)

    # Download CSV (Unauthenticated)
    record_test("Download CSV (Public)", "GET", "/download-csv", 200)

    # --- 3. ADMIN ANALYTICS ---
    admin_eps = [
        "/admin/analytics", "/admin/location-analytics", "/admin/locations",
        "/admin/trends/aqi-monthly", "/admin/trends/pollution-dist", "/admin/trends/temp-hum-correlation"
    ]
    for ep in admin_eps:
        record_test(f"Admin Access: {ep}", "GET", ep, 200, headers=auth_admin)
        record_test(f"Student Access: {ep}", "GET", ep, 403, headers=auth_a)
        record_test(f"No Token Access: {ep}", "GET", ep, 401)

    # --- 4. NEGATIVE & SECURITY ---
    record_test("Login Failed Password", "POST", "/login", 400, {"username": "admin", "password": "wrong"})
    record_test("Login Unknown User", "POST", "/login", 400, {"username": "nonexistent", "password": "password"})
    record_test("Add Data Missing Fields", "POST", "/add-data", 422, {"temp": 10}, headers=auth_a)
    record_test("Add Data Invalid AQI", "POST", "/add-data", 422, 
                {"date": "2026-04-01", "temperature": 25, "humidity": 60, "aqi": 999999, 
                 "pollution_level": "N/A", "location": "Test"}, headers=auth_a)
    record_test("PUT Non-existent ID", "PUT", "/edit-data/999999", 404, 
                {"date": "2026-04-01", "temperature": 25, "humidity": 60, "aqi": 50, 
                 "pollution_level": "Good", "location": "Test"}, headers=auth_admin)

    # --- 5. CLEANUP (Admin deletes test users) ---
    record_test("Admin Delete Student A", "DELETE", "/admin/users/test_student_a", 200, headers=auth_admin)
    record_test("Admin Delete Student B", "DELETE", "/admin/users/test_student_b", 200, headers=auth_admin)
    
    # Re-login check
    record_test("Login Deleted User", "POST", "/login", 400, {"username": "test_student_a", "password": "password123"})

    with open("audit_results.json", "w") as f:
        json.dump(RESULTS, f, indent=4)
    print("Audit Complete. results saved to audit_results.json")

if __name__ == "__main__":
    main()
