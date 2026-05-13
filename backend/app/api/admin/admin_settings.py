"""
管理员-系统设置 / 预警规则 / 审计日志
"""


from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.class_system import Question

from .shared import *

router = APIRouter(prefix="", tags=["管理员-系统设置"])

# ============================
# 系统配置 CRUD
# ============================

@router.get("/system-settings")
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """读取所有系统配置（键值对）"""
    result = await db.execute(select(SystemConfig))
    rows = result.scalars().all()
    return {r.key: r.value for r in rows}


@router.get("/settings")
async def get_settings_alias(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """系统设置（前端别名 → /system-settings）"""
    result = await db.execute(select(SystemConfig))
    rows = result.scalars().all()
    return {r.key: r.value for r in rows}


@router.put("/settings")
async def update_settings_alias(
    settings_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """更新系统设置（前端别名）"""
    for key, val in settings_data.items():
        str_val = "true" if val is True else "false" if val is False else str(val)
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = str_val
            existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.add(SystemConfig(key=key, value=str_val))
    await db.commit()
    return {"success": True}


@router.put("/system-settings")
async def update_system_settings(
    settings_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """更新系统配置（upsert）"""
    for key, val in settings_data.items():
        # 布尔值 Switch 返回 True/False
        str_val = "true" if val is True else "false" if val is False else str(val)
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = str_val
            existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.add(SystemConfig(key=key, value=str_val))
    await db.commit()
    return {"success": True}


# ============================
# 预警规则 CRUD
# ============================

@router.get("/alert-rules")
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """预警规则列表"""
    result = await db.execute(select(AlertRule).order_by(AlertRule.rule_type))
    rules = result.scalars().all()
    return [{
        "id": r.id, "name": r.name, "rule_type": r.rule_type,
        "threshold_value": r.threshold_value, "enabled": r.enabled,
        "notify_roles": r.notify_roles
    } for r in rules]


@router.post("/alert-rules")
async def create_alert_rule(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """创建预警规则"""
    rule = AlertRule(
        name=data.get("name", ""),
        rule_type=data.get("rule_type", ""),
        threshold_value=data.get("threshold_value", 0),
        enabled=data.get("enabled", True),
        notify_roles=data.get("notify_roles", "manager,instructor")
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"success": True, "id": rule.id}


@router.put("/alert-rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """更新预警规则"""
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    for field in ["name", "rule_type", "notify_roles"]:
        if field in data:
            setattr(rule, field, data[field])
    if "threshold_value" in data:
        rule.threshold_value = data["threshold_value"]
    if "enabled" in data:
        rule.enabled = data["enabled"]
    rule.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"success": True}


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """删除预警规则"""
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    await db.commit()
    return {"success": True}


# ============================
# 审计日志
# ============================

@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    user_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """审计日志列表（分页+筛选）"""
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if user_name:
        q = q.where(AuditLog.user_name.ilike(f"%{user_name}%"))

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()

    return {
        "total": total, "page": page, "page_size": page_size,
        "data": [{
            "id": l.id, "user_name": l.user_name, "user_role": l.user_role,
            "action": l.action, "target_type": l.target_type,
            "target_name": l.target_name, "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None
        } for l in logs]
    }


@router.get("/audit-logs/stats")
async def get_audit_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """审计统计：按操作类型汇总"""
    result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action)
    )
    return {"actions": [{"action": row[0], "count": row[1]} for row in result.all()]}


# ============================
# 管理后台仪表盘
# ============================

@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """管理后台仪表盘 - 聚合统计"""
    # 班级统计
    total_classes = (await db.execute(select(func.count()).select_from(Class))).scalar() or 0
    active_classes = (await db.execute(
        select(func.count()).select_from(Class).where(Class.status == ClassStatus.ACTIVE)
    )).scalar() or 0
    # 学员统计
    total_students = (await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.STUDENT, User.is_active == True)
    )).scalar() or 0
    enrolled_students = (await db.execute(
        select(func.count()).select_from(ClassMember).where(ClassMember.role == UserRole.STUDENT)
    )).scalar() or 0
    # 教材统计
    total_textbooks = (await db.execute(select(func.count()).select_from(Textbook))).scalar() or 0
    # 题目统计
    total_questions = (await db.execute(select(func.count()).select_from(Question))).scalar() or 0
    # 告警统计
    unread_alerts = (await db.execute(
        select(func.count()).select_from(AlertRecord).where(AlertRecord.is_read == False)
    )).scalar() or 0

    return {
        "classes": {"total": total_classes, "active": active_classes},
        "students": {"total": total_students, "enrolled": enrolled_students},
        "textbooks": total_textbooks,
        "questions": total_questions,
        "unread_alerts": unread_alerts
    }


# ============================
# 告警记录
# ============================

@router.get("/alert-records")
async def list_alert_records(
    class_id: int | None = Query(None),
    severity: str | None = Query(None),
    is_read: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """告警记录列表"""
    q = select(AlertRecord)
    if class_id:
        q = q.where(AlertRecord.class_id == class_id)
    if severity:
        q = q.where(AlertRecord.severity == severity)
    if is_read is not None:
        q = q.where(AlertRecord.is_read == is_read)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(AlertRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return {
        "total": total, "page": page, "page_size": page_size,
        "data": [{
            "id": r.id, "class_id": r.class_id,
            "rule_type": r.rule_type, "severity": r.severity,
            "message": r.message, "is_read": r.is_read,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in items]
    }


# ============================

