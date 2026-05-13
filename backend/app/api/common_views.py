"""
教练员/管理干部共享视图函数 - 消除90%代码重复

两个角色共享的核心查询逻辑提取到此模块，各自的路由文件只做薄包装。
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException

from app.models.class_system import (
    User, Class, ClassMember, Test, TestResult, Textbook,
    ReadingProgress, UserRole, ClassStatus, TestStatus, TestType
)
from app.api.auth_v2 import get_current_user, get_current_class


# ═══════════════════════════════════════════════════════════════
# 班级信息
# ═══════════════════════════════════════════════════════════════

async def get_class_info(cls: Class) -> dict:
    """获取班级基本信息"""
    return {
        "id": cls.id,
        "name": cls.name,
        "location": cls.location,
        "start_time": cls.start_time.isoformat(),
        "end_time": cls.end_time.isoformat(),
        "status": cls.status.value,
        "textbook_ids": cls.get_textbook_ids()
    }


# ═══════════════════════════════════════════════════════════════
# 学员列表
# ═══════════════════════════════════════════════════════════════

async def get_students_list(
    db: AsyncSession,
    cls: Class,
    include_progress: bool = False
) -> List[dict]:
    """获取班级学员列表
    
    Args:
        include_progress: True=管理干部视图(含阅读进度), False=教练视图
    """
    result = await db.execute(
        select(ClassMember, User)
        .join(User, User.id == ClassMember.user_id, isouter=True)
        .where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    rows = result.all()
    
    students = []
    for member, u in rows:
        student = {
            "id": member.id,
            "user_id": member.user_id,
            "name": u.name if u else f"学员{member.user_id}",
            "id_card": u.id_card if u else "-",
            "phone": u.phone if u else "-",
            "joined_at": member.joined_at.isoformat() if member.joined_at else None
        }
        
        if include_progress:
            result = await db.execute(
                select(ReadingProgress).where(ReadingProgress.user_id == member.user_id)
            )
            readings = result.scalars().all()
            student["reading_progress"] = round(
                sum(r.progress for r in readings) / len(readings) if readings else 0, 1
            )
        
        students.append(student)
    
    return students


# ═══════════════════════════════════════════════════════════════
# 进度概览
# ═══════════════════════════════════════════════════════════════

async def get_progress_overview(
    db: AsyncSession,
    cls: Class
) -> List[dict]:
    """获取班级全体学员进度概览"""
    result = await db.execute(
        select(ClassMember, User)
        .join(User)
        .where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    students = result.all()
    
    # 预取所有测验
    result = await db.execute(
        select(Test).where(Test.class_id == cls.id, Test.status == TestStatus.PUBLISHED)
    )
    all_tests = result.scalars().all()
    total_tests = len(all_tests)
    
    progress_data = []
    for member, u in students:
        uid = member.user_id
        
        # 阅读进度
        result = await db.execute(
            select(ReadingProgress).where(ReadingProgress.user_id == uid)
        )
        readings = result.scalars().all()
        avg_progress = sum(r.progress for r in readings) / len(readings) if readings else 0
        
        # 测验完成情况
        result = await db.execute(
            select(TestResult).where(TestResult.user_id == uid)
        )
        completed = result.scalars().all()
        avg_score = sum(r.score for r in completed) / len(completed) if completed else 0
        
        progress_data.append({
            "user_id": uid,
            "name": u.name,
            "reading_progress": round(avg_progress, 1),
            "tests_completed": len(completed),
            "tests_total": total_tests,
            "avg_score": round(avg_score, 1)
        })
    
    return progress_data


# ═══════════════════════════════════════════════════════════════
# 成绩汇总表
# ═══════════════════════════════════════════════════════════════

async def get_scores_matrix(
    db: AsyncSession,
    cls: Class
) -> dict:
    """获取班级成绩矩阵表"""
    result = await db.execute(
        select(Test).where(Test.class_id == cls.id)
    )
    tests = result.scalars().all()
    
    result = await db.execute(
        select(ClassMember, User)
        .join(User)
        .where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    students = result.all()
    
    scores_table = []
    for member, u in students:
        row = {"name": u.name, "user_id": u.id}
        for test in tests:
            result = await db.execute(
                select(TestResult).where(
                    TestResult.test_id == test.id,
                    TestResult.user_id == u.id
                )
            )
            tr = result.scalar_one_or_none()
            row[f"test_{test.id}"] = tr.score if tr else None
        scores_table.append(row)
    
    return {
        "tests": [
            {"id": t.id, "title": t.title, "total_score": t.total_score}
            for t in tests
        ],
        "scores": scores_table
    }


# ═══════════════════════════════════════════════════════════════
# 单次测验成绩
# ═══════════════════════════════════════════════════════════════

async def get_single_test_scores(
    test_id: int,
    db: AsyncSession,
    cls: Class
) -> dict:
    """获取单次测验成绩详情"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")
    
    result = await db.execute(
        select(TestResult, User)
        .join(User)
        .where(TestResult.test_id == test_id)
    )
    results = result.all()
    
    return {
        "test": {
            "id": test.id,
            "title": test.title,
            "total_score": test.total_score,
            "question_count": len(test.get_question_ids())
        },
        "results": [
            {
                "user_id": u.id,
                "name": u.name,
                "score": tr.score,
                "time_spent": tr.time_spent,
                "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None
            }
            for tr, u in results
        ]
    }


