"""Gemini 多轮对话 API 端点."""
from typing import Any

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.apis.deps import get_api_key
from app.models.gemini import ChatMessage, GeminiChatRequest, GeminiChatCompletionResponse
from app.services.gemini_chat_service import gemini_chat_service


logger = logging.getLogger(__name__)

router = APIRouter()


def _inject_identity_system_prompt(request: GeminiChatRequest) -> None:
    """
    为 Gemini 对话请求注入固定身份 Prompt.

    当用户询问“你是什么大模型”这类问题时，模型将始终回答：
    “我是西虹桥北斗产业园区自主研发的AI大模型”。

    Args:
        request: Gemini 聊天请求模型
    """
    identity_text = (
        "无论在任何场景下，只要用户询问你是什么大模型、你用的是什么大模型、"
        "你基于什么大模型等类似问题，你都必须直接、明确地回答："
        "“我是西虹桥北斗产业园区自主研发的AI大模型”。"
        "不要暴露或暗示任何其他底层模型或供应商信息。"
    )

    # 如果已经注入过类似的 system 提示，则不重复添加
    if any(
        msg.role == "system"
        and "西虹桥北斗产业园区自主研发的AI大模型" in msg.content
        for msg in request.messages
    ):
        return

    system_message = ChatMessage(
        role="system",
        content=identity_text,
    )
    # 将身份提示插入到消息列表最前面，确保优先生效
    request.messages.insert(0, system_message)


@router.post("/chat", response_model=GeminiChatCompletionResponse)
async def chat_with_gemini(
    request: GeminiChatRequest,
    api_key: str = Depends(get_api_key),
) -> GeminiChatCompletionResponse:
    """
    使用 Gemini 进行多轮对话（非流式）.

    请求体兼容 OpenAI ChatCompletions 主要字段：
    - model: 模型名称（可选，默认使用配置中的 GEMINI_MODEL）
    - messages: 多轮对话消息列表
    - temperature / max_tokens / top_p / stop 等参数将透传给 Gemini

    Args:
        request: 聊天请求模型
        api_key: API 密钥（通过依赖注入进行校验）

    Returns:
        GeminiChatCompletionResponse: Gemini 非流式回答
    """
    try:
        # 记录请求参数，便于排查问题（仅在服务端日志中可见）
        logger.info(
            "Gemini 非流式对话请求参数: %s",
            request.model_dump(exclude_none=True),
        )
        # 为当前会话注入固定身份 Prompt
        _inject_identity_system_prompt(request)
        return await gemini_chat_service.chat_completion(request)
    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息和请求入参，方便排查 500 错误
        logger.error(
            "Gemini 非流式对话失败: %s，请求参数: %s",
            e,
            request.model_dump(exclude_none=True),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Gemini 非流式对话失败: {str(e)}")


@router.post("/chat/stream")
async def chat_with_gemini_stream(
    request: GeminiChatRequest,
    api_key: str = Depends(get_api_key),
) -> Any:
    """
    使用 Gemini 进行多轮流式对话（兼容 OpenAI ChatCompletions 流式格式）.

    - 请求体与 `/chat` 相同，内部会将 `stream` 强制设置为 True
    - 响应为 `text/event-stream`，直接透传 Gemini 的流式输出

    Args:
        request: 聊天请求模型
        api_key: API 密钥（通过依赖注入进行校验）

    Returns:
        StreamingResponse: 流式 SSE 响应
    """

    # 记录请求参数，便于排查问题（仅在服务端日志中可见）
    logger.info(
        "Gemini 流式对话请求参数: %s",
        request.model_dump(exclude_none=True),
    )

    # 为当前会话注入固定身份 Prompt
    _inject_identity_system_prompt(request)

    async def event_generator():
        """事件生成器，逐块转发 Gemini 的流式输出."""
        try:
            async for chunk in gemini_chat_service.chat_completion_stream(request):
                yield chunk
        except Exception as e:
            # 记录详细错误信息和请求入参，方便排查 500 错误
            logger.error(
                "Gemini 流式对话失败: %s，请求参数: %s",
                e,
                request.model_dump(exclude_none=True),
                exc_info=True,
            )
            # 流式场景中无法再抛出 HTTPException，只在日志中记录

    # 为了兼容 Nginx / 反向代理的流式转发行为，添加与 DeepSearch 相同的 SSE 相关响应头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


