"""
教练员API - 班级制培训管理系统
"""
import json
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_instructor
from app.api.auth_v2 import get_current_class, get_current_user
from app.api.common_views import (
    get_analytics_summary,
    get_class_info,
    get_progress_overview,
    get_reading_ranking,
    get_scores_matrix,
    get_scores_ranking,
    get_single_test_scores,
    get_students_list,
)
from app.core.database import get_db
from app.core.textbook_utils import get_class_textbooks
from app.models.class_system import (
    Class,
    Question,
    QuestionType,
    ReadingProgress,
    Test,
    TestResult,
    TestStatus,
    TestType,
    User,
)

router = APIRouter(
    prefix="/instructor",
    tags=["教练员"],
    dependencies=[Depends(require_instructor)]
)


# ═══════════════════════════════════════════════
# 班级信息
# ═══════════════════════════════════════════════

@router.get("/class")
async def get_instructor_class(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """获取当前班级信息"""
    return await get_class_info(cls)


@router.get("/classes")
async def get_instructor_classes_alias(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """班级信息（前端别名 → /class）"""
    return await get_class_info(cls)


@router.get("/students")
async def list_students(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """学员列表"""
    return await get_students_list(db, cls, include_progress=False)


# ═══════════════════════════════════════════════
# 教材浏览
# ═══════════════════════════════════════════════

@router.get("/textbooks")
async def list_textbooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """可用教材列表（教练查看）"""
    textbooks = await get_class_textbooks(db, cls.id)
    return [
        {
            "id": t.id, "name": t.name, "description": t.description,
            "total_chapters": t.total_chapters, "total_pages": t.total_pages,
            "has_interactive": t.has_interactive
        }
        for t in textbooks
    ]


# ═══════════════════════════════════════════════
# 测验管理
# ═══════════════════════════════════════════════

class TestCreateRequest(BaseModel):
    title: str
    test_type: str
    questions: list[int]
    duration: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class GenerateTestRequest(BaseModel):
    textbook_id: int | None = None
    chapter_ids: list[int] | None = None
    question_types: list[str] | None = None
    difficulty_min: int = 1
    difficulty_max: int = 5
    count: int = 20


@router.get("/tests")
async def list_tests(
    test_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """测验列表"""
    query = select(Test).where(Test.class_id == cls.id)
    if test_type:
        query = query.where(Test.test_type == TestType(test_type))
    query = query.order_by(Test.created_at.desc())
    result = await db.execute(query)
    tests = result.scalars().all()

    return [
        {
            "id": t.id, "title": t.title, "test_type": t.test_type.value,
            "total_score": t.total_score, "duration": t.duration,
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
            "status": t.status.value, "question_count": len(t.get_question_ids()),
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in tests
    ]


@router.post("/tests")
async def create_test(
    request: TestCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """发布测验"""
    test = Test(
        class_id=cls.id,
        title=request.title,
        test_type=TestType(request.test_type),
        questions=json.dumps(request.questions),
        total_score=len(request.questions) * 5,
        duration=request.duration,
        start_time=request.start_time,
        end_time=request.end_time,
        status=TestStatus.PUBLISHED,
        created_by=user.id
    )
    db.add(test)
    await db.commit()
    return {"success": True, "id": test.id, "message": "测验发布成功"}


@router.get("/tests/{test_id}")
async def get_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """测验详情"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")

    question_ids = test.get_question_ids()
    result = await db.execute(select(Question).where(Question.id.in_(question_ids)))
    questions = result.scalars().all()

    return {
        "id": test.id, "title": test.title, "test_type": test.test_type.value,
        "total_score": test.total_score, "duration": test.duration,
        "start_time": test.start_time.isoformat() if test.start_time else None,
        "end_time": test.end_time.isoformat() if test.end_time else None,
        "status": test.status.value,
        "questions": [
            {"id": q.id, "question_type": q.question_type.value,
             "content": q.content, "options": q.get_options(), "difficulty": q.difficulty}
            for q in questions
        ]
    }


@router.delete("/tests/{test_id}")
async def delete_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """删除测验"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")
    await db.delete(test)
    await db.commit()
    return {"success": True, "message": "测验已删除"}


@router.post("/tests/generate")
async def generate_test(
    request: GenerateTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """智能抽题组卷"""
    query = select(Question).where(Question.is_active == True)
    if request.textbook_id:
        query = query.where(Question.textbook_id == request.textbook_id)
    if request.chapter_ids:
        query = query.where(Question.chapter_id.in_(request.chapter_ids))
    if request.question_types:
        types = [QuestionType(t) for t in request.question_types]
        query = query.where(Question.question_type.in_(types))
    query = query.where(Question.difficulty >= request.difficulty_min,
                        Question.difficulty <= request.difficulty_max)

    result = await db.execute(query)
    all_questions = result.scalars().all()
    if len(all_questions) < request.count:
        raise HTTPException(status_code=400,
            detail=f"题目数量不足，只有 {len(all_questions)} 道符合条件的题目")

    selected = random.sample(list(all_questions), request.count)
    return {
        "success": True, "count": len(selected),
        "questions": [
            {"id": q.id, "question_type": q.question_type.value,
             "content": q.content, "options": q.get_options(),
             "difficulty": q.difficulty, "textbook_id": q.textbook_id}
            for q in selected
        ]
    }


@router.get("/questions")
async def list_questions_for_instructor(
    textbook_id: int | None = None,
    question_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """题库浏览"""
    query = select(Question).where(Question.is_active == True)
    if textbook_id:
        query = query.where(Question.textbook_id == textbook_id)
    if question_type:
        query = query.where(Question.question_type == QuestionType(question_type))
    result = await db.execute(query)
    questions = result.scalars().all()
    return [
        {"id": q.id, "question_type": q.question_type.value,
         "content": q.content, "options": q.get_options(), "difficulty": q.difficulty}
        for q in questions
    ]


# ═══════════════════════════════════════════════
# 进度 & 成绩（共享视图）
# ═══════════════════════════════════════════════

@router.get("/progress")
async def get_students_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """学员进度概览"""
    return await get_progress_overview(db, cls)


@router.get("/progress/{user_id}")
async def get_student_detail_progress(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """单个学员详细进度"""
    result = await db.execute(select(User).where(User.id == user_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")

    # 验证学员属于该班级
    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user_id)
    )
    readings = result.scalars().all()

    # 成绩详情
    result = await db.execute(
        select(TestResult, Test).join(Test)
        .where(TestResult.user_id == user_id, Test.class_id == cls.id)
    )
    test_results = result.all()

    # 获取教材列表用于名称显示
    from app.core.textbook_utils import get_class_textbooks
    textbooks = await get_class_textbooks(db, cls.id)
    text_map = {t.id: t.name for t in textbooks}

    return {
        "user_id": student.id,
        "name": student.name,
        "reading": [
            {
                "textbook_id": rp.textbook_id,
                "textbook_name": text_map.get(rp.textbook_id, f"教材{rp.textbook_id}"),
                "progress": rp.progress, "current_page": rp.current_page,
                "duration": rp.duration,
                "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None
            }
            for rp in readings
        ],
        "tests": [
            {
                "test_id": tr.test_id, "test_title": t.title,
                "score": tr.score, "time_spent": tr.time_spent,
                "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None
            }
            for tr, t in test_results
        ]
    }


@router.get("/scores")
async def get_scores_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """成绩汇总表"""
    return await get_scores_matrix(db, cls)


@router.get("/scores/{test_id}")
async def get_test_scores(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """单次测验成绩详情"""
    return await get_single_test_scores(test_id, db, cls)


@router.get("/analytics/overview")
async def get_class_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """班级统计概览"""
    return await get_analytics_summary(db, cls)


@router.get("/analytics/reading")
async def get_reading_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """阅读统计排行"""
    return await get_reading_ranking(db, cls)


@router.get("/analytics/scores")
async def get_scores_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """成绩统计排行"""
    return await get_scores_ranking(db, cls)
