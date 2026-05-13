"""
API 文档和错误处理
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import copy
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _now() -> datetime:
    """返回 naive UTC datetime（DB TIMESTAMP WITHOUT TIME ZONE 兼容）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sanitize_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """递归清理验证错误中的不可序列化对象（如 ValueError 等），转为字符串"""
    sanitized = []
    for err in errors:
        err_copy = copy.deepcopy(err)
        if "ctx" in err_copy and isinstance(err_copy["ctx"], dict):
            for k, v in err_copy["ctx"].items():
                if isinstance(v, Exception):
                    err_copy["ctx"][k] = str(v)
        sanitized.append(err_copy)
    return sanitized


class APIException(Exception):
    """自定义 API 异常"""
    def __init__(self, status_code: int, message: str, detail: str = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail or message


def setup_error_handlers(app: FastAPI):
    """设置错误处理器"""
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """处理自定义 API 异常"""
        logger.error(f"API Error: {exc.message}", extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": exc.status_code,
                "message": exc.message,
                "detail": exc.detail,
                "timestamp": _now().isoformat(),
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理验证错误"""
        logger.warning(f"Validation Error: {exc.errors()}", extra={
            "path": request.url.path,
            "method": request.method,
        })
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "code": 422,
                "message": "请求数据验证失败",
                "errors": _sanitize_errors(exc.errors()),
                "timestamp": _now().isoformat(),
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.exception(f"Unhandled Exception: {str(exc)}", extra={
            "path": request.url.path,
            "method": request.method,
        })
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "服务器内部错误",
                "timestamp": _now().isoformat(),
            }
        )


def setup_logging():
    """设置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
