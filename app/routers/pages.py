from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

PROJECT_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(PROJECT_DIR / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/health")
def health():
    return {"status": "ok"}
