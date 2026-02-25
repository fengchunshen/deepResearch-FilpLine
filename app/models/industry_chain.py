"""产业链生成的 Pydantic 数据模型。"""
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class IndustryChainAnalyzeRequest(BaseModel):
    """产业链分析请求模型（第一步：搜索+生成理解）。"""
    query: str = Field(..., description="产业链描述/关键词", min_length=1, max_length=2000)


class IndustryChainGenerateRequest(BaseModel):
    """产业链生成/修改请求模型（第二步：生成或基于反馈修改产业链树）。"""
    query: str = Field(..., description="产业链描述/关键词", min_length=1, max_length=2000)
    understanding: str = Field(..., description="用户确认后的产业链理解文本", min_length=1, max_length=20000)
    tree: Optional[dict] = Field(default=None, description="当前产业链树形结构，修改模式时必传")
    feedback: Optional[str] = Field(default=None, description="用户的修改意见", max_length=5000)


class IndustryChainEventType(str, Enum):
    """产业链 SSE 事件类型。"""
    STARTED = "started"
    SEARCHING = "searching"          # 保留，兼容旧前端
    KEYWORD_GENERATED = "keyword_generated"
    WEB_SEARCHING = "web_searching"
    WEB_RESULT = "web_result"
    PROGRESS = "progress"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"


class IndustryChainEvent(BaseModel):
    """产业链 SSE 事件统一结构。"""
    event_type: IndustryChainEventType = Field(..., description="事件类型")
    timestamp: str = Field(..., description="时间戳（ISO 8601格式）")
    sequence_number: int = Field(..., description="事件序号")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据载荷")
    message: Optional[str] = Field(default=None, description="描述性消息")


class IndustryChainNode(BaseModel):
    """产业链树节点（递归结构）。"""
    name: str = Field(..., description="节点名称")
    description: str = Field(default="", description="节点描述")
    type: str = Field(default="", description="节点类型，如 上游/中游/下游/细分领域")
    children: List["IndustryChainNode"] = Field(default_factory=list, description="子节点列表")


IndustryChainNode.model_rebuild()


class IndustryChainTree(BaseModel):
    """产业链树顶层结构（LLM 结构化输出）。"""
    industry_name: str = Field(..., description="产业名称")
    description: str = Field(default="", description="产业概述")
    children: List[IndustryChainNode] = Field(default_factory=list, description="一级子节点列表")
