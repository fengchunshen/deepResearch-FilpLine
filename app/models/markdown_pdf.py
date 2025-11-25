"""Markdown 转 PDF 相关的 Pydantic 数据模型."""
from typing import Optional

from pydantic import BaseModel, Field


class MarkdownToPdfRequest(BaseModel):
    """Markdown 转 PDF 请求模型."""

    markdown: str = Field(..., description="Markdown 文本内容")
    filename: Optional[str] = Field(
        default=None,
        description="可选的 PDF 文件名（不包含扩展名或包含 .pdf 均可）",
    )


class MarkdownToPdfResponse(BaseModel):
    """Markdown 转 PDF 响应模型."""

    success: bool = Field(..., description="是否成功")
    pdf_path: str = Field(..., description="生成的 PDF 文件绝对路径")
    message: str = Field(..., description="提示消息")


