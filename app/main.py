from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.core.config import settings
from app.database import engine, Base
from app import models


from fastapi.staticfiles import StaticFiles


# Import all routers
from app.routes import (
    auth,
    users,
    organizations,
    projects,
    tasks,
    comments,
    memberships,
)
# -------------------------------------------------
# Create FastAPI instance
# -------------------------------------------------

app = FastAPI(
    title="TeamFlow API",
    version="1.0.0",
    description="Multi-tenant Project Management SaaS Backend",
)

# -------------------------------------------------
# Include Routers
# -------------------------------------------------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(memberships.router)


# -------------------------------------------------
# Root / Health Check Route
# -------------------------------------------------

@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# -------------------------------------------------
# Startup Event
# -------------------------------------------------

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# -------------------------------------------------
# Shutdown Event (Optional)
# -------------------------------------------------

@app.on_event("shutdown")
async def shutdown():
    """
    Runs when application stops.
    """
    print("Shutting down TeamFlow API...")