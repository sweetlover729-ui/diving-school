"""
课程管理API - 潜水培训系统
提供独立的课程设置管理功能
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.admin.shared import require_admin
from app.api.auth_v2 import get_current_user
from app.core.database import get_db
from app.models.class_system import DocumentTemplate, User, UserRole

router = APIRouter(
    prefix="/admin/courses",
    tags=["课程管理"],
    dependencies=[Depends(require_admin)]
)


# ===== 请求模型 =====

class CourseCreateRequest(BaseModel):
    """创建课程请求"""
    code: str  # 课程代码，如 OW, AOW, RESCUE
    name: str  # 课程名称，如 开放水域潜水员
    description: str | None = None  # 课程描述
    level: str | None = "beginner"  # 级别: beginner/intermediate/advanced
    duration_days: int | None = None  # 培训天数
    max_depth: int | None = None  # 最大深度(米)
    is_active: bool = True


class CourseUpdateRequest(BaseModel):
    """更新课程请求"""
    code: str | None = None
    name: str | None = None
    description: str | None = None
    level: str | None = None
    duration_days: int | None = None
    max_depth: int | None = None
    is_active: bool | None = None


class CourseResponse(BaseModel):
    """课程响应模型"""
    id: str  # 使用code作为id
    code: str
    name: str
    description: str | None
    level: str
    duration_days: int | None
    max_depth: int | None
    is_active: bool
    created_at: str | None
    updated_at: str | None

    model_config = ConfigDict(from_attributes=True)


# ===== 工具函数 =====

async def get_course_template(db: AsyncSession) -> DocumentTemplate | None:
    """获取存储课程列表的文书模板（使用waiver类型的文书）"""
    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.doc_type == "waiver")
    )
    return result.scalar_one_or_none()


def parse_course_choices(template: DocumentTemplate | None) -> list[dict]:
    """从模板中解析课程列表"""
    if not template or not template.course_choices:
        return []
    return template.course_choices


def courses_to_choices(courses: list[dict]) -> list[dict]:
    """将课程列表转换为选项格式"""
    return [{"id": c["code"], "name": c["name"]} for c in courses if c.get("is_active", True)]


# ===== API路由 =====

@router.get("", response_model=list[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有课程列表"""
    template = await get_course_template(db)
    courses = parse_course_choices(template)

    # 添加时间戳字段（如果没有）
    for c in courses:
        if "created_at" not in c:
            c["created_at"] = None
        if "updated_at" not in c:
            c["updated_at"] = None

    return courses


