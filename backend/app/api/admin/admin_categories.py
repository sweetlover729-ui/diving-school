"""
管理员-培训类别管理 API
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_admin
from app.core.database import get_db
from app.models.class_system import Category

router = APIRouter(prefix="/categories", tags=["管理员-培训类别"])

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    icon: str | None = None
    sort_order: int | None = 0
    is_active: bool | None = True
    terminology_config: dict[str, Any] | None = None

class CategoryUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    terminology_config: dict[str, Any] | None = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    icon: str | None
    sort_order: int
    is_active: bool
    terminology_config: dict | None
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True

@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    stmt = select(Category)
    if not include_inactive:
        stmt = stmt.where(Category.is_active == True)
    stmt = stmt.order_by(Category.sort_order, Category.id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "icon": r.icon,
            "sort_order": r.sort_order,
            "is_active": r.is_active,
            "terminology_config": r.terminology_config,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return out

@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    existing = await db.execute(select(Category).where(Category.code == data.code))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="类别编码已存在")
    cat = Category(
        name=data.name,
        code=data.code,
        description=data.description,
        icon=data.icon,
        sort_order=data.sort_order or 0,
        is_active=data.is_active if data.is_active is not None else True,
        terminology_config=data.terminology_config or {},
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {
        "id": cat.id, "name": cat.name, "code": cat.code,
        "description": cat.description, "icon": cat.icon,
        "sort_order": cat.sort_order, "is_active": cat.is_active,
        "terminology_config": cat.terminology_config,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
    }

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")
    return {
        "id": cat.id, "name": cat.name, "code": cat.code,
        "description": cat.description, "icon": cat.icon,
        "sort_order": cat.sort_order, "is_active": cat.is_active,
        "terminology_config": cat.terminology_config,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
    }

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cat, key, value)
    cat.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(cat)
    return {
        "id": cat.id, "name": cat.name, "code": cat.code,
        "description": cat.description, "icon": cat.icon,
        "sort_order": cat.sort_order, "is_active": cat.is_active,
        "terminology_config": cat.terminology_config,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
    }

@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")
    await db.delete(cat)
    await db.commit()
    return {"success": True, "message": "类别已删除"}
