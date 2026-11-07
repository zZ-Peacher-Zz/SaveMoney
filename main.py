"""Application entry point: uvicorn main:app --reload."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import auth, avatars, expenses, groups, months, pages

PROJECT_DIR = Path(__file__).resolve().parent

init_db()
app = FastAPI(title="Monthly Expense Tracker", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(PROJECT_DIR / "static")), name="static")

for module in (pages, auth, avatars, groups, months, expenses):
    app.include_router(module.router)
