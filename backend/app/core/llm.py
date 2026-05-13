"""
LLM Helper - OpenAI-compatible API wrapper
Config loaded from database (llm_config module), not env vars.
"""
import os
import json
import httpx
import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class LLMHelper:
    """Flexible LLM wrapper for content analysis tasks"""

    def __init__(self):
        self.api_url: str = ""
        self.api_key: str = ""
        self.model: str = ""
        self.timeout: int = 120
        self._client: Optional[httpx.AsyncClient] = None

    def configure(self, config: Dict[str, str]):
        """从数据库配置加载（由 llm_config.db_get_llm_runtime_config 提供）"""
        self.api_url = config.get("llm_base_url", "")
        self.api_key = config.get("llm_api_key", "")
        self.model = config.get("llm_model", "deepseek-chat")
        max_tok = config.get("llm_max_tokens", "4096")
        try:
            self.timeout = min(int(max_tok) * 2, 300)
        except ValueError:
            self.timeout = 120

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_key and self.model)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Send chat completion request"""
        if not self.is_configured:
            raise RuntimeError("LLM not configured. Call configure() first or check db settings.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = await self.client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    async def analyze_content(
        self,
        system_prompt: str,
        content: str,
        temperature: float = 0.2,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]
        return await self.chat(messages, temperature=temperature, max_tokens=4096)

    async def analyze_content_json(
        self,
        system_prompt: str,
        content: str,
        temperature: float = 0.2,
    ) -> Any:
        raw = await self.analyze_content(system_prompt, content, temperature)
        return self._parse_json_response(raw)

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        logger.error(f"Failed to parse JSON from LLM response: {text[:200]}")
        raise ValueError("LLM response is not valid JSON")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


_singleton: Optional[LLMHelper] = None

def get_llm_helper() -> LLMHelper:
    global _singleton
    if _singleton is None:
        _singleton = LLMHelper()
    return _singleton