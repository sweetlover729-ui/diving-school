"""
API 响应格式化工具
"""
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone


class ApiResponse(BaseModel):
    """标准 API 响应"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
    timestamp: str = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class ApiError(BaseModel):
    """标准错误响应"""
    code: int = 400
    message: str = "error"
    detail: Optional[str] = None


def _now() -> datetime:
    """返回 naive UTC datetime，用于 DB 列和响应 timestamp"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": _now().isoformat()
    }


def error_response(code: int = 400, message: str = "error", detail: str = None) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "detail": detail,
        "timestamp": _now().isoformat()
    }


def paginated_response(items: list, total: int, page: int = 1, page_size: int = 20) -> dict:
    """分页响应"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        },
        "timestamp": _now().isoformat()
    }
