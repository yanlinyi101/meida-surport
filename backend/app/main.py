"""
FastAPI application with authentication, RBAC, and admin features.
"""
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from .core.config import settings
from .core.deps import get_current_active_user
from .db.base import Base, engine
from .api.auth import router as auth_router
from .api.admin import router as admin_router
from .api.appointments import router as appointments_router
from .api.tickets import router as tickets_router
from .api.files import router as files_router
from .models.user import User

# Import all models to ensure they are registered with SQLAlchemy
from .models import user, role, session, audit, ticket, technician, ticket_image

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="美大客服支持系统 - 管理后台API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(files_router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def user_home():
    """用户端首页"""
    with open("templates/user_home.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/booking", response_class=HTMLResponse)
async def booking_page():
    """用户端预约页面"""
    with open("templates/booking.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/admin", response_class=HTMLResponse)
async def admin_login():
    """管理后台登录页面"""
    with open("templates/admin_login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    current_user: User = Depends(get_current_active_user)
):
    """管理后台主页（需要登录）"""
    # 检查用户是否有管理权限
    if not current_user:
        return RedirectResponse(url="/admin", status_code=302)
    
    with open("templates/admin_home.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/admin/roles", response_class=HTMLResponse)
async def admin_roles(
    current_user: User = Depends(get_current_active_user)
):
    """角色管理页面（需要登录）"""
    if not current_user:
        return RedirectResponse(url="/admin", status_code=302)
    
    with open("templates/roles.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/admin/tickets", response_class=HTMLResponse)
async def admin_tickets(
    current_user: User = Depends(get_current_active_user)
):
    """工单管理页面（需要登录）"""
    if not current_user:
        return RedirectResponse(url="/admin", status_code=302)
    
    with open("templates/admin_tickets.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/admin/my-jobs", response_class=HTMLResponse)
async def technician_jobs(
    current_user: User = Depends(get_current_active_user)
):
    """技师端工单页面（需要登录）"""
    if not current_user:
        return RedirectResponse(url="/admin", status_code=302)
    
    with open("templates/technician_jobs.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/issues", response_class=HTMLResponse)
async def issues_redirect(
    current_user: User = Depends(get_current_active_user)
):
    """故障工单页面 - 重定向到工单管理（需要登录）"""
    if not current_user:
        return RedirectResponse(url="/admin", status_code=302)
    
    # 直接返回工单管理页面
    with open("templates/admin_tickets.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())



@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0",
        "features": {
            "authentication": True,
            "rbac": True,
            "audit_logs": True,
            "2fa": True,
            "password_reset": True
        }
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    print(f"🚀 {settings.app_name} started successfully!")
    print(f"📍 Environment: {'Production' if not settings.debug else 'Development'}")
    print(f"🔐 Authentication: Enabled")
    print(f"🛡️  RBAC: Enabled")
    print(f"📊 Audit Logs: Enabled")
    print(f"🔑 2FA: Available")
    print("💡 Run seed script to initialize default data: python -m backend.app.db.seed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    print("👋 Application shutting down...")


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return HTMLResponse(
        content="""
        <html>
        <head><title>404 - 页面未找到</title></head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>404 - 页面未找到</h1>
            <p>您访问的页面不存在</p>
            <a href="/" style="color: #007bff;">返回首页</a>
        </body>
        </html>
        """,
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return HTMLResponse(
        content="""
        <html>
        <head><title>500 - 服务器错误</title></head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>500 - 服务器内部错误</h1>
            <p>服务器遇到了一个错误，请稍后再试</p>
            <a href="/" style="color: #007bff;">返回首页</a>
        </body>
        </html>
        """,
        status_code=500
    )


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    ) 