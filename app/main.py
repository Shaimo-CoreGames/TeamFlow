from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.database import engine, Base
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
app = FastAPI(
    title="TeamFlow API",
    version="1.0.0",
    description="Multi-tenant Project Management SaaS Backend",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(memberships.router)

@app.get("/")
async def read_index():
    return FileResponse("app/static/index.html")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def on_startup():
    try:
        async with engine.begin() as conn:
            # Check if we can actually connect
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables synced successfully.")
    except Exception as e:
        print(f"❌ Database startup error: {e}")

@app.on_event("shutdown")
async def shutdown():
    """
    Runs when application stops.
    """
    print("Shutting down TeamFlow API...")