"""
管理员-题目管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select, func, delete, text as sql_text
from app.core.database import AsyncSessionLocal
from app.models.class_system import Question as QuestionModel, User, UserRole
from .shared import require_admin

router = APIRouter(prefix="/questions", tags=["管理员-题目管理"])


# ─── Schema ───────────────────────────────────────────────────────────────────

import json

def _parse_list(val) -> List[str]:
    """从数据库 TEXT/JSON 字段解析为 Python list"""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


class QuestionBase(BaseModel):
    content: str
    question_type: str
    textbook_id: Optional[int] = None
    chapter_id: Optional[int] = None

class QuestionCreate(QuestionBase):
    options: List[str] = []
    answer: List[str] = []
    difficulty: Optional[int] = None
    explanation: Optional[str] = None

class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    question_type: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[List[str]] = None
    difficulty: Optional[int] = None
    explanation: Optional[str] = None


# ─── 辅助 ────────────────────────────────────────────────────────────────────

def _to_json(val) -> Optional[str]:
    """Python list → JSON 字符串，用于写入 TEXT 列"""
    if val is None:
        return None
    return json.dumps(val, ensure_ascii=False)


# ─── 导入模板下载（必须在 /{question_id} 之前定义）───────────────────────────

from fastapi.responses import StreamingResponse
import io
import csv

@router.get("/import-template")
async def download_import_template(
    _: User = Depends(require_admin),
):
    """下载题目导入 CSV 模板"""
    headers = ["题目内容", "题型(single/judge/multiple)", "选项(JSON数组)", "答案(JSON数组)", "难度(1-5整数)", "解析"]
    sample = [
        ["水下救援时，漩涡的最佳逃脱方向是？", "single",
         '["A. 顺漩涡方向游出", "B. 向漩涡中心游去", "C. 横向游出漩涡范围", "D. 原地等待救援"]',
         '["C"]', "3", "C选项是正确答案"],
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(sample)
    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.read().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=question_import_template.csv"},
    )


# ─── 批量导入（占位）───────────────────────────────────────────────────────────

@router.post("/import")
async def import_questions(
    _: User = Depends(require_admin),
):
    raise HTTPException(status_code=501, detail="批量导入功能开发中")


# ─── 列表 ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    textbook_id: Optional[int] = Query(None),
    _: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        query = select(QuestionModel)
        count_q = select(func.count(QuestionModel.id))

        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(QuestionModel.content.ilike(pattern))
            count_q = count_q.where(QuestionModel.content.ilike(pattern))
        if question_type:
            query = query.where(QuestionModel.question_type == question_type)
            count_q = count_q.where(QuestionModel.question_type == question_type)
        if textbook_id:
            query = query.where(QuestionModel.textbook_id == textbook_id)
            count_q = count_q.where(QuestionModel.textbook_id == textbook_id)

        total = (await db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(QuestionModel.id.desc())
        rows = (await db.execute(query)).scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": r.id,
                    "content": r.content,
                    "question_type": r.question_type,
                    "options": _parse_list(r.options),
                    "answer": _parse_list(r.answer),
                    "difficulty": r.difficulty,
                    "explanation": r.explanation,
                    "textbook_id": r.textbook_id,
                    "chapter_id": r.chapter_id,
                }
                for r in rows
            ],
        }


# ─── 题目详情 ──────────────────────────────────────────────────────────────────

@router.get("/{question_id}")
async def get_question(
    question_id: int,
    _: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        r = await db.get(QuestionModel, question_id)
        if not r:
            raise HTTPException(status_code=404, detail="题目不存在")
        return {
            "id": r.id,
            "content": r.content,
            "question_type": r.question_type,
            "options": _parse_list(r.options),
            "answer": _parse_list(r.answer),
            "difficulty": r.difficulty,
            "explanation": r.explanation,
            "textbook_id": r.textbook_id,
            "chapter_id": r.chapter_id,
        }


# ─── 新增题目 ──────────────────────────────────────────────────────────────────

@router.post("")
async def create_question(
    body: QuestionCreate,
    current_user: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        try:
            question = QuestionModel(
                content=body.content,
                question_type=body.question_type,
                options=_to_json(body.options),
                answer=_to_json(body.answer),
                difficulty=body.difficulty,
                explanation=body.explanation,
                textbook_id=body.textbook_id,
                chapter_id=body.chapter_id,
            )
            db.add(question)
            await db.commit()
            await db.refresh(question)
            return {"success": True, "id": question.id, "message": "题目创建成功"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"创建失败：{str(e)}")


# ─── 更新题目 ──────────────────────────────────────────────────────────────────

@router.put("/{question_id}")
async def update_question(
    question_id: int,
    body: QuestionUpdate,
    _: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        r = await db.get(QuestionModel, question_id)
        if not r:
            raise HTTPException(status_code=404, detail="题目不存在")
        try:
            if body.content is not None:
                r.content = body.content
            if body.question_type is not None:
                r.question_type = body.question_type
            if body.options is not None:
                r.options = _to_json(body.options)
            if body.answer is not None:
                r.answer = _to_json(body.answer)
            if body.difficulty is not None:
                r.difficulty = body.difficulty
            if body.explanation is not None:
                r.explanation = body.explanation
            await db.commit()
            return {"success": True, "id": question_id, "message": "题目更新成功"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"更新失败：{str(e)}")


# ─── 删除题目 ──────────────────────────────────────────────────────────────────

@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    _: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        r = await db.get(QuestionModel, question_id)
        if not r:
            raise HTTPException(status_code=404, detail="题目不存在")
        try:
            await db.delete(r)
            await db.commit()
            return {"success": True, "message": "题目删除成功"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"删除失败：{str(e)}")



