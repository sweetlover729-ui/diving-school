"""
admin 公共模块 - 所有子模块共享的导入、依赖和 Schema 定义
v2: 精细化角色守卫
"""
import os
import re
import json
import logging
import io
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Body, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_, text as sql_text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from docx import Document

from app.core.database import AsyncSessionLocal, get_db
from app.core.config import settings
from app.core.textbook_utils import (
    get_class_textbooks, get_class_textbook_ids, get_class_textbook_pairs,
    assign_textbook_to_class, remove_textbook_from_class
)
from app.core.ai_interactive_converter import AIInteractiveConverter
from app.core.enhanced_converter import EnhancedAIConverter, TextbookEditor
from app.models.class_system import (
    User, Class, ClassMember, ClassTextbook, Textbook, Chapter, Company,
    UserRole, ClassStatus, TestType, QuestionType, TestStatus,
    SystemConfig, AlertRule, AlertRecord, AuditLog, LearningPath,
    ChapterProgress, TestResult
)
from app.api.auth_v2 import get_current_user

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
    description: Optional[str] = ""
    total_chapters: int = 0
    total_pages: int = 0
    is_active: bool = True


class ClassCreateRequest(BaseModel):
    name: str
    location: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "pending"
    textbooks: List[int] = []
    instructor_name: Optional[str] = None
    instructor_id_card: Optional[str] = None
    instructor_phone: Optional[str] = None
    instructor_password: Optional[str] = None
    company_id: Optional[int] = None
    province: str = ""
    city: str = ""
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    students: List[Dict] = []


class ClassUpdateRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    textbooks: Optional[List[int]] = None
    courses: Optional[List[Dict[str, Any]]] = None


class CompanyCreateRequest(BaseModel):
    name: str
    province: str = ""
    city: str = ""
    contact: str = ""
    phone: str = ""


class InstructorCreateRequest(BaseModel):
    name: str
    id_card: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    company_id: Optional[int] = None
    instructor_code: Optional[str] = None
    province: str = ""
    city: str = ""



class PeopleFilterRequest(BaseModel):
    role: str = "student"
    keyword: str = ""
    class_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20


class StudentImportRequest(BaseModel):
    students: List[Dict[str, Any]] = []


class InstructorPasswordResetRequest(BaseModel):
    password: str


class PersonCreateRequest(BaseModel):
    name: str
    role: str = "student"
    phone: str = ""
    id_card: Optional[str] = ""
    company_id: Optional[int] = None
    province: str = ""
    city: str = ""


class PersonPasswordResetRequest(BaseModel):
    password: str
