# Academic Environmental Data Hub v2.0

A premium, production-ready platform for monitoring and analyzing environmental data. Modernized with a high-end UI, secure backend, and easy deployment options.

## 🚀 Key Features
- **Premium UI/UX**: Modern Tailwind CSS design with Glassmorphism and vibrant visualizations.
- **Secure API**: JWT-based authentication for data integrity.
- **Data Analytics**: Real-time charts for Temperature, Humidity, and AQI trends.
- **Bulk Operations**: Seamless CSV upload and export functionality.
- **Deployment Ready**: Full Docker orchestration included.

## 🛠 Tech Stack
- **Frontend**: Tailwind CSS, Chart.js, Vanilla JavaScript.
- **Backend**: FastAPI (Python), PyJWT, Pydantic.
- **Database**: MySQL with Connection Pooling.

## 💻 Running in VS Code

Follow these steps to set up and run the project locally.

### Step 1: Environment Setup
1. Open the project folder in VS Code.
2. Open a new Terminal (**Ctrl+`**).
3. Create and activate a Virtual Environment:
   ```powershell
   # Create venv
   python -m venv venv
   
   # Activate venv
   .\venv\Scripts\activate
   ```
4. Install dependencies:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

### Step 2: Database Initialization
1. In the terminal (ensure venv is active and you are in the root directory), run:
   ```powershell
   python setup_db.py
   ```
   *This creates the `environment_db` and the default admin user.*
2. Ensure your `backend/.env` file has the correct MySQL `DB_PASSWORD`.

### Step 3: Start the Backend
1. Navigate to the backend folder:
   ```powershell
   cd backend
   ```
2. Launch the server:
   ```powershell
   uvicorn main:app --reload
   ```
3. Access the app: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🔒 Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

## 📁 Folder Structure
- `backend/`: FastAPI source code and API logic.
- `frontend/`: HTML/JS/CSS files for the user interface.
- `docs/`: API documentation and Postman collections.
- `setup_db.py`: Initialization script for MySQL.

---

## 🛠️ Troubleshooting

### Login Error: "Internal Server Error"
If you see an error in the logs mentioning `AttributeError: module 'bcrypt' has no attribute '__about__'`, this is a compatibility issue between `passlib` and newer versions of `bcrypt`.

**Fix**:
1. Activate your virtual environment.
2. Run:
   ```powershell
   pip install bcrypt==3.2.0
   ```
3. Restart the server (`uvicorn main:app --reload`).

---

## 🔄 Auto-Git Sync (Optional)

To automatically commit and push your changes to GitHub as you work, use the included PowerShell script.

### How to use:
1. Open a **new** terminal in VS Code.
2. Run the sync script:
   ```powershell
   .\git-sync.ps1
   ```
3. Keep this terminal open in the background. It will check for changes every 30 seconds and automatically sync them to your `main` branch.

**Note**: Press `Ctrl+C` in that terminal to stop the auto-sync at any time.
