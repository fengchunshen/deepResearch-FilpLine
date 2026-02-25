"""产业链生成 API 端点."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import datetime
from app.models.industry_chain import (
    IndustryChainAnalyzeRequest,
    IndustryChainGenerateRequest,
    IndustryChainEvent,
    IndustryChainEventType,
)
from app.services.industry_chain_service import industry_chain_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sse_wrapper(event_iter):
    """统一的 SSE 事件包装器。"""
    seq = 0
    try:
        async for event in event_iter:
            seq = max(seq, event.sequence_number)
            yield f"event: {event.event_type.value}\n"
            yield f"data: {event.model_dump_json()}\n\n"
    except Exception as e:
        logger.error("产业链流式执行失败: %s", e, exc_info=True)
        seq += 1
        error_event = IndustryChainEvent(
            event_type=IndustryChainEventType.ERROR,
            timestamp=datetime.now().isoformat(),
            sequence_number=seq,
            data={},
            message="服务内部错误，请稍后重试",
        )
        yield f"event: {error_event.event_type.value}\n"
        yield f"data: {error_event.model_dump_json()}\n\n"


def _sse_response(event_iter) -> StreamingResponse:
    return StreamingResponse(
        _sse_wrapper(event_iter),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/analyze/stream")
async def analyze_industry_chain_stream(request_data: IndustryChainAnalyzeRequest):
    """
    产业链分析流式接口（第一步）.

    根据用户描述搜索网络信息，生成产业链理解文本供用户确认。

    事件序列：started → searching → analyzing → completed
    completed 事件 data 包含 understanding（理解文本）和 sources（来源列表）。
    """
    logger.info("产业链分析请求: query=%r", request_data.query)
    return _sse_response(industry_chain_service.analyze_stream(request_data))


@router.post("/generate/stream")
async def generate_industry_chain_stream(request_data: IndustryChainGenerateRequest):
    """
    产业链生成流式接口（第二步）.

    基于用户确认后的产业链理解文本，生成多层级嵌套树形产业链结构。

    事件序列：started → generating → completed
    completed 事件 data 包含 tree（产业链树形结构）。
    """
    logger.info("产业链生成请求: query=%r", request_data.query)
    return _sse_response(industry_chain_service.generate_stream(request_data))
