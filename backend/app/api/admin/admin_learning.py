"""
管理员-学习路径 / 跨班对比
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.class_system import (
    ChapterProgress,
    ChapterProgressStatus,
    Class,
    ClassMember,
    LearningPath,
    TestResult,
    User,
    UserRole,
)

from .shared import *

router = APIRouter(prefix="", tags=["管理员-学习路径与对比"])


# ============================
# 学习路径
# ============================

@router.get("/learning-paths")
async def list_learning_paths(
    class_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """学习路径列表"""
    q = select(LearningPath)
    if class_id:
        q = q.where(LearningPath.class_id == class_id)
    q = q.order_by(LearningPath.created_at.desc())
    result = await db.execute(q)
    items = result.scalars().all()
    return {
        "data": [{
            "id": lp.id, "class_id": lp.class_id, "user_id": lp.user_id,
            "path_type": lp.path_type, "assigned_reason": lp.assigned_reason,
            "current_stage": lp.current_stage,
            "fast_track_skipped": lp.fast_track_skipped,
            "created_at": lp.created_at.isoformat() if lp.created_at else None,
            "updated_at": lp.updated_at.isoformat() if lp.updated_at else None
        } for lp in items]
    }


# ============================
# 跨班对比
# ============================

@router.get("/comparison")
async def cross_class_comparison(
    class_ids: str | None = Query(None, description="逗号分隔的班级ID列表"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """跨班级对比分析"""
    ids = []
    if class_ids:
        ids = [int(x.strip()) for x in class_ids.split(",") if x.strip().isdigit()]
    else:
        result = await db.execute(
            select(Class).where(
                Class.status.in_([ClassStatus.ACTIVE])
            ).order_by(Class.created_at.desc()).limit(5)
        )
        ids = [c.id for c in result.scalars().all()]

    comparison = []
    for cid in ids:
        cls_obj = await db.get(Class, cid)
        if not cls_obj:
            continue

        # 学员数
        student_count_result = await db.execute(
            select(func.count()).select_from(ClassMember).where(
                ClassMember.class_id == cid, ClassMember.role == UserRole.STUDENT
            )
        )
        student_count = student_count_result.scalar() or 0

        # 章节完成率
        total_cp = (await db.execute(
            select(func.count()).where(ChapterProgress.class_id == cid)
        )).scalar() or 0
        completed_cp = (await db.execute(
            select(func.count()).where(
                ChapterProgress.class_id == cid,
                ChapterProgress.status == ChapterProgressStatus.COMPLETED
            )
        )).scalar() or 0
        completion_rate = round(completed_cp / total_cp * 100, 1) if total_cp > 0 else 0

        # 平均成绩 - TestResult 没有 class_id，通过 user_id in class 来算
        student_ids_subq = select(ClassMember.user_id).where(
            ClassMember.class_id == cid, ClassMember.role == UserRole.STUDENT
        ).subquery()
        avg_score_result = await db.execute(
            select(func.avg(TestResult.score)).where(
                TestResult.user_id.in_(student_ids_subq),
                TestResult.score > 0
            )
        )
        avg_score = avg_score_result.scalar()

        # 切标签总次数
        tab_switches = (await db.execute(
            select(func.sum(ChapterProgress.tab_switch_count)).where(ChapterProgress.class_id == cid)
        )).scalar() or 0

        status_val = cls_obj.status.value if hasattr(cls_obj.status, 'value') else str(cls_obj.status)

        comparison.append({
            "class_id": cid,
            "class_name": cls_obj.name,
            "status": status_val,
            "student_count": student_count,
            "completion_rate": completion_rate,
            "avg_score": round(float(avg_score), 1) if avg_score else 0,
            "tab_switches": tab_switches
        })

    return {"data": comparison}
