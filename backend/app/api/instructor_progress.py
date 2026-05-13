"""教练/管理干部 - 学员学习进度监控API"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_v2 import get_current_user
from app.core.database import get_db
from app.models.class_system import (
    User, ClassMember, ChapterProgress, ChapterProgressStatus, UserRole
)

router = APIRouter(prefix="/instructor/students", tags=["教练学员管理"])


async def get_instructor_class(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取教练所带班级（含角色校验）"""
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="需要教练员权限")
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == user.id,
            ClassMember.role == UserRole.INSTRUCTOR
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=400, detail="未分配班级")
    return member.class_id


# ============ 学员章节进度列表 ============

@router.get("/progress")
async def list_student_progress(
    class_id: int = Depends(get_instructor_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取班级所有学员的学习进度"""
    # 获取班级所有学员
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    members = result.scalars().all()
    
    students_data = []
    for member in members:
        # 获取用户信息
        student = await db.get(User, member.user_id)
        if not student:
            continue
        
        # 获取该学员所有章节进度
        result = await db.execute(
            select(ChapterProgress).where(
                ChapterProgress.user_id == member.user_id,
                ChapterProgress.class_id == class_id
            )
        )
        progress_list = result.scalars().all()
        
        # 统计
        completed = sum(1 for p in progress_list if p.status == ChapterProgressStatus.COMPLETED)
        reading_done = sum(1 for p in progress_list if p.status == ChapterProgressStatus.READING_DONE)
        practicing = sum(1 for p in progress_list if p.status == ChapterProgressStatus.PRACTICING)
        waiting_test = sum(1 for p in progress_list if p.status == ChapterProgressStatus.WAITING_TEST)
        total_time = sum(p.total_reading_time for p in progress_list)
        
        # 获取最近学习的章节
        recent_chapter = None
        if progress_list:
            recent = max(progress_list, key=lambda p: p.last_updated or p.created_at)
            recent_chapter_row = await db.execute(
                select(ChapterProgress).where(ChapterProgress.id == recent.id)
            )
            recent_chapter = recent_chapter_row.scalar_one_or_none()
        
        students_data.append({
            "user_id": student.id,
            "name": student.name,
            "progress": {
                "total": 72,
                "completed": completed,
                "reading_done": reading_done,
                "practicing": practicing,
                "waiting_test": waiting_test,
                "progress_percent": round(completed / 72 * 100, 1) if 72 else 0,
                "total_reading_time_minutes": round(total_time / 60, 1)
            },
            "last_active": max((p.last_updated for p in progress_list if p.last_updated), default=None)
        })
    
    return {
        "class_id": class_id,
        "students": students_data
    }


@router.get("/{user_id}/progress")
async def get_student_progress_detail(
    user_id: int,
    class_id: int = Depends(get_instructor_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取单个学员的详细学习进度"""
    # 获取学员信息
    student = await db.get(User, user_id)
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")
    
    # 获取该学员所有章节进度
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == user_id,
            ChapterProgress.class_id == class_id
        )
    )
    progress_list = result.scalars().all()
    progress_map = {p.chapter_id: p for p in progress_list}
    
    # 按章节整理
    from app.models.class_system import Chapter
    chapters_data = []
    
    # 获取6个大章
    result = await db.execute(
        select(Chapter).where(
            Chapter.textbook_id == 1,
            Chapter.parent_id.is_(None)
        ).order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()
    
    for ch in chapters:
        result = await db.execute(
            select(Chapter).where(Chapter.parent_id == ch.id).order_by(Chapter.sort_order)
        )
        sections = result.scalars().all()
        
        sections_data = []
        for sec in sections:
            p = progress_map.get(sec.id)
            sections_data.append({
                "id": sec.id,
                "title": sec.title,
                "status": p.status.value if p else "locked",
                "total_reading_time": p.total_reading_time if p else 0,
                "reading_done_at": p.reading_done_at.isoformat() if p and p.reading_done_at else None,
                "practice_done_at": p.practice_done_at.isoformat() if p and p.practice_done_at else None,
                "completed_at": p.completed_at.isoformat() if p and p.completed_at else None
            })
        
        chapters_data.append({
            "id": ch.id,
            "title": ch.title,
            "sections": sections_data
        })
    
    # 汇总
    total_sections = 72
    completed = sum(1 for p in progress_list if p.status == ChapterProgressStatus.COMPLETED)
    total_time = sum(p.total_reading_time for p in progress_list)
    
    return {
        "user_id": student.id,
        "name": student.name,
        "chapters": chapters_data,
        "summary": {
            "total_sections": total_sections,
            "completed": completed,
            "progress_percent": round(completed / total_sections * 100, 1) if total_sections else 0,
            "total_reading_time_minutes": round(total_time / 60, 1)
        }
    }


# ============ 待发布测验提醒 ============

@router.get("/pending-tests")
async def get_pending_tests(
    class_id: int = Depends(get_instructor_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取等待发布随堂测验的学员列表"""
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.class_id == class_id,
            ChapterProgress.status == ChapterProgressStatus.WAITING_TEST
        )
    )
    pending_list = result.scalars().all()
    
    from app.models.class_system import Chapter
    notifications = []
    for p in pending_list:
        student = await db.get(User, p.user_id)
        chapter = await db.get(Chapter, p.chapter_id)
        if student and chapter:
            notifications.append({
                "user_id": student.id,
                "student_name": student.name,
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "completed_at": p.practice_done_at.isoformat() if p.practice_done_at else None
            })
    
    return {"pending_tests": notifications}


# ============ 成绩汇总 ============

@router.get("/scores")
async def get_class_scores(
    class_id: int = Depends(get_instructor_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取班级所有测验成绩"""
    from app.models.class_system import Test, TestResult
    
    # 获取班级所有测验
    result = await db.execute(
        select(Test).where(Test.class_id == class_id)
    )
    tests = result.scalars().all()
    
    # 获取所有测验结果
    all_results = []
    pass_count = 0
    total_score = 0
    total_tests = 0
    
    for test in tests:
        result = await db.execute(
            select(TestResult).where(TestResult.test_id == test.id)
        )
        test_results = result.scalars().all()
        
        for tr in test_results:
            student = await db.get(User, tr.user_id)
            if student:
                all_results.append({
                    "id": tr.id,
                    "student_name": student.name,
                    "test_title": test.title,
                    "test_type": test.test_type,
                    "score": tr.score,
                    "total_score": test.total_score,
                    "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None,
                })
                total_score += tr.score
                total_tests += 1
                if tr.score >= 60:
                    pass_count += 1
    
    return {
        "results": all_results,
        "stats": {
            "total_tests": total_tests,
            "avg_score": round(total_score / total_tests, 1) if total_tests > 0 else 0,
            "pass_count": pass_count,
            "fail_count": total_tests - pass_count,
        }
    }


# ============ 统计分析 ============

@router.get("/analytics/overview")
async def get_analytics_overview(
    class_id: int = Depends(get_instructor_class),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取班级统计分析数据"""
    from app.models.class_system import Test, TestResult, Chapter, Class
    from datetime import datetime
    
    # 获取班级学员
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    members = result.scalars().all()
    student_count = len(members)
    
    # 获取班级信息
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    
    # 计算剩余天数
    remaining_days = 0
    if cls and cls.end_time:
        remaining_days = max(0, (cls.end_time - datetime.now(timezone.utc).replace(tzinfo=None)).days)
    
    # 获取所有章节进度
    result = await db.execute(
        select(ChapterProgress).where(ChapterProgress.class_id == class_id)
    )
    all_progress = result.scalars().all()
    
    # 计算平均阅读进度
    total_reading_time = sum(p.total_reading_time or 0 for p in all_progress)
    completed_count = sum(1 for p in all_progress if p.status == ChapterProgressStatus.COMPLETED)
    avg_reading_progress = round((completed_count / len(all_progress) * 100), 1) if all_progress else 0
    
    # 获取所有测验成绩
    result = await db.execute(
        select(Test).where(Test.class_id == class_id)
    )
    tests = result.scalars().all()
    test_count = len(tests)
    
    # 计算平均成绩
    total_score = 0
    score_count = 0
    for test in tests:
        result = await db.execute(
            select(TestResult).where(TestResult.test_id == test.id)
        )
        test_results = result.scalars().all()
        for tr in test_results:
            total_score += tr.score
            score_count += 1
    avg_score = round(total_score / score_count, 1) if score_count > 0 else 0
    
    # 章节统计（通过班级关联的教材获取章节）
    from app.models.class_system import ClassTextbook
    result = await db.execute(
        select(ClassTextbook.textbook_id).where(ClassTextbook.class_id == class_id)
    )
    textbook_ids = [r[0] for r in result.fetchall()]
    
    if not textbook_ids:
        chapters = []
    else:
        result = await db.execute(
            select(Chapter).where(Chapter.textbook_id.in_(textbook_ids))
        )
        chapters = result.scalars().all()
    
    chapter_stats = []
    for chapter in chapters:
        result = await db.execute(
            select(ChapterProgress).where(
                ChapterProgress.chapter_id == chapter.id,
                ChapterProgress.class_id == class_id
            )
        )
        chapter_progress = result.scalars().all()
        if chapter_progress:
            completed = sum(1 for p in chapter_progress if p.status == ChapterProgressStatus.COMPLETED)
            rate = round((completed / len(chapter_progress)) * 100, 1)
            chapter_stats.append({
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "completion_rate": rate,
                "avg_score": 0,
            })
    
    return {
        "student_count": student_count,
        "avg_score": avg_score,
        "avg_reading_progress": avg_reading_progress,
        "total_reading_time": total_reading_time,
        "test_count": test_count,
        "remaining_days": remaining_days,
        "chapter_stats": chapter_stats,
    }