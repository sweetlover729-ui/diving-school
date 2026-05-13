"""
FastAPI 主应用 - 班级制培训管理系统
"""
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router

# 班级制API
from app.api.auth_v2 import router as auth_router
from app.api.courses import router as courses_router
from app.api.documents import admin_router as document_admin_router
from app.api.documents import student_router as document_student_router
from app.api.instructor import router as instructor_router
from app.api.instructor_progress import router as instructor_progress_router
from app.api.manager import router as manager_router
from app.api.student import router as student_router
from app.api.student_chapters import router as student_chapters_router
from app.api.textbook_import import router as textbook_import_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.errors import setup_error_handlers
from app.models.class_system import AuditLog

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"🚀 {settings.APP_NAME} v2.0 班级制系统启动中...")
    yield
    logger.info(f"👋 {settings.APP_NAME} 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="消防系统公共安全潜水班级制培训管理系统",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 注册全局异常处理器
setup_error_handlers(app)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 审计日志中间件
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """记录所有 API 操作到审计日志"""
    path = request.url.path
    method = request.method

    # 静态资源和健康检查不记录
    skip_prefixes = ["/static", "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    should_skip = any(path.startswith(p) for p in skip_prefixes)

    response: Response = await call_next(request)

    if not should_skip and method in ("POST", "PUT", "PATCH", "DELETE", "GET"):
        try:
            # 仅记录写操作和关键读操作
            audit_actions = {
                "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete",
                "GET": "view"
            }
            action = audit_actions.get(method, "unknown")

            # 从 path 推断 target_type
            path_parts = path.split("/")
            target_type = path_parts[3] if len(path_parts) > 3 else "unknown"

            # 获取用户信息（从 header 或 cookie）
            user_name = request.headers.get("x-user-name", "")
            user_role = request.headers.get("x-user-role", "")
            ip = request.client.host if request.client else ""

            async with AsyncSessionLocal() as session:
                log = AuditLog(
                    user_name=user_name or "anonymous",
                    user_role=user_role or "guest",
                    action=f"{action}_{target_type}",
                    target_type=target_type,
                    target_name=f"{method} {path}",
                    details=f"{method} {path}",
                    ip_address=ip
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning(f"审计日志写入失败: {e}", exc_info=True)

    return response

# 注册API路由
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(instructor_router, prefix="/api/v1")
app.include_router(manager_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")
app.include_router(student_chapters_router, prefix="/api/v1")
app.include_router(instructor_progress_router, prefix="/api/v1")
app.include_router(textbook_import_router, prefix="/api/v1")
app.include_router(document_student_router, prefix="/api/v1")
app.include_router(document_admin_router, prefix="/api/v1")
app.include_router(courses_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": "2.0.0 - 班级制",
        "status": "running",
        "docs": "/docs",
        "features": [
            "四级用户角色（管理员/教练/管理干部/学员）",
            "班级生命周期管理",
            "在线教材学习",
            "测验考试系统",
            "进度统计分析"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
