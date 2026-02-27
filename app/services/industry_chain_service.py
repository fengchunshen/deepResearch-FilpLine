"""产业链生成服务。"""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import AsyncGenerator

from app.core.config import settings
from app.models.industry_chain import (
    IndustryChainAnalyzeRequest,
    IndustryChainEvent,
    IndustryChainEventType,
    IndustryChainGenerateRequest,
    IndustryChainTree,
)
from app.services.deepsearch_engine import bocha_web_search, invoke_llm_with_fallback

logger = logging.getLogger(__name__)

KEYWORD_PROMPT = """你是一个产业链研究专家。根据用户描述的产业，生成 5 个搜索关键词，用于全面了解该产业链。

要求：
1. 每个关键词必须从不同维度切入，覆盖以下 5 个方面：
   - 上下游结构与核心环节
   - 关键技术路线或核心材料/部件
   - 市场规模与竞争格局
   - 头部企业与供应商
   - 政策趋势或行业动态
2. 关键词要具体，体现该产业的专业术语，避免泛泛的"产业链 上下游"式表述
3. 关键词之间搜索结果重叠度尽量低

直接返回一个 JSON 数组，不要包含其他内容。

示例（半导体产业）：
["半导体 晶圆代工 封装测试 产业环节", "EUV光刻机 先进制程 技术路线", "全球芯片 市场份额 竞争格局 2024", "台积电 三星 英特尔 晶圆产能", "芯片 自主可控 政策补贴 发展趋势"]

用户描述：{query}"""

UNDERSTANDING_PROMPT = """你是一个产业链研究专家。根据以下搜索资料，为"{query}"产业链撰写一份结构化的产业链分析理解。

要求：
1. 概述该产业的整体情况（2-3句话）
2. 分别描述上游、中游、下游各环节的主要构成，包括关键细分领域和代表性企业/技术
3. 指出该产业链的核心驱动因素和发展趋势
4. 语言简洁专业，便于后续生成产业链树形结构

请直接输出分析文本，不要使用 JSON 格式。

搜索资料：
{search_context}"""

CHAIN_PROMPT = """你是一个产业链分析专家。根据以下产业链分析理解，为"{query}"生成一个完整的多层级产业链树形结构。

产业链分析理解：
{understanding}

要求：
1. 第一层通常为：上游（原材料/核心部件）、中游（制造/集成）、下游（应用/终端市场）
2. 每层下面细分具体的子领域，至少 2-3 层嵌套
3. 每个节点包含 name（名称）、description（简短描述）、type（节点类型）、children（子节点数组）
4. type 字段使用：上游、中游、下游、细分领域、原材料、核心部件、制造、应用 等标签
5. 确保结构完整、层次清晰，覆盖该产业的主要环节

请严格按以下 JSON 格式输出，不要包含其他内容：
{{
  "industry_name": "产业名称",
  "description": "产业概述",
  "children": [
    {{
      "name": "上游",
      "description": "...",
      "type": "上游",
      "children": [
        {{"name": "子领域", "description": "...", "type": "细分领域", "children": []}}
      ]
    }}
  ]
}}"""

REFINE_KEYWORD_PROMPT = """你是一个产业链研究专家。用户对"{query}"产业链结构提出了修改意见，请根据修改意见生成 2-3 个搜索关键词，用于补充相关信息。

用户修改意见：{feedback}

要求：
1. 关键词要紧扣用户的修改意见，不要生成泛泛的产业链关键词
2. 关键词要具体，便于搜索到用户想补充的细分领域、企业、技术等信息

直接返回一个 JSON 数组，不要包含其他内容。"""

REFINE_PROMPT = """你是一个产业链分析专家。用户对当前的"{query}"产业链结构不满意，请根据用户的修改意见和补充搜索资料调整产业链树。

当前产业链结构：
{current_tree}

用户修改意见：
{feedback}

补充搜索资料：
{search_context}

要求：
1. 仅根据用户意见做针对性修改，不要大幅重构未提及的部分
2. 优先使用搜索资料中的真实信息（企业名、技术名、数据等），避免凭空编造
3. 保持原有结构的合理部分不变
4. 每个节点包含 name、description、type、children 字段
5. 输出格式与原结构一致

请严格按以下 JSON 格式输出，不要包含其他内容：
{{
  "industry_name": "产业名称",
  "description": "产业概述",
  "children": [
    {{
      "name": "上游",
      "description": "...",
      "type": "上游",
      "children": [
        {{"name": "子领域", "description": "...", "type": "细分领域", "children": []}}
      ]
    }}
  ]
}}"""


