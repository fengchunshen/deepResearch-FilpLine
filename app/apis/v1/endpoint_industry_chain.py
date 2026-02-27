"""产业链生成 API 端点."""
from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from app.models.industry_chain import (
    IndustryChainAnalyzeRequest,
    IndustryChainGenerateRequest,
    IndustryChainEvent,
    IndustryChainEventType,
    EnterpriseSearchRequest,
    EnterpriseSearchResponse,
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


@router.post(
    "/analyze/stream",
    summary="产业链分析",
    description="根据用户描述搜索网络信息，生成产业链理解文本供用户确认。事件序列：started → searching → analyzing → completed。",
)
async def analyze_industry_chain_stream(request_data: IndustryChainAnalyzeRequest):
    logger.info("产业链分析请求: query=%r", request_data.query)
    return _sse_response(industry_chain_service.analyze_stream(request_data))


@router.post(
    "/generate/stream",
    summary="产业链生成",
    description=(
        "支持两种模式：\n\n"
        "**生成模式**（首次）：传入 query + understanding，生成多层级嵌套树形产业链结构。"
        "事件序列：started → generating → completed。\n\n"
        "**修改模式**（迭代）：额外传入 tree + feedback，根据用户修改意见搜索补充资料后调整现有产业链树。"
        "事件序列：started → progress → keyword_generated → web_result → progress → completed。\n\n"
        "completed 事件 data 包含 tree（产业链树形结构，含 industry_name / description / children）。"
    ),
)
async def generate_industry_chain_stream(request_data: IndustryChainGenerateRequest):
    logger.info("产业链生成请求: query=%r", request_data.query)
    return _sse_response(industry_chain_service.generate_stream(request_data))


@router.post(
    "/search-enterprises",
    response_model=EnterpriseSearchResponse,
    summary="搜索产业链节点关联企业",
    description="根据产业链节点名称和产业链介绍，通过网络搜索和AI分析，返回相关企业列表。",
)
async def search_related_enterprises(request_data: EnterpriseSearchRequest) -> EnterpriseSearchResponse:
    try:
        logger.info("企业搜索请求: node_name=%r", request_data.node_name)
        enterprises = await industry_chain_service.search_related_enterprises(
            request_data.node_name,
            request_data.chain_definition,
        )
        return EnterpriseSearchResponse(
            success=True,
            node_name=request_data.node_name,
            enterprises=enterprises,
            message=f"找到 {len(enterprises)} 家相关企业",
        )
    except Exception as e:
        logger.error("企业搜索失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="企业搜索失败，请稍后重试",
        )
