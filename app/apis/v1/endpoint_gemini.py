"""Gemini 多轮对话 API 端点."""
from typing import Any
import json
import re

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.apis.deps import get_api_key
from app.models.gemini import (
    ChatMessage,
    GeminiChatRequest,
    GeminiChatCompletionResponse,
    PolicyFormatRequest,
    PolicyFormatResponse,
)
from app.services.gemini_chat_service import gemini_chat_service


logger = logging.getLogger(__name__)

router = APIRouter()


def _count_chinese_and_digits(text: str) -> int:
    """
    统计文本中的中文字符和数字数量（排除标点符号）.
    
    Args:
        text: 待统计的文本
        
    Returns:
        中文字符和数字的总数
    """
    # 匹配中文字符（\u4e00-\u9fff）和数字（0-9）
    pattern = re.compile(r'[\u4e00-\u9fff0-9]')
    matches = pattern.findall(text)
    return len(matches)


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


@router.post("/chat/format", response_model=PolicyFormatResponse)
async def format_policy_markdown(
    request: PolicyFormatRequest,
    api_key: str = Depends(get_api_key),
) -> PolicyFormatResponse:
    """
    将政策原文转换为 Markdown 思维导图格式并生成概要.

    请求体：
    - content: 原文文本

    返回：
    - mind_map: 生成的 Markdown 思维导图正文
    - summary: 55 字以内的中文概要
    """
    system_prompt = (
        "你是政策结构化专家。请读取给定政策文本，分析其类型（如：资金扶持类、法规约束类、任务规划类、通知公告类等），并将其转换为逻辑清晰、排版美观的通用 Markdown 文档，同时给出一个 55 字以内的中文概要。\n\n"
        "一、 核心排版规范（严禁 Emoji）\n"
        "1. 视觉统一：标题下方必须使用 `---` 分割线。\n"
        "2. 数据敏感：所有 **金额、时限、日期、关键指标（数字）** 必须使用 **加粗**。\n"
        "3. 摘要置顶：文首必须包含一个 `> 引用块`，用于提炼政策的核心精神或一句话摘要。\n"
        "4. 层级清晰：使用无序列表 `*` 罗列要点，避免大段文字；若有步骤或顺序，使用有序列表 `1.`。\n\n"
        "二、 动态结构策略（根据内容自动适配）\n"
        "根据文本内容，动态选择最合适的二级标题结构，示例：\n"
        "- 资金扶持/申报类：申报对象、支持标准、申报条件、截止时间\n"
        "- 法律法规/管理办法类：适用范围、禁止行为、处罚措施、执行日期\n"
        "- 规划/指导意见类：建设目标、主要任务、保障措施\n"
        "- 通知/公告类：背景/目的、工作安排、具体要求、联系方式\n\n"
        "三、 输出格式示例\n"
        "# [政策标题]\n\n"
        "> **核心摘要**：[智能提炼政策核心，如：明确了数据出境的安全评估标准，自2025年起实施]\n\n"
        "---\n\n"
        "### [动态标题1，如：适用范围 / 建设目标]\n"
        "* 要点一...\n"
        "* 要点二...\n\n"
        "### [动态标题2，如：主要任务 / 支持标准]\n"
        "* **关键点**：...\n"
        "* 细节描述...\n\n"
        "### [动态标题3，如：执行标准 / 申报要求]\n"
        "* ...\n"
        "...（根据内容自动延展）...\n\n"
        "### [动态标题N，如：实施时间 / 联系方式]\n"
        "* ...\n\n"
        "---\n\n"
        "要求：\n"
        "1. 保持 Markdown 格式纯净，无额外解释。\n"
        "2. 标题名称要简练准确（2-6个字）。\n"
        "3. 遇到原文中没有的信息，不要生造标题。\n"
        "4. 输出 JSON，字段包含：`mind_map`（上述 Markdown 正文）、`summary`（中文概要，必须 ≤55 字，超出必须自行截断到 55 字以内）。\n"
    )

    chat_request = GeminiChatRequest(
        # 指定轻量模型用于结构化格式化，避免影响其他接口默认模型
        model="gemini-2.5-flash",
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=request.content),
        ],
        stream=False,
    )

    try:
        logger.info("Gemini 政策格式化请求开始")
        def _parse_output(choice_message: Any) -> tuple[str, str]:
            raw_content_local = choice_message["content"]
            if not isinstance(raw_content_local, str):
                raw_content_local = str(raw_content_local)

            cleaned_content_local = raw_content_local.strip()
            if cleaned_content_local.startswith("```"):
                cleaned_content_local = cleaned_content_local.strip("`")
                if cleaned_content_local.lower().startswith("json"):
                    cleaned_content_local = cleaned_content_local[4:].lstrip("\n")
            try:
                parsed_local = json.loads(cleaned_content_local)
            except Exception:
                logger.error("Gemini 政策格式化输出非 JSON，原文: %s", raw_content_local)
                raise HTTPException(status_code=500, detail="模型输出解析失败：非 JSON 格式")

            mind_map_local = parsed_local.get("mind_map")
            summary_local = parsed_local.get("summary")
            if not mind_map_local or not summary_local:
                raise HTTPException(
                    status_code=500, detail="模型输出缺少 mind_map 或 summary 字段"
                )

            if not isinstance(summary_local, str):
                summary_local = str(summary_local)
            summary_local = summary_local.strip()
            return mind_map_local, summary_local

        completion = await gemini_chat_service.chat_completion(chat_request)
        choices = completion.choices or []
        if not choices or "content" not in choices[0].message:
            raise HTTPException(status_code=500, detail="未获取到模型输出内容")

        mind_map, summary = _parse_output(choices[0].message)

        if _count_chinese_and_digits(summary) > 55:
            logger.warning("summary 超长，准备重试生成: %s", summary)
            retry_request = GeminiChatRequest(
                model=chat_request.model,
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(
                        role="system",
                        content=(
                            "上一次 summary 超过 55 字。请重新生成，确保 summary 严格不超过 55 字，"
                            "mind_map 依旧输出完整 Markdown。只返回 JSON。"
                        ),
                    ),
                    ChatMessage(role="user", content=request.content),
                ],
                stream=False,
            )
            retry_completion = await gemini_chat_service.chat_completion(retry_request)
            retry_choices = retry_completion.choices or []
            if not retry_choices or "content" not in retry_choices[0].message:
                raise HTTPException(status_code=500, detail="重试未获取到模型输出内容")
            mind_map, summary = _parse_output(retry_choices[0].message)
            if _count_chinese_and_digits(summary) > 55:
                raise HTTPException(status_code=500, detail="summary 超过 55 字限制（重试后仍失败）")

        return PolicyFormatResponse(mind_map=mind_map, summary=summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Gemini 政策格式化失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gemini 政策格式化失败: {str(e)}")


