from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import current_user

PROJECT_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(PROJECT_DIR / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    try:
        current_user(request, db)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return RedirectResponse("/login", status_code=303, headers={"Cache-Control": "no-store"})
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/health")
def health():
    return {"status": "ok"}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "page": "login", "title": "Đăng nhập"})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "page": "register", "title": "Tạo tài khoản"})