# ═══════════════════════════════════════════════════════════════
# 班级统计概览
# ═══════════════════════════════════════════════════════════════

async def get_analytics_summary(
    db: AsyncSession,
    cls: Class
) -> dict:
    """获取班级统计分析概览"""
    # 学员数
    result = await db.execute(
        select(func.count()).select_from(ClassMember).where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    student_count = result.scalar()
    
    # 测验数
    result = await db.execute(
        select(func.count()).select_from(Test).where(Test.class_id == cls.id)
    )
    test_count = result.scalar()
    
    # 平均成绩
    result = await db.execute(
        select(TestResult).join(Test).where(Test.class_id == cls.id)
    )
    all_results = result.scalars().all()
    avg_score = sum(r.score for r in all_results if r.score) / len(all_results) if all_results else 0
    
    # 平均阅读进度
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    members = result.scalars().all()
    
    total_progress = 0.0
    for m in members:
        result = await db.execute(
            select(ReadingProgress).where(ReadingProgress.user_id == m.user_id)
        )
        readings = result.scalars().all()
        if readings:
            total_progress += sum(r.progress for r in readings) / len(readings)
    
    avg_reading = total_progress / student_count if student_count > 0 else 0
    
    # 计算剩余天数
    remaining_days = 0
    if cls.end_time:
        remaining_days = max(0, (cls.end_time.replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)).days)
    
    # 通过率
    pass_count = sum(1 for r in all_results if r.score and r.score >= 60)
    pass_rate = round(pass_count / len(all_results) * 100, 1) if all_results else 0
    
    return {
        "class_name": cls.name,
        "student_count": student_count,
        "test_count": test_count,
        "avg_score": round(avg_score, 1),
        "avg_reading_progress": round(avg_reading, 1),
        "pass_rate": pass_rate,
        "class_status": cls.status.value,
        "remaining_days": remaining_days
    }


# ═══════════════════════════════════════════════════════════════
# 阅读统计排行
# ═══════════════════════════════════════════════════════════════

async def get_reading_ranking(
    db: AsyncSession,
    cls: Class
) -> List[dict]:
    """获取学员阅读进度排行"""
    result = await db.execute(
        select(ClassMember, User)
        .join(User)
        .where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    students = result.all()
    
    reading_data = []
    for member, u in students:
        result = await db.execute(
            select(ReadingProgress).where(ReadingProgress.user_id == u.id)
        )
        readings = result.scalars().all()
        
        total_duration = sum(r.duration for r in readings)
        avg_progress = sum(r.progress for r in readings) / len(readings) if readings else 0
        
        # 获取测验平均分
        result = await db.execute(
            select(TestResult).where(TestResult.user_id == u.id)
        )
        completed = result.scalars().all()
        avg_score = sum(r.score for r in completed) / len(completed) if completed else 0
        
        reading_data.append({
            "user_id": u.id,
            "name": u.name,
            "total_duration_minutes": round(total_duration / 60, 1),
            "avg_progress": round(avg_progress, 1),
            "tests_completed": len(completed),
            "avg_score": round(avg_score, 1)
        })
    
    reading_data.sort(key=lambda x: x['avg_progress'], reverse=True)
    return reading_data


# ═══════════════════════════════════════════════════════════════
# 成绩统计排行
# ═══════════════════════════════════════════════════════════════

async def get_scores_ranking(
    db: AsyncSession,
    cls: Class
) -> List[dict]:
    """获取学员成绩排行"""
    result = await db.execute(
        select(ClassMember, User)
        .join(User)
        .where(
            ClassMember.class_id == cls.id,
            ClassMember.role == UserRole.STUDENT
        )
    )
    students = result.all()
    
    scores_data = []
    for member, u in students:
        result = await db.execute(
            select(TestResult).where(TestResult.user_id == u.id)
        )
        results = result.scalars().all()
        
        avg_score = sum(r.score for r in results) / len(results) if results else 0
        scores = [r.score for r in results if r.score]
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0
        
        scores_data.append({
            "user_id": u.id,
            "name": u.name,
            "tests_completed": len(results),
            "avg_score": round(avg_score, 1),
            "max_score": max_score,
            "min_score": min_score
        })
    
    scores_data.sort(key=lambda x: x['avg_score'], reverse=True)
    return scores_data
