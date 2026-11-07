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


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "page": "login", "title": "Đăng nhập"})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "page": "register", "title": "Tạo tài khoản"})


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "page": "forgot-password", "title": "Quên mật khẩu"})


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    return templates.TemplateResponse("recovery.html", {"request": request, "verify": False})


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(request: Request):
    return templates.TemplateResponse("recovery.html", {"request": request, "verify": True})
