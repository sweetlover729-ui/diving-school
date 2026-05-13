"""
admin 公共模块 - 所有子模块共享的导入、依赖和 Schema 定义
v2: 精细化角色守卫
"""
import logging
from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from app.api.auth_v2 import get_current_user
from app.core.database import AsyncSessionLocal
from app.models.class_system import User, UserRole

logger = logging.getLogger(__name__)

# ============================
# 工具函数
# ============================

def serialize_datetime(dt):
    """序列化 datetime 为 ISO 格式字符串"""
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except (AttributeError, TypeError):
        return str(dt)

# ============================
# 依赖项 — 精细化角色守卫
# ============================

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


async def require_superadmin(user: User = Depends(get_current_user)):
    """
    超级管理员专属 — 仅 ADMIN 角色
    用于：系统设置、审计日志、用户角色变更、数据库级操作
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return user


async def require_admin(user: User = Depends(get_current_user)):
    """
    管理员权限 — ADMIN 独享
    用于：班级管理、教材管理、题库管理、学员管理、系统设置
    注意：MANAGER（管理干部）不可访问，需用 /manager/ 端点
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


async def require_manager(user: User = Depends(get_current_user)):
    """
    管理干部权限 — MANAGER + ADMIN
    用于：审计日志查询、跨班分析、预警管理
    """
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="需要管理员或管理干部权限")
    return user


async def require_instructor(user: User = Depends(get_current_user)):
    """
    教练员专属 — 仅 INSTRUCTOR 角色
    用于：创建测验、批改作业、生成报告
    """
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="需要教练员权限")
    return user


async def require_student(user: User = Depends(get_current_user)):
    """
    学员专属 — 仅 STUDENT 角色
    用于：学习进度、提交作业、参加考试
    """
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="需要学员权限")
    return user


async def require_staff(user: User = Depends(get_current_user)):
    """
    教职工权限 — ADMIN + MANAGER + INSTRUCTOR
    用于：预览学生界面、查看公共报表
    """
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.INSTRUCTOR]:
        raise HTTPException(status_code=403, detail="需要教职工权限")
    return user


async def require_authenticated(user: User = Depends(get_current_user)):
    """
    已认证用户 — 所有角色
    用于：仅需登录但不需要特定角色的端点
    """
    return user


# ============================
# Pydantic Schemas
# ============================

class TextbookCreate(BaseModel):
    name: str
    description: str | None = ""
    total_chapters: int = 0
    total_pages: int = 0
    is_active: bool = True


class ClassCreateRequest(BaseModel):
    name: str
    location: str = ""
    start_time: str | None = None
    end_time: str | None = None
    status: str = "pending"
    textbooks: list[int] = []
    instructor_name: str | None = None
    instructor_id_card: str | None = None
    instructor_phone: str | None = None
    instructor_password: str | None = None
    company_id: int | None = None
    province: str = ""
    city: str = ""
    manager_name: str | None = None
    manager_phone: str | None = None
    students: list[dict] = []


class ClassUpdateRequest(BaseModel):
    name: str | None = None
    location: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    textbooks: list[int] | None = None
    courses: list[dict[str, Any]] | None = None


class CompanyCreateRequest(BaseModel):
    name: str
    province: str = ""
    city: str = ""
    contact: str = ""
    phone: str = ""


class InstructorCreateRequest(BaseModel):
    name: str
    id_card: str | None = None
    phone: str | None = None
    password: str | None = None
    company_id: int | None = None
    instructor_code: str | None = None
    province: str = ""
    city: str = ""



class PeopleFilterRequest(BaseModel):
    role: str = "student"
    keyword: str = ""
    class_id: int | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20


class StudentImportRequest(BaseModel):
    students: list[dict[str, Any]] = []


class InstructorPasswordResetRequest(BaseModel):
    password: str


class PersonCreateRequest(BaseModel):
    name: str
    role: str = "student"
    phone: str = ""
    id_card: str | None = ""
    company_id: int | None = None
    province: str = ""
    city: str = ""


class PersonPasswordResetRequest(BaseModel):
    password: str