ENTERPRISE_EXTRACT_PROMPT = """你是一个产业链研究专家。根据以下搜索资料，提取与"{node_name}"节点相关的企业信息。

产业链背景：{chain_definition}

搜索资料：
{search_context}

要求：
1. 提取与该产业链节点直接相关的企业，包括上下游供应商、制造商、服务商等
2. 每个企业包含以下字段：
   - name: 企业全称（必须使用工商注册的完整公司名称，如"宁德时代新能源科技股份有限公司"，不要使用简称如"宁德时代"）
   - description: 一句话简介（主营业务）
   - role: 在该产业链节点中的角色/定位
3. 只提取搜索资料中明确提到的真实企业，不要编造。如果搜索资料中只有简称，请根据你的知识补全为工商注册全称
4. 按相关性排序，最多返回 15 家企业
5. 如果搜索资料中没有找到相关企业，返回空数组 []

请严格按以下 JSON 数组格式输出，不要包含其他内容：
[
  {{"name": "企业名称", "description": "企业简介", "role": "产业链角色"}}
]"""


class IndustryChainService:
    """产业链生成服务（单例）。"""

    def _make_event(
        self, event_type: IndustryChainEventType, seq: int,
        data: dict = None, message: str = None,
    ) -> IndustryChainEvent:
        return IndustryChainEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            sequence_number=seq,
            data=data or {},
            message=message,
        )

    def _make_progress_event(
        self, seq: int, step_name: str,
        completed_steps: int, total_steps: int, percentage: int,
    ) -> IndustryChainEvent:
        """构造 PROGRESS 事件，data 结构与 DeepSearch 的 ProgressEvent 一致。"""
        return self._make_event(
            IndustryChainEventType.PROGRESS, seq,
            data={
                "step_name": step_name,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "percentage": percentage,
            },
            message=step_name,
        )

    async def _search_one(self, keyword: str, count: int = 8) -> tuple[str, dict, Exception | None]:
        """包装 bocha_web_search，返回 (keyword, result, error) 元组，内部捕获异常避免丢失 keyword。"""
        try:
            result = await bocha_web_search(keyword, count=count)
            return (keyword, result, None)
        except Exception as e:
            logger.warning("搜索关键词 %r 失败: %s", keyword, e)
            return (keyword, {}, e)

    @staticmethod
    def _extract_json_object(text: str) -> str:
        """从 LLM 返回文本中健壮地提取 JSON 对象字符串。"""
        # 优先尝试 markdown 代码块
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
        if m:
            return m.group(1)
        # 回退：用括号配对找最外层 {}
        start = text.find("{")
        if start == -1:
            raise ValueError("LLM 未返回有效的 JSON 产业链结构")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        raise ValueError("LLM 返回的 JSON 括号不匹配")

    @staticmethod
    def _extract_json_array(text: str) -> str:
        """从 LLM 返回文本中提取 JSON 数组字符串。"""
        m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", text)
        if m:
            return m.group(1)
        start = text.find("[")
        if start == -1:
            raise ValueError("LLM 未返回有效的 JSON 数组")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        raise ValueError("LLM 返回的 JSON 数组括号不匹配")

    async def _generate_keywords(self, query: str) -> list[str]:
        """用 LLM 从用户描述生成搜索关键词。"""
        prompt = KEYWORD_PROMPT.format(query=query)
        default_keywords = [
            f"{query} 产业链 核心环节 上下游",
            f"{query} 关键技术 核心材料",
            f"{query} 市场规模 竞争格局",
            f"{query} 头部企业 供应商",
            f"{query} 政策趋势 行业动态",
        ]
        try:
            result = await invoke_llm_with_fallback(
                invoke_func=lambda llm: llm.ainvoke(prompt),
                node_name="industry_chain_keywords",
                gemini_model=settings.GEMINI_MODEL,
                temperature=0.7,
            )
            text = result.content if hasattr(result, "content") else str(result)
            # 提取 JSON 数组
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                keywords = json.loads(text[start:end + 1])
                if isinstance(keywords, list) and len(keywords) > 0:
                    return [str(k) for k in keywords[:5]]
            return default_keywords
        except Exception as e:
            logger.warning("关键词生成失败，使用默认关键词: %s", e)
            return default_keywords

    async def analyze_stream(
        self, request: IndustryChainAnalyzeRequest,
    ) -> AsyncGenerator[IndustryChainEvent, None]:
        """第一步：搜索+生成产业链理解，yield 细粒度 SSE 事件。"""
        seq = 0
        query = request.query

        try:
            # 1. STARTED
            seq += 1
            yield self._make_event(
                IndustryChainEventType.STARTED, seq,
                data={"query": query},
                message=f"开始分析产业链: {query}",
            )

            # 2. PROGRESS — 正在生成关键词
            seq += 1
            yield self._make_progress_event(seq, "正在生成搜索关键词", 0, 5, 10)

            # 3. 生成搜索关键词
            keywords = await self._generate_keywords(query)

            # 4. KEYWORD_GENERATED
            seq += 1
            yield self._make_event(
                IndustryChainEventType.KEYWORD_GENERATED, seq,
                data={"keywords": keywords},
                message=f"已生成 {len(keywords)} 个搜索关键词",
            )

            # 5. PROGRESS — 开始搜索
            seq += 1
            yield self._make_progress_event(seq, "开始搜索网络信息", 1, 5, 20)

            # 6. 并行搜索，逐个返回结果
            all_webpages = []
            all_formatted = []
            keyword_count = len(keywords)
            tasks = [asyncio.ensure_future(self._search_one(kw)) for kw in keywords]
            completed = 0

            for coro in asyncio.as_completed(tasks):
                keyword, res, err = await coro
                completed += 1
                if err is not None:
                    seq += 1
                    yield self._make_event(
                        IndustryChainEventType.WEB_RESULT, seq,
                        data={"keyword": keyword, "result_count": 0},
                        message=f"关键词「{keyword}」搜索失败",
                    )
                else:
                    webpages = res.get("webpages", [])
                    text = res.get("formatted_text", "")
                    all_webpages.extend(webpages)
                    if text and text != "未找到相关结果。":
                        all_formatted.append(text)
                    sources = [
                        {"title": p.get("name", ""), "url": p.get("url", ""), "siteName": p.get("siteName", "")}
                        for p in webpages if p.get("url")
                    ]
                    seq += 1
                    yield self._make_event(
                        IndustryChainEventType.WEB_RESULT, seq,
                        data={"keyword": keyword, "result_count": len(webpages), "sources": sources},
                        message=f"关键词「{keyword}」搜索到 {len(webpages)} 条结果",
                    )
                # 搜索进度 20% → 60%
                pct = 20 + int(40 * completed / keyword_count)
                seq += 1
                yield self._make_progress_event(
                    seq, f"已完成 {completed}/{keyword_count} 个关键词搜索",
                    2, 5, pct,
                )

            source_count = len(all_webpages)
            search_context = "\n\n".join(all_formatted) if all_formatted else "未找到相关搜索结果。"

            # 7. PROGRESS — 搜索完成
            seq += 1
            yield self._make_progress_event(seq, "搜索完成，正在整合资料", 3, 5, 60)

            # 8. ANALYZING
            seq += 1
            yield self._make_event(
                IndustryChainEventType.ANALYZING, seq,
                data={"source_count": source_count},
                message=f"已获取 {source_count} 条搜索结果，正在生成产业链理解",
            )

            # 9. PROGRESS — 正在生成理解
            seq += 1
            yield self._make_progress_event(seq, "正在生成产业链理解", 4, 5, 75)

            # 10. LLM 生成产业链理解文本
            prompt = UNDERSTANDING_PROMPT.format(query=query, search_context=search_context[:15000])
            result = await invoke_llm_with_fallback(
                invoke_func=lambda llm: llm.ainvoke(prompt),
                node_name="industry_chain_analyze",
                gemini_model=settings.GEMINI_MODEL,
                temperature=0.3,
            )
            understanding = result.content if hasattr(result, "content") else str(result)

            # 11. 构建来源列表
            sources = []
            seen_urls = set()
            for page in all_webpages:
                url = page.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({
                        "title": page.get("name", ""),
                        "url": url,
                        "siteName": page.get("siteName", ""),
                    })

            # 12. PROGRESS — 分析完成
            seq += 1
            yield self._make_progress_event(seq, "分析完成", 5, 5, 100)

            # 13. COMPLETED
            seq += 1
            yield self._make_event(
                IndustryChainEventType.COMPLETED, seq,
                data={
                    "success": True,
                    "understanding": understanding,
                    "sources": sources,
                },
                message="产业链分析完成，请确认理解内容",
            )

        except Exception as e:
            logger.error("产业链分析失败: %s", e, exc_info=True)
            seq += 1
            yield self._make_event(
                IndustryChainEventType.ERROR, seq,
                data={},
                message="产业链分析失败，请稍后重试",
            )

    async def generate_stream(
        self, request: IndustryChainGenerateRequest,
    ) -> AsyncGenerator[IndustryChainEvent, None]:
        """第二步：生成或修改产业链树，yield SSE 事件。"""
        seq = 0
        query = request.query
        is_refine = request.tree is not None and request.feedback is not None

        try:
            # 1. STARTED
            seq += 1
            yield self._make_event(
                IndustryChainEventType.STARTED, seq,
                data={"query": query, "mode": "refine" if is_refine else "generate"},
                message=f"开始{'修改' if is_refine else '生成'}产业链结构: {query}",
            )

            # 2. 构造 prompt（refine 模式先搜索补充资料）
            max_attempts = 2
            tree = None
            last_error = None

            if is_refine:
                # 2a. 生成搜索关键词
                seq += 1
                yield self._make_progress_event(seq, "正在根据修改意见生成搜索关键词", 0, 4, 10)

                refine_kw_prompt = REFINE_KEYWORD_PROMPT.format(query=query, feedback=request.feedback)
                try:
                    kw_result = await invoke_llm_with_fallback(
                        invoke_func=lambda llm: llm.ainvoke(refine_kw_prompt),
                        node_name="industry_chain_refine_keywords",
                        gemini_model=settings.GEMINI_MODEL,
                        temperature=0.7,
                    )
                    kw_text = kw_result.content if hasattr(kw_result, "content") else str(kw_result)
                    kw_start = kw_text.find("[")
                    kw_end = kw_text.rfind("]")
                    if kw_start != -1 and kw_end != -1:
                        refine_keywords = [str(k) for k in json.loads(kw_text[kw_start:kw_end + 1])[:3]]
                    else:
                        refine_keywords = [f"{query} {request.feedback}"]
                except Exception as e:
                    logger.warning("修改关键词生成失败: %s", e)
                    refine_keywords = [f"{query} {request.feedback}"]

                seq += 1
                yield self._make_event(
                    IndustryChainEventType.KEYWORD_GENERATED, seq,
                    data={"keywords": refine_keywords},
                    message=f"已生成 {len(refine_keywords)} 个补充搜索关键词",
                )

                # 2b. 并行搜索
                seq += 1
                yield self._make_progress_event(seq, "正在搜索补充资料", 1, 4, 25)

                all_formatted = []
                kw_count = len(refine_keywords)
                tasks = [asyncio.ensure_future(self._search_one(kw)) for kw in refine_keywords]
                completed = 0

                for coro in asyncio.as_completed(tasks):
                    keyword, res, err = await coro
                    completed += 1
                    if err is not None:
                        seq += 1
                        yield self._make_event(
                            IndustryChainEventType.WEB_RESULT, seq,
                            data={"keyword": keyword, "result_count": 0},
                            message=f"关键词「{keyword}」补充搜索失败",
                        )
                    else:
                        webpages = res.get("webpages", [])
                        text = res.get("formatted_text", "")
                        if text and text != "未找到相关结果。":
                            all_formatted.append(text)
                        sources = [
                            {"title": p.get("name", ""), "url": p.get("url", ""), "siteName": p.get("siteName", "")}
                            for p in webpages if p.get("url")
                        ]
                        seq += 1
                        yield self._make_event(
                            IndustryChainEventType.WEB_RESULT, seq,
                            data={"keyword": keyword, "result_count": len(webpages), "sources": sources},
                            message=f"关键词「{keyword}」搜索完成",
                        )
                    pct = 25 + int(25 * completed / kw_count)
                    seq += 1
                    yield self._make_progress_event(
                        seq, f"已完成 {completed}/{kw_count} 个补充搜索", 1, 4, pct,
                    )

                search_context = "\n\n".join(all_formatted) if all_formatted else "未找到补充资料。"

                # 2c. 构造 refine prompt
                seq += 1
                yield self._make_progress_event(seq, "正在根据修改意见调整产业链结构", 2, 4, 55)

                current_tree_json = json.dumps(request.tree, ensure_ascii=False, indent=2)
                prompt = REFINE_PROMPT.format(
                    query=query, current_tree=current_tree_json,
                    feedback=request.feedback, search_context=search_context[:10000],
                )
            else:
                seq += 1
                yield self._make_event(
                    IndustryChainEventType.GENERATING, seq,
                    message="正在根据产业链理解生成树形结构",
                )
                prompt = CHAIN_PROMPT.format(query=query, understanding=request.understanding)

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await invoke_llm_with_fallback(
                        invoke_func=lambda llm: llm.ainvoke(prompt),
                        node_name="industry_chain_generate",
                        gemini_model=settings.GEMINI_MODEL,
                        temperature=0.3,
                    )
                    text = result.content if hasattr(result, "content") else str(result)
                    json_str = self._extract_json_object(text)
                    tree = IndustryChainTree.model_validate_json(json_str)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning("产业链 JSON 解析失败（第%d次），重试: %s", attempt, e)
                    else:
                        logger.error("产业链 JSON 解析失败（已重试%d次）: %s", max_attempts, e)

            if tree is None:
                raise ValueError(f"LLM 多次未返回有效的产业链结构: {last_error}")

            # 4. COMPLETED
            seq += 1
            yield self._make_event(
                IndustryChainEventType.COMPLETED, seq,
                data={
                    "success": True,
                    "tree": tree.model_dump(),
                },
                message="产业链生成完成",
            )

        except Exception as e:
            logger.error("产业链生成失败: %s", e, exc_info=True)
            seq += 1
            yield self._make_event(
                IndustryChainEventType.ERROR, seq,
                data={},
                message="产业链生成失败，请稍后重试",
            )


    async def search_related_enterprises(
        self, node_name: str, chain_definition: str,
    ) -> list[dict]:
        """根据产业链节点搜索关联企业列表。"""
        # 1. 构造搜索关键词
        queries = [
            f"{node_name} 代表企业 龙头公司",
            f"{node_name} {chain_definition[:50]} 相关企业 供应商",
            f"{node_name} 行业企业 市场份额 竞争格局",
        ]

        # 2. 并行搜索
        tasks = [asyncio.ensure_future(self._search_one(kw)) for kw in queries]
        all_formatted = []
        for coro in asyncio.as_completed(tasks):
            keyword, res, err = await coro
            if err is not None:
                logger.warning("企业搜索关键词 %r 失败: %s", keyword, err)
                continue
            text = res.get("formatted_text", "")
            if text and text != "未找到相关结果。":
                all_formatted.append(text)

        search_context = "\n\n".join(all_formatted) if all_formatted else "未找到相关搜索结果。"

        # 3. LLM 提取企业信息
        prompt = ENTERPRISE_EXTRACT_PROMPT.format(
            node_name=node_name,
            chain_definition=chain_definition,
            search_context=search_context[:15000],
        )

        max_attempts = 2
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = await invoke_llm_with_fallback(
                    invoke_func=lambda llm: llm.ainvoke(prompt),
                    node_name="industry_chain_enterprises",
                    gemini_model=settings.GEMINI_MODEL,
                    temperature=0.3,
                )
                text = result.content if hasattr(result, "content") else str(result)
                json_str = self._extract_json_array(text)
                enterprises = json.loads(json_str)
                if not isinstance(enterprises, list):
                    raise ValueError("LLM 返回的不是数组")
                return enterprises[:15]
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    logger.warning("企业提取 JSON 解析失败（第%d次），重试: %s", attempt, e)
                else:
                    logger.error("企业提取 JSON 解析失败（已重试%d次）: %s", max_attempts, e)

        raise ValueError(f"LLM 多次未返回有效的企业列表: {last_error}")


industry_chain_service = IndustryChainService()
