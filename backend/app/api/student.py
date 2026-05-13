"""
学员API - 班级制培训管理系统
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_student
from app.api.auth_v2 import get_current_class, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.textbook_utils import (
    get_class_textbook_ids,
    get_class_textbooks,
)
from app.models.class_system import (
    Chapter,
    Class,
    ClassTextbook,
    QAQuestion,
    Question,
    QuestionType,
    ReadingProgress,
    Test,
    TestResult,
    TestStatus,
    Textbook,
    User,
)

router = APIRouter(
    prefix="/student",
    tags=["学员"],
    dependencies=[Depends(require_student)]
)


# ===== 教材学习 =====

@router.get("/textbooks")
async def list_textbooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """可学习教材列表（统一教材查询）"""
    textbooks = await get_class_textbooks(db, cls.id)

    # 获取阅读进度
    progress_data = []
    for t in textbooks:
        result = await db.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user.id,
                ReadingProgress.textbook_id == t.id
            )
        )
        rp = result.scalar_one_or_none()

        progress_data.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "total_chapters": t.total_chapters,
            "total_pages": t.total_pages,
            "has_interactive": t.has_interactive,
            "progress": rp.progress if rp else 0,
            "current_page": rp.current_page if rp else 0
        })

    return progress_data


@router.get("/textbooks/{textbook_id}")
async def get_textbook(
    textbook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """教材详情（含章节目录）
    
    互动式教材从 JSON 文件读取章节结构
    PDF教材从数据库读取章节
    """
    import os

    textbook_ids = await get_class_textbook_ids(db, cls.id)

    if textbook_id not in textbook_ids:
        raise HTTPException(status_code=403, detail="该教材不在班级范围内")

    result = await db.execute(select(Textbook).where(Textbook.id == textbook_id))
    t = result.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail="教材不存在")

    # 获取阅读进度
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user.id,
            ReadingProgress.textbook_id == textbook_id
        )
    )
    rp = result.scalar_one_or_none()

    # 检查是否是互动式教材
    json_path = f"{settings.INTERACTIVE_DATA_DIR}/{textbook_id}_interactive.json"

    if os.path.exists(json_path):
        # 互动式教材：从 JSON 文件读取
        try:
            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)
            return {
                "id": str(t.id),
                "title": data.get("title", t.name),
                "name": data.get("title", t.name),  # 兼容 name 字段
                "description": data.get("description", t.description),
                "total_sections": data.get("total_sections", 0),
                "progress": rp.progress if rp else 0,
                "current_section": rp.current_page if rp else 0,
                "is_interactive": True,
                "sections": data.get("sections", []),
                "key_concepts_map": data.get("key_concepts_map", {}),
                "metadata": data.get("metadata", {})
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取教材失败: {str(e)}")
    else:
        # PDF教材：从数据库读取章节
        result = await db.execute(
            select(Chapter).where(Chapter.textbook_id == textbook_id).order_by(Chapter.sort_order)
        )
        chapters = result.scalars().all()

        return {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "total_pages": t.total_pages,
            "progress": rp.progress if rp else 0,
            "current_page": rp.current_page if rp else 0,
            "is_interactive": False,
            "chapters": [
                {
                    "id": c.id,
                    "title": c.title,
                    "page_start": c.page_start,
                    "page_end": c.page_end
                }
                for c in chapters
            ]
        }


@router.get("/textbooks/{textbook_id}/chapters/{chapter_id}")
async def get_chapter_content(
    textbook_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """章节内容"""
    # 获取班级分配的所有教材ID（统一表，包含 pdf 和 interactive）
    pdf_result = await db.execute(
        select(ClassTextbook.textbook_id).where(
            ClassTextbook.class_id == cls.id,
            ClassTextbook.resource_type == 'pdf'
        )
    )
    pdf_ids = [row[0] for row in pdf_result.all()]

    interactive_result = await db.execute(
        select(ClassTextbook.textbook_id).where(
            ClassTextbook.class_id == cls.id,
            ClassTextbook.resource_type == 'interactive'
        )
    )
    interactive_ids = [row[0] for row in interactive_result.all()]

    textbook_ids = list(set(pdf_ids + interactive_ids))

    if textbook_id not in textbook_ids:
        raise HTTPException(status_code=403, detail="该教材不在班级范围内")

    result = await db.execute(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.textbook_id == textbook_id
        )
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    return {
        "id": chapter.id,
        "title": chapter.title,
        "content": chapter.content,
        "page_start": chapter.page_start,
        "page_end": chapter.page_end
    }


class ReadingProgressRequest(BaseModel):
    textbook_id: int
    chapter_id: int | None = None
    current_page: int
    duration: int  # 本次阅读时长（秒）
    progress_percent: int | None = None  # 互动式教材前端直接传百分比


@router.post("/reading/progress")
async def update_reading_progress(
    request: ReadingProgressRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """上报阅读进度"""
    # 验证教材在班级范围内 — 检查 class_textbooks 表
    ct_result = await db.execute(
        select(ClassTextbook.textbook_id).where(ClassTextbook.class_id == cls.id)
    )
    allowed_ids = [r[0] for r in ct_result.all()]
    # 也兼容旧方式的textbooks字段
    textbook_ids = cls.get_textbook_ids()
    allowed_ids = list(set(allowed_ids + textbook_ids))

    if request.textbook_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="该教材不在班级范围内")

    result = await db.execute(select(Textbook).where(Textbook.id == request.textbook_id))
    t = result.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail="教材不存在")

    # 计算进度百分比 — 互动式教材前端可直接传百分比，否则后端计算
    if request.progress_percent is not None:
        progress = request.progress_percent
    elif t.has_interactive:
        # 互动式教材：current_page=完成单元数，基数从JSON文件获取
        import json as _json
        import os
        interactive_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'interactive')
        total_units = 0
        for fname in os.listdir(interactive_dir):
            if fname.endswith('_interactive.json'):
                try:
                    with open(os.path.join(interactive_dir, fname)) as f:
                        _data = _json.load(f)
                    if int(fname.split('_')[0]) == t.id:
                        total_units = sum(len(s.get('units', [])) for s in _data.get('sections', []))
                        break
                except Exception:
                    pass
        if total_units == 0:
            total_units = t.total_chapters or 1
        progress = min(100, int((request.current_page / total_units) * 100)) if total_units > 0 else 0
    else:
        progress = int((request.current_page / t.total_pages) * 100) if t.total_pages > 0 else 0

    # 查找或创建进度记录
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user.id,
            ReadingProgress.textbook_id == request.textbook_id
        )
    )
    rp = result.scalar_one_or_none()

    if rp:
        rp.current_page = request.current_page
        rp.progress = progress
        rp.duration += request.duration
        rp.chapter_id = request.chapter_id
        rp.last_read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        rp = ReadingProgress(
            user_id=user.id,
            textbook_id=request.textbook_id,
            chapter_id=request.chapter_id,
            current_page=request.current_page,
            progress=progress,
            duration=request.duration,
            last_read_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(rp)

    await db.commit()

    return {"success": True, "progress": progress}


@router.get("/reading/progress")
async def get_reading_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """获取我的阅读进度"""
    result = await db.execute(
        select(ReadingProgress, Textbook)
        .join(Textbook)
        .where(ReadingProgress.user_id == user.id)
    )
    readings = result.all()

    return [
        {
            "textbook_id": rp.textbook_id,
            "textbook_name": t.name,
            "progress": rp.progress,
            "current_page": rp.current_page,
            "duration": rp.duration,
            "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None
        }
        for rp, t in readings
    ]


# ===== 测验/考试 =====

@router.get("/tests")
async def list_tests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """测验列表"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = await db.execute(
        select(Test).where(
            Test.class_id == cls.id,
            Test.status == TestStatus.PUBLISHED
        ).order_by(Test.created_at.desc())
    )
    tests = result.scalars().all()

    tests_data = []
    for t in tests:
        # 检查是否已提交
        result = await db.execute(
            select(TestResult).where(
                TestResult.test_id == t.id,
                TestResult.user_id == user.id
            )
        )
        tr = result.scalar_one_or_none()

        # 检查时间范围
        is_available = True
        if t.start_time and t.start_time > now:
            is_available = False
        if t.end_time and t.end_time < now:
            is_available = False

        tests_data.append({
            "id": t.id,
            "title": t.title,
            "test_type": t.test_type.value,
            "total_score": t.total_score,
            "duration": t.duration,
            "question_count": len(t.get_question_ids()),
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
            "is_available": is_available,
            "is_completed": tr is not None,
            "score": tr.score if tr else None
        })

    return tests_data


