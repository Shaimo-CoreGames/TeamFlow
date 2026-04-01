# 🚀 TeamFlow | Full-Stack Project Management Suite

TeamFlow is a high-performance, asynchronous project management tool designed to streamline team collaboration. Built with a focus on security, scalability, and clean API architecture, it allows users to manage workspaces, track project milestones, and coordinate tasks in real-time.

**🌐 Live Demo:** [https://team-flow-6tu1.onrender.com/]

---

## 🛠️ Technical Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+) - Asynchronous API framework.
- **Database:** [SQLAlchemy](https://www.sqlalchemy.org/) with **AioSQLite** for async database operations.
- **Security:** OAuth2 with Password Flow, **JWT (JSON Web Tokens)**, and **Bcrypt** password hashing.
- **DevOps:** [Docker](https://www.docker.com/) & Docker Compose for containerization.
- **Frontend:** Vanilla JavaScript, HTML5, and CSS3 (Responsive Design.
- **Deployment:** Render (Backend Dockerized).

---

## ✨ Key Features

- **Secure Authentication:** Robust login/signup flow using JWT-based session management.
- **Workspace Orchestration:** Create and manage multiple organizations and team environments.
- **Task Management:** CRUD operations for projects and tasks with real-time status tracking.
- **Member Access Control:** Logic-driven member assignment to specific projects.
- **Containerized Architecture:** Fully Dockerized environment for "plug-and-play" development.

---

## 🚀 Getting Started

### 1. Prerequisites
- Docker & Docker Desktop
- Python 3.11 (if running without Docker)

### 2. Environment Variables
Create a `.env` file in the root directory and add the following:
```env
DATABASE_URL=sqlite+aiosqlite:///./teamflow.db
JWT_SECRET_KEY=your_super_long_random_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```
### 3. Running with Docker
Bash
# Build the image
  ```
docker build -t teamflow .
```

# Run the container
  ```docker run -p 8000:10000 --env-file .env teamflow```
- The application will be available at http://localhost:8000.

📸 Screenshots
Login:
<img width="960" height="413" alt="image" src="https://github.com/user-attachments/assets/213e8197-9174-4e5c-906a-097aaeaf1ad2" />
PageDashboard:
<img width="1920" height="838" alt="image" src="https://github.com/user-attachments/assets/7532f9cf-76f2-40ad-bff8-1427657ffffb" />

🤝 Contact & Support
- Project Maintainer: [SHAH MEER]
- LinkedIn: [https://www.linkedin.com/in/shah-meer-3642233b2]
- GitHub: [https://github.com/Shaimo-CoreGames]
