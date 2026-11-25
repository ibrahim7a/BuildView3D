# BuildView 3D

> **See Your Home Before It's Built**

An AI-powered platform that transforms 2D floor plans into interactive 3D house models. Upload a floor plan, and within minutes our AI builds a fully explorable 3D model you can walk through, customise, and share with anyone.

---

## 🏗️ What is BuildView 3D?

BuildView 3D is a web-based SaaS platform for builders, architects, and homeowners. It reads a 2D architectural floor plan and automatically generates a 3D model that can be explored in a browser or on Meta Quest VR.

**Key features:**
- 📐 AI-powered floor plan analysis (rooms, walls, doors, windows)
- 🏠 Automatic 3D model generation (2.7m ceiling height, metric dimensions)
- 🚶 Interactive virtual walkthrough
- 🎨 Interior customisation (walls, floors, furniture)
- 🔗 Public share links (no login required to view)
- 📱 Works on desktop, mobile, and Meta Quest VR

---

## 🛠️ Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.11+, FastAPI, SQLAlchemy, SQLite     |
| Auth        | JWT (python-jose), bcrypt (passlib)           |
| Frontend    | HTML5, CSS3, JavaScript (ES6+), Tailwind CSS  |
| 3D Viewer   | Three.js (Phase 2)                            |
| AI/ML       | Pillow, custom floor plan parser (Phase 2+)   |
| VR          | WebXR + Meta Quest (Phase 3)                  |

---

## 📁 Project Structure

```
D:\BuildView3D\
├── backend\                   ← Python FastAPI backend
│   ├── app\
│   │   ├── main.py            ← App entry point
│   │   ├── config.py          ← Settings (from .env)
│   │   ├── database.py        ← SQLAlchemy setup
│   │   ├── models\            ← Database models (User, Project)
│   │   ├── schemas\           ← Pydantic request/response schemas
│   │   ├── routers\           ← API route handlers
│   │   └── services\          ← Business logic (auth, etc.)
│   ├── uploads\               ← User-uploaded floor plans
│   ├── outputs\               ← Generated 3D model files
│   ├── temp\                  ← Temporary processing files
│   ├── requirements.txt       ← Python dependencies
│   └── .env                   ← Environment variables (keep secret!)
├── frontend\                  ← HTML/CSS/JS frontend
│   ├── index.html             ← Landing page
│   ├── login.html             ← Login page
│   ├── register.html          ← Registration page
│   ├── dashboard.html         ← User dashboard
│   ├── css\                   ← Stylesheets
│   └── js\                    ← JavaScript files
├── .gitignore
├── README.md
└── start.bat                  ← Windows startup script
```

---

## ⚙️ Installation (Windows)

### Prerequisites

Before starting, make sure you have installed:

1. **Python 3.11 or newer** — Download from [python.org](https://www.python.org/downloads/)
   - During installation, tick **"Add Python to PATH"**
2. **Git** (optional, for cloning) — [git-scm.com](https://git-scm.com/)

### Step-by-Step Setup

**Step 1: Get the project files**

If you have Git:
```bash
git clone <your-repo-url> D:\BuildView3D
```

Or simply copy the `D:\BuildView3D` folder to your machine.

**Step 2: Open Command Prompt or PowerShell**

Press `Win + R`, type `cmd`, press Enter.

**Step 3: Create a Python virtual environment**

```cmd
cd D:\BuildView3D\backend
python -m venv venv
```

**Step 4: Activate the virtual environment**

```cmd
venv\Scripts\activate
```

You should see `(venv)` at the start of your command prompt.

**Step 5: Install dependencies**

```cmd
pip install -r requirements.txt
```

This may take 2–5 minutes the first time.

**Step 6: Configure the environment**

The `.env` file is already set up with development defaults. For production, change `SECRET_KEY` to a long random string.

---

## 🚀 Running the Project

### Option A: Double-click start.bat

Navigate to `D:\BuildView3D\` and double-click `start.bat`.

This automatically:
1. Creates the virtual environment (if needed)
2. Installs all dependencies
3. Starts the backend server
4. Opens the browser

### Option B: Manual start

```cmd
cd D:\BuildView3D\backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 Accessing the Application

Once the server is running:

| Page             | URL                                              |
|------------------|--------------------------------------------------|
| **Landing page** | http://localhost:8000/app/index.html             |
| **Register**     | http://localhost:8000/app/register.html          |
| **Login**        | http://localhost:8000/app/login.html             |
| **Dashboard**    | http://localhost:8000/app/dashboard.html         |
| **API Docs**     | http://localhost:8000/docs                       |
| **API Root**     | http://localhost:8000/                           |
| **Health Check** | http://localhost:8000/health                     |

---

## 📡 API Documentation

The interactive API documentation is auto-generated by FastAPI.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint                   | Description                         | Auth Required |
|--------|----------------------------|-------------------------------------|---------------|
| POST   | `/api/v1/auth/register`    | Create a new account                | No            |
| POST   | `/api/v1/auth/login`       | Log in and get a token              | No            |
| GET    | `/api/v1/auth/me`          | Get current user info               | Yes (Bearer)  |
| GET    | `/health`                  | API health check                    | No            |

---

## 🔧 Configuration

Edit `backend/.env` to change settings:

```env
# Secret key for JWT signing — change this in production!
SECRET_KEY=your-very-long-random-secret-key-here

# JWT algorithm (don't change unless you know what you're doing)
ALGORITHM=HS256

# How long login tokens last (in minutes). 10080 = 7 days
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Database URL — SQLite file stored in backend/
DATABASE_URL=sqlite:///./buildview3d.db
```

---

## 🗺️ Development Roadmap

| Phase | Features                                                        | Status       |
|-------|-----------------------------------------------------------------|--------------|
| **1** | Project setup, auth, landing page, dashboard                    | ✅ Complete  |
| **2** | Floor plan upload, file management, project CRUD API            | 🔜 Next      |
| **3** | AI floor plan analysis, wall/room detection, scale calculation  | 📋 Planned   |
| **4** | 3D model generation with Three.js                               | 📋 Planned   |
| **5** | Interior customisation (walls, floors, furniture)               | 📋 Planned   |
| **6** | Public share links, VR support (Meta Quest WebXR)               | 📋 Planned   |

---

## 🛡️ Security Notes

- Passwords are hashed with **bcrypt** (industry standard)
- JWT tokens expire after **7 days** by default
- Change `SECRET_KEY` in production to a long random string
- CORS is set to `allow_origins=["*"]` for development only — restrict this in production

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

## 🤝 Contributing

This project is under active development. Contributions welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

*Built with ❤️ for builders and homeowners. See your home before it's built.*
