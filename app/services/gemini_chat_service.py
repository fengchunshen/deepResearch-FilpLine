"""Gemini 聊天服务 - 使用 OpenAI ChatCompletions 兼容方式调用 Gemini."""
from typing import AsyncIterator, Dict, Any

import httpx
import logging

from app.core.config import settings
from app.models.gemini import GeminiChatRequest, GeminiChatCompletionResponse
from app.services.deepsearch_engine import get_gemini_base_url


logger = logging.getLogger(__name__)


class GeminiChatService:
    """Gemini 聊天服务类."""

    def __init__(self) -> None:
        """初始化 Gemini 聊天服务."""
        self._api_key = settings.GEMINI_API_KEY
        self._default_model = settings.GEMINI_MODEL
        self._timeout = settings.API_TIMEOUT

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY 未配置，请检查环境变量或 .env 文件")

        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: GeminiChatRequest, stream: bool) -> Dict[str, Any]:
        """构建发送到 Gemini 的请求体."""
        payload: Dict[str, Any] = request.model_dump(exclude_none=True)

        # 默认模型
        if not payload.get("model"):
            payload["model"] = self._default_model

        payload["stream"] = stream
        return payload

    async def chat_completion(
        self,
        request: GeminiChatRequest,
    ) -> GeminiChatCompletionResponse:
        """
        使用非流式方式调用 Gemini ChatCompletions.

        Args:
            request: 聊天请求模型

        Returns:
            GeminiChatCompletionResponse: 完整回答
        """
        base_url = get_gemini_base_url()
        url = f"{base_url}/chat/completions"

        headers = self._build_headers()
        payload = self._build_payload(request, stream=False)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return GeminiChatCompletionResponse.model_validate(data)
        except httpx.HTTPError as e:
            logger.error(f"Gemini 非流式请求失败: {e}")
            raise

    async def chat_completion_stream(
        self,
        request: GeminiChatRequest,
    ) -> AsyncIterator[str]:
        """
        使用流式方式调用 Gemini ChatCompletions.

        直接透传底层 Gemini 的 SSE/流式返回数据，兼容 OpenAI 的流式格式。

        Args:
            request: 聊天请求模型

        Yields:
            str: 从 Gemini 返回的原始流式数据片段
        """
        base_url = get_gemini_base_url()
        url = f"{base_url}/chat/completions"

        headers = self._build_headers()
        payload = self._build_payload(request, stream=True)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        # 直接将 Gemini 的响应片段透传给前端客户端
                        if chunk:
                            yield chunk
        except httpx.HTTPError as e:
            logger.error(f"Gemini 流式请求失败: {e}")
            raise


# 创建全局服务实例
gemini_chat_service = GeminiChatService()


