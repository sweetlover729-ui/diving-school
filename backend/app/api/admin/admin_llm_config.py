"""
Admin API - LLM Configuration
Super admin only: manage API key, global toggle, per-course toggle
"""
import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.shared import require_admin
from app.core import llm_config
from app.core.database import get_db

router = APIRouter(prefix="/llm-config", tags=["LLM配置"])

# ── Schemas ──

class LLMConfigResponse(BaseModel):
    llm_enabled: str = "false"
    llm_api_key: str = "****"
    llm_base_url: str = ""
    llm_model: str = ""
    llm_max_tokens: str = ""
    llm_temperature: str = ""
    llm_enabled_desc: str = ""
    llm_api_key_desc: str = ""
    llm_base_url_desc: str = ""
    llm_model_desc: str = ""
    llm_max_tokens_desc: str = ""
    llm_temperature_desc: str = ""
    _has_key: bool = False

class LLMConfigUpdate(BaseModel):
    llm_enabled: str | None = None   # "true" / "false"
    llm_api_key: str | None = None   # 新 key，传了就会更新（加密存储）
    llm_base_url: str | None = None
    llm_model: str | None = None     # 会被校验，禁止 pro
    llm_max_tokens: str | None = None
    llm_temperature: str | None = None

class TestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: float = 0

class CourseLLMStatus(BaseModel):
    id: int
    title: str
    llm_enabled: bool

class ToggleRequest(BaseModel):
    enabled: bool

# ── Endpoints ──

@router.get("", response_model=LLMConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """查询LLM全局配置（API Key 已脱敏，任何角色都看不到明文）"""
    return await llm_config.db_get_all_config(db)


@router.put("", response_model=LLMConfigResponse)
async def update_config(
    data: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """更新LLM全局配置。API Key 会加密存储到数据库。"""
    updates = data.model_dump(exclude_none=True)

    if "llm_model" in updates:
        ok, msg = llm_config.validate_model(updates["llm_model"])
        if not ok:
            raise HTTPException(400, msg)

    for key, value in updates.items():
        encrypted = key == "llm_api_key"
        await llm_config.db_set_setting(db, key, str(value), encrypted)

    return await llm_config.db_get_all_config(db)


@router.post("/test", response_model=TestResponse)
async def test_api_key(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """测试 API Key 是否有效。不返回 Key 明文。"""
    cfg = await llm_config.db_get_llm_runtime_config(db)
    api_key = cfg.get("llm_api_key", "")
    base_url = cfg.get("llm_base_url", "")
    model = cfg.get("llm_model", "")

    if not api_key:
        raise HTTPException(400, "未配置 API Key")

    if not base_url:
        raise HTTPException(400, "未配置 API 地址")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            start = asyncio.get_event_loop().time()
            resp = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
            )
            latency = (asyncio.get_event_loop().time() - start) * 1000

            if resp.status_code == 200:
                return TestResponse(success=True, message=f"连接成功（{model}）", latency_ms=latency)
            elif resp.status_code == 401:
                return TestResponse(success=False, message="API Key 无效（401 未授权）", latency_ms=latency)
            else:
                body = resp.text[:300]
                return TestResponse(
                    success=False,
                    message=f"返回 {resp.status_code}: {body}",
                    latency_ms=latency,
                )
    except httpx.ConnectError:
        return TestResponse(success=False, message="无法连接到 API 地址，请检查网络和URL")
    except Exception as e:
        return TestResponse(success=False, message=f"测试失败: {str(e)[:200]}")


# ── Per-Course Toggle ──

@router.get("/courses", response_model=list[CourseLLMStatus])
async def list_courses_llm(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return await llm_config.get_courses_llm_status(db)


@router.put("/courses/{course_id}")
async def toggle_course_llm(
    course_id: int,
    req: ToggleRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    await llm_config.toggle_course_llm(db, course_id, req.enabled)
    status = "已开启" if req.enabled else "已关闭"
    return {"success": True, "course_id": course_id, "status": status}


@router.get("/textbooks")
async def list_textbooks_llm(
    course_id: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    return await llm_config.get_textbooks_llm_status(db, course_id)


@router.put("/textbooks/{textbook_id}")
async def toggle_textbook_llm(
    textbook_id: int,
    req: ToggleRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    await llm_config.toggle_textbook_llm(db, textbook_id, req.enabled)
    status = "已开启" if req.enabled else "已关闭"
    return {"success": True, "textbook_id": textbook_id, "status": status}


@router.get("/check/{course_id}")
async def check_course_llm(
    course_id: int,
    textbook_id: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """检查指定课程/教材的LLM是否可用"""
    allowed, reason = await llm_config.check_llm_allowed(db, course_id, textbook_id)
    return {"allowed": allowed, "reason": reason}
