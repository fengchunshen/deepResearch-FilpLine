"""Markdown 工具 API 端点 - 提供 Markdown 转 PDF 功能."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.apis.deps import get_api_key
from app.models.markdown_pdf import MarkdownToPdfRequest, MarkdownToPdfResponse
from app.services.markdown_pdf_service import markdown_pdf_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/markdown-to-pdf", response_model=MarkdownToPdfResponse)
async def markdown_to_pdf(
    request: MarkdownToPdfRequest,
    api_key: str = Depends(get_api_key),
) -> MarkdownToPdfResponse:
    """
    将 Markdown 文本转换为 PDF 文件.

    Args:
        request: 包含 Markdown 文本和可选文件名的请求对象
        api_key: API 密钥（通过依赖注入）

    Returns:
        MarkdownToPdfResponse: 包含生成的 PDF 路径的响应

    Raises:
        HTTPException: 当请求参数无效或转换失败时
    """
    try:
        pdf_path = await markdown_pdf_service.markdown_to_pdf(
            markdown_text=request.markdown,
            filename=request.filename,
        )
        return MarkdownToPdfResponse(
            success=True,
            pdf_path=pdf_path,
            message="Markdown 转 PDF 成功",
        )
    except ValueError as e:
        logger.error(f"Markdown 转 PDF 参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Markdown 转 PDF 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Markdown 转 PDF 失败: {str(e)}",
        )