@router.post("", response_model=CourseResponse)
async def create_course(
    request: CourseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新课程"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    if not template:
        raise HTTPException(status_code=404, detail="未找到文书模板，请先初始化系统")

    courses = parse_course_choices(template)

    # 检查code是否已存在
    if any(c["code"] == request.code for c in courses):
        raise HTTPException(status_code=400, detail=f"课程代码 {request.code} 已存在")

    # 创建新课程
    now = datetime.now(timezone.utc).isoformat()
    new_course = {
        "id": request.code,
        "code": request.code,
        "name": request.name,
        "description": request.description,
        "level": request.level or "beginner",
        "duration_days": request.duration_days,
        "max_depth": request.max_depth,
        "is_active": request.is_active,
        "created_at": now,
        "updated_at": now,
    }

    courses.append(new_course)

    # 更新模板
    template.course_choices = courses
    flag_modified(template, "course_choices")
    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return new_course


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个课程详情"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    courses = parse_course_choices(template)

    course = next((c for c in courses if c["code"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    return course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    request: CourseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新课程信息"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    if not template:
        raise HTTPException(status_code=404, detail="未找到文书模板")

    courses = parse_course_choices(template)

    # 查找课程
    course_index = next((i for i, c in enumerate(courses) if c["code"] == course_id), None)
    if course_index is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    # 如果要修改code，检查新code是否已存在
    if request.code and request.code != course_id:
        if any(c["code"] == request.code for c in courses):
            raise HTTPException(status_code=400, detail=f"课程代码 {request.code} 已存在")
        courses[course_index]["code"] = request.code
        courses[course_index]["id"] = request.code

    # 更新字段
    if request.name is not None:
        courses[course_index]["name"] = request.name
    if request.description is not None:
        courses[course_index]["description"] = request.description
    if request.level is not None:
        courses[course_index]["level"] = request.level
    if request.duration_days is not None:
        courses[course_index]["duration_days"] = request.duration_days
    if request.max_depth is not None:
        courses[course_index]["max_depth"] = request.max_depth
    if request.is_active is not None:
        courses[course_index]["is_active"] = request.is_active

    courses[course_index]["updated_at"] = datetime.now(timezone.utc).isoformat()

    # 保存
    template.course_choices = courses
    flag_modified(template, "course_choices")
    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return courses[course_index]


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除课程（软删除，标记为inactive）"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    if not template:
        raise HTTPException(status_code=404, detail="未找到文书模板")

    courses = parse_course_choices(template)

    # 查找并标记为inactive
    course = next((c for c in courses if c["code"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    course["is_active"] = False
    course["updated_at"] = datetime.now(timezone.utc).isoformat()

    template.course_choices = courses
    flag_modified(template, "course_choices")
    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return {"success": True, "message": "课程已停用"}


@router.post("/{course_id}/restore")
async def restore_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """恢复已停用的课程"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    if not template:
        raise HTTPException(status_code=404, detail="未找到文书模板")

    courses = parse_course_choices(template)

    course = next((c for c in courses if c["code"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    course["is_active"] = True
    course["updated_at"] = datetime.now(timezone.utc).isoformat()

    template.course_choices = courses
    flag_modified(template, "course_choices")
    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return {"success": True, "message": "课程已恢复"}


@router.post("/init-defaults")
async def init_default_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """初始化默认课程数据"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="无权访问")

    template = await get_course_template(db)
    if not template:
        raise HTTPException(status_code=404, detail="未找到文书模板，请先初始化系统")

    default_courses = [
        {
            "id": "OW",
            "code": "OW",
            "name": "开放水域潜水员 (Open Water)",
            "description": "入门级潜水课程，学习基础潜水技能和知识，最大深度18米",
            "level": "beginner",
            "duration_days": 3,
            "max_depth": 18,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "AOW",
            "code": "AOW",
            "name": "进阶开放水域潜水员 (Advanced Open Water)",
            "description": "进阶课程，包含深潜、导航等专项训练，最大深度30米",
            "level": "intermediate",
            "duration_days": 2,
            "max_depth": 30,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "RESCUE",
            "code": "RESCUE",
            "name": "救援潜水员 (Rescue Diver)",
            "description": "学习救援技巧和紧急情况处理，提升潜水安全意识",
            "level": "intermediate",
            "duration_days": 3,
            "max_depth": 30,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "DIVEMASTER",
            "code": "DIVEMASTER",
            "name": "潜水长 (Divemaster)",
            "description": "专业级课程，培养领导能力和专业潜水技能",
            "level": "advanced",
            "duration_days": 14,
            "max_depth": 40,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "EFR",
            "code": "EFR",
            "name": "紧急第一反应 (EFR)",
            "description": "急救和心肺复苏培训，救援潜水员的前提课程",
            "level": "beginner",
            "duration_days": 1,
            "max_depth": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "NITROX",
            "code": "NITROX",
            "name": "高氧空气潜水员 (Enriched Air Nitrox)",
            "description": "学习使用高氧空气进行潜水，延长水下停留时间",
            "level": "intermediate",
            "duration_days": 1,
            "max_depth": 40,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    # 合并现有课程和默认课程（避免重复）
    existing_codes = {c["code"] for c in template.course_choices or []}
    new_courses = [c for c in default_courses if c["code"] not in existing_codes]

    if template.course_choices:
        template.course_choices.extend(new_courses)
    else:
        template.course_choices = default_courses

    flag_modified(template, "course_choices")
    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return {
        "success": True,
        "message": f"已添加 {len(new_courses)} 门默认课程",
        "added": [c["code"] for c in new_courses],
        "skipped": list(existing_codes)
    }