@router.get("/tests/{test_id}")
async def get_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """测验详情（含题目）"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")

    if test.status != TestStatus.PUBLISHED:
        raise HTTPException(status_code=403, detail="测验未发布")

    # 检查是否已提交
    result = await db.execute(
        select(TestResult).where(
            TestResult.test_id == test_id,
            TestResult.user_id == user.id
        )
    )
    tr = result.scalar_one_or_none()

    if tr and tr.submitted_at:
        raise HTTPException(status_code=400, detail="您已完成该测验")

    # 获取题目
    question_ids = test.get_question_ids()
    result = await db.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    questions = result.scalars().all()

    return {
        "id": test.id,
        "title": test.title,
        "test_type": test.test_type.value,
        "duration": test.duration,
        "total_score": test.total_score,
        "questions": [
            {
                "id": q.id,
                "question_type": q.question_type.value,
                "content": q.content,
                "options": q.get_options(),
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    }


class StartTestRequest(BaseModel):
    pass


class SubmitTestRequest(BaseModel):
    answers: list[dict]  # [{question_id, answer}]


@router.post("/tests/{test_id}/start")
async def start_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """开始答题（记录开始时间）"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")

    # 检查是否已提交
    result = await db.execute(
        select(TestResult).where(
            TestResult.test_id == test_id,
            TestResult.user_id == user.id
        )
    )
    tr = result.scalar_one_or_none()

    if tr:
        raise HTTPException(status_code=400, detail="您已完成该测验")

    # 创建答题记录（用于计时）
    tr = TestResult(
        test_id=test_id,
        user_id=user.id,
        answers=json.dumps([]),
        submitted_at=None,
        is_graded=False
    )
    db.add(tr)
    await db.commit()

    return {
        "success": True,
        "start_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "duration": test.duration
    }


