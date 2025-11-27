"""Gemini 聊天相关 Pydantic 数据模型."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息模型."""

    role: str = Field(..., description="消息角色，例如 system、user、assistant")
    content: Any = Field(
        ...,
        description=(
            "消息内容，可以是纯文本字符串，"
            "也可以是多模态内容数组（例如包含 text、image_url 等结构），"
            "以兼容 OpenAI / Gemini ChatCompletions 的多模态入参格式"
        ),
    )


class GeminiChatRequest(BaseModel):
    """Gemini 聊天请求模型（兼容 OpenAI ChatCompletions 的主要字段）."""

    model: Optional[str] = Field(
        default=None,
        description="模型名称，不传则使用配置中的 GEMINI_MODEL",
    )
    messages: List[ChatMessage] = Field(
        ...,
        description="多轮对话消息列表，按时间顺序排列",
    )
    stream: Optional[bool] = Field(
        default=True,
        description="是否开启流式输出，默认开启",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="采样温度",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="最大生成 token 数",
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="核采样参数",
    )
    stop: Optional[List[str]] = Field(
        default=None,
        description="停止词列表",
    )
    user: Optional[str] = Field(
        default=None,
        description="用户 ID，用于审计与限流",
    )

    model_config = {
        "extra": "allow",  # 允许透传未显式声明的字段到下游 Gemini
    }


class GeminiChatChoice(BaseModel):
    """Gemini 聊天单条选择结果."""

    index: int = Field(..., description="选项索引")
    message: Dict[str, Any] = Field(..., description="回复消息对象（兼容 OpenAI 格式）")
    finish_reason: Optional[str] = Field(
        default=None,
        description="结束原因，如 stop、length 等",
    )


class GeminiChatCompletionResponse(BaseModel):
    """Gemini 聊天完整响应（非流式）."""

    id: str = Field(..., description="回答 ID")
    model: str = Field(..., description="实际使用的模型名称")
    object: str = Field(..., description="对象类型，一般为 chat.completion")
    created: int = Field(..., description="创建时间戳（秒）")
    choices: List[GeminiChatChoice] = Field(..., description="回答选项列表")
    usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="token 计费信息",
    )