@router.post("/tests/{test_id}/submit")
async def submit_test(
    test_id: int,
    request: SubmitTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """提交答案"""
    result = await db.execute(
        select(Test).where(Test.id == test_id, Test.class_id == cls.id)
    )
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(status_code=404, detail="测验不存在")

    # 检查答题记录
    result = await db.execute(
        select(TestResult).where(
            TestResult.test_id == test_id,
            TestResult.user_id == user.id
        )
    )
    tr = result.scalar_one_or_none()

    if not tr:
        # 自动创建答题记录（兼容直接提交的情况）
        tr = TestResult(
            test_id=test_id,
            user_id=user.id,
            answers=json.dumps([]),
            is_graded=False
        )
        db.add(tr)
        await db.flush()

    if tr.submitted_at:
        raise HTTPException(status_code=400, detail="您已提交答案")

    # 获取题目
    question_ids = test.get_question_ids()
    result = await db.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    questions = result.scalars().all()

    # 计算成绩
    score = 0
    per_question_score = test.total_score / len(questions) if questions else 5

    for q in questions:
        for answer in request.answers:
            if answer['question_id'] == q.id:
                correct_answer = q.get_answer()
                user_answer = answer['answer']

                # 判断是否正确
                if q.question_type == QuestionType.SINGLE:
                    if user_answer == correct_answer:
                        score += per_question_score
                elif q.question_type == QuestionType.MULTIPLE:
                    if isinstance(user_answer, list) and set(user_answer) == set(correct_answer):
                        score += per_question_score
                elif q.question_type == QuestionType.JUDGE:
                    if user_answer == correct_answer:
                        score += per_question_score

    # 更新记录
    tr.answers = json.dumps(request.answers)
    tr.score = int(score)
    tr.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    tr.is_graded = True

    await db.commit()

    return {
        "success": True,
        "score": int(score),
        "total_score": test.total_score,
        "submitted_at": tr.submitted_at.isoformat()
    }


# ===== 成绩查看 =====

@router.get("/scores")
async def get_my_scores(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """我的成绩列表"""
    result = await db.execute(
        select(TestResult, Test)
        .join(Test)
        .where(
            TestResult.user_id == user.id,
            Test.class_id == cls.id
        ).order_by(TestResult.submitted_at.desc())
    )
    results = result.all()

    return [
        {
            "test_id": tr.test_id,
            "test_title": t.title,
            "test_type": t.test_type.value,
            "score": tr.score,
            "total_score": t.total_score,
            "time_spent": tr.time_spent,
            "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None
        }
        for tr, t in results
    ]


@router.get("/scores/{test_id}")
async def get_test_detail(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """单次测验详情"""
    result = await db.execute(
        select(TestResult, Test)
        .join(Test)
        .where(
            TestResult.test_id == test_id,
            TestResult.user_id == user.id,
            Test.class_id == cls.id
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="测验记录不存在")

    tr, t = row

    # 获取题目和用户答案
    question_ids = t.get_question_ids()
    result = await db.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    questions = result.scalars().all()

    user_answers = json.loads(tr.answers) if tr.answers else []

    return {
        "test": {
            "id": t.id,
            "title": t.title,
            "score": tr.score,
            "total_score": t.total_score
        },
        "questions": [
            {
                "id": q.id,
                "content": q.content,
                "options": q.get_options(),
                "correct_answer": q.get_answer(),
                "explanation": q.explanation,
                "user_answer": next(
                    (a['answer'] for a in user_answers if a['question_id'] == q.id),
                    None
                )
            }
            for q in questions
        ]
    }


# ===== 错题本 =====

@router.get("/wrong-answers")
async def get_wrong_answers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """我的错题列表"""
    # 获取所有测验记录
    result = await db.execute(
        select(TestResult, Test)
        .join(Test)
        .where(
            TestResult.user_id == user.id,
            Test.class_id == cls.id,
            TestResult.is_graded == True
        )
    )
    test_results = result.all()

    wrong_questions = []

    for tr, t in test_results:
        question_ids = t.get_question_ids()
        result = await db.execute(
            select(Question).where(Question.id.in_(question_ids))
        )
        questions = result.scalars().all()

        user_answers = json.loads(tr.answers) if tr.answers else []

        for q in questions:
            for answer in user_answers:
                if answer['question_id'] == q.id:
                    correct_answer = q.get_answer()
                    user_answer = answer['answer']

                    # 判断是否错误
                    is_wrong = False
                    if q.question_type == QuestionType.SINGLE:
                        is_wrong = user_answer != correct_answer
                    elif q.question_type == QuestionType.MULTIPLE:
                        is_wrong = isinstance(user_answer, list) and set(user_answer) != set(correct_answer)
                    elif q.question_type == QuestionType.JUDGE:
                        is_wrong = user_answer != correct_answer

                    if is_wrong:
                        wrong_questions.append({
                            "id": q.id,
                            "test_title": t.title,
                            "content": q.content,
                            "options": q.get_options(),
                            "correct_answer": correct_answer,
                            "user_answer": user_answer,
                            "explanation": q.explanation
                        })

    return wrong_questions


# ===== 个人信息 =====

@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """个人信息"""
    return {
        "id": user.id,
        "name": user.name,
        "id_card": user.id_card,
        "phone": user.phone,
        "class_name": cls.name,
        "class_status": cls.status.value
    }


# ===== 学习概览 =====

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """学习概览"""
    # 阅读进度平均
    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user.id)
    )
    readings = result.scalars().all()

    avg_reading_progress = sum(r.progress for r in readings) / len(readings) if readings else 0

    # 测验完成情况
    result = await db.execute(
        select(Test).where(Test.class_id == cls.id, Test.status == TestStatus.PUBLISHED)
    )
    all_tests = result.scalars().all()

    result = await db.execute(
        select(TestResult).where(TestResult.user_id == user.id, TestResult.is_graded == True)
    )
    completed = result.scalars().all()

    avg_score = sum(r.score for r in completed) / len(completed) if completed else 0

    return {
        "class_name": cls.name,
        "reading_progress": round(avg_reading_progress, 1),
        "tests_total": len(all_tests),
        "tests_completed": len(completed),
        "avg_score": round(avg_score, 1),
        "remaining_days": (cls.end_time - datetime.now(timezone.utc).replace(tzinfo=None)).days if cls.end_time > datetime.now(timezone.utc).replace(tzinfo=None) else 0
    }


# ═══════════════════════════════════════════════
# 问答模块（学员视角）
# ═══════════════════════════════════════════════

@router.get("/qa")
async def list_qa(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """问答列表"""
    result = await db.execute(
        select(QAQuestion).where(QAQuestion.class_id == cls.id)
        .order_by(QAQuestion.created_at.desc()).limit(50)
    )
    items = result.scalars().all()
    return [{
        "id": q.id, "title": q.title, "content": q.content,
        "reply": q.reply, "replied_at": q.replied_at.isoformat() if q.replied_at else None,
        "asker_name": q.asker.name if q.asker else "",
        "replier_name": q.replier.name if q.replier else "",
        "created_at": q.created_at.isoformat() if q.created_at else None
    } for q in items]


@router.post("/qa")
async def ask_question(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    cls: Class = Depends(get_current_class)
):
    """提问"""
    q = QAQuestion(
        class_id=cls.id, user_id=user.id,
        title=data.get("title", ""), content=data.get("content", "")
    )
    db.add(q)
    await db.commit()
    return {"success": True, "id": q.id}
