"""H5移动端 API 端点."""
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.apis.deps import get_api_key
from app.core.config import settings
from app.services.fastgpt_service import fastgpt_service
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class PolicyInterpretRequest(BaseModel):
    """政策解读请求模型."""
    policy_name: str  # 政策名称
    chat_id: Optional[str] = None  # 会话 ID（可选）


class CompanyInfo(BaseModel):
    """企业基本信息模型."""
    companyName: str  # 企业名称
    companyScale: Optional[str] = None  # 企业规模
    companyCategory: Optional[List[str]] = []  # 企业类别
    industry: Optional[str] = None  # 所属行业
    businessScope: Optional[str] = None  # 经营范围
    otherInformation: Optional[str] = None  # 其他信息汇总


class CompanyDetail(BaseModel):
    """企业详细信息模型."""
    companyName: str  # 企业名称
    scale: Optional[str] = None  # 企业规模
    industry: Optional[str] = None  # 所属行业
    category: Optional[List[str]] = []  # 企业类别
    businessScope: Optional[str] = None  # 经营范围
    ipCoreTech: Optional[str] = None  # 知识产权/核心技术
    certificatesHonors: Optional[str] = None  # 资质证书/荣誉
    policyNeeds: Optional[str] = None  # 政策需求
    otherInfo: Optional[str] = None  # 其他补充说明


class PolicyGuideRequest(BaseModel):
    """政策申报指南请求模型."""
    policy_name: str  # 政策名称
    policy_level: str  # 政策级别（国家级/市级/区级/园区）
    policy_summary: Optional[str] = None  # 政策摘要（可选）
    company_info: Optional[CompanyInfo] = None  # 企业基本信息
    company_detail: Optional[CompanyDetail] = None  # 企业详细信息
    chat_id: Optional[str] = None  # 会话 ID（可选）


class ChainNodeAnalyzeRequest(BaseModel):
    """产业链节点分析请求模型."""
    node_name: str  # 节点名称
    chat_id: Optional[str] = None  # 会话 ID（可选）


class SimpleCompanyQueryRequest(BaseModel):
    """企业简单查询请求模型."""
    companyName: str  # 企业名称（必填）
    companyScale: Optional[str] = None  # 企业规模
    companyCategory: Optional[List[str]] = []  # 企业类别列表
    industry: Optional[str] = None  # 行业
    revenueLastYear: Optional[Any] = None  # 去年营收
    businessScope: Optional[str] = None  # 经营范围
    otherInformation: Optional[str] = None  # 其他信息


class TianyanchaCompanyItem(BaseModel):
    """天眼查企业信息项."""
    id: Optional[int] = None  # 公司ID
    name: Optional[str] = None  # 公司名称
    type: Optional[int] = None  # 类型
    companyType: Optional[int] = None  # 公司类型
    base: Optional[str] = None  # 所在地
    legalPersonName: Optional[str] = None  # 法人代表
    regCapital: Optional[str] = None  # 注册资本
    estiblishTime: Optional[str] = None  # 成立日期
    regStatus: Optional[str] = None  # 经营状态
    creditCode: Optional[str] = None  # 统一社会信用代码
    regNumber: Optional[str] = None  # 注册号
    orgNumber: Optional[str] = None  # 组织机构代码
    matchType: Optional[str] = None  # 匹配类型


class TianyanchaSearchResponse(BaseModel):
    """天眼查搜索响应模型."""
    total: int = 0  # 总数
    items: List[TianyanchaCompanyItem] = []  # 企业列表


class TianyanchaBaseInfoResponse(BaseModel):
    """天眼查企业基本信息响应模型."""
    id: Optional[int] = None  # 公司ID
    name: Optional[str] = None  # 公司名称
    type: Optional[int] = None  # 类型
    companyOrgType: Optional[str] = None  # 企业类型
    estiblishTime: Optional[str] = None  # 成立日期
    regStatus: Optional[str] = None  # 经营状态
    regCapital: Optional[str] = None  # 注册资本
    legalPersonName: Optional[str] = None  # 法人代表
    regNumber: Optional[str] = None  # 工商注册号
    creditCode: Optional[str] = None  # 统一社会信用代码
    orgNumber: Optional[str] = None  # 组织机构代码
    taxNumber: Optional[str] = None  # 纳税人识别号
    regLocation: Optional[str] = None  # 注册地址
    regInstitute: Optional[str] = None  # 登记机关
    businessScope: Optional[str] = None  # 经营范围
    industry: Optional[str] = None  # 行业
    staffNumRange: Optional[str] = None  # 人员规模
    socialStaffNum: Optional[int] = None  # 参保人数
    base: Optional[str] = None  # 省份简称
    city: Optional[str] = None  # 城市
    district: Optional[str] = None  # 区县
    approvedTime: Optional[str] = None  # 核准日期
    historyNames: Optional[str] = None  # 曾用名
    bondName: Optional[str] = None  # 股票名称
    bondNum: Optional[str] = None  # 股票号
    bondType: Optional[str] = None  # 股票类型
    actualCapital: Optional[str] = None  # 实缴资本


class TianyanchaPatentItem(BaseModel):
    """天眼查专利信息项."""
    id: Optional[int] = None  # 专利ID
    patentName: Optional[str] = None  # 专利名称
    patentNum: Optional[str] = None  # 申请号
    applicationPublishNum: Optional[str] = None  # 申请公布号
    patentType: Optional[str] = None  # 专利类型
    patentStatus: Optional[str] = None  # 专利状态
    applicationTime: Optional[str] = None  # 申请日期
    pubDate: Optional[str] = None  # 公布日期
    applicantname: Optional[str] = None  # 申请人
    inventor: Optional[str] = None  # 发明人
    agent: Optional[str] = None  # 代理人
    agency: Optional[str] = None  # 代理机构
    address: Optional[str] = None  # 地址
    abstracts: Optional[str] = None  # 摘要
    mainCatNum: Optional[str] = None  # 主分类号
    cat: Optional[str] = None  # 分类


class TianyanchaPatentResponse(BaseModel):
    """天眼查专利列表响应模型."""
    total: int = 0  # 总数
    items: List[TianyanchaPatentItem] = []  # 专利列表


class TianyanchaCertificateDetailItem(BaseModel):
    """天眼查资质证书详情项."""
    title: Optional[str] = None  # 标题
    content: Optional[str] = None  # 内容


class TianyanchaCertificateItem(BaseModel):
    """天眼查资质证书信息项."""
    id: Optional[str] = None  # 证书ID
    certNo: Optional[str] = None  # 证书编号
    certificateName: Optional[str] = None  # 证书名称
    certificateType: Optional[str] = None  # 证书类型
    startDate: Optional[str] = None  # 发证日期
    endDate: Optional[str] = None  # 到期日期
    detail: Optional[List[TianyanchaCertificateDetailItem]] = []  # 详情列表


class TianyanchaCertificateResponse(BaseModel):
    """天眼查资质证书列表响应模型."""
    total: int = 0  # 总数
    items: List[TianyanchaCertificateItem] = []  # 证书列表


@router.get("/health")
async def health_check(api_key: str = Depends(get_api_key)):
    """
    H5移动端服务健康检查.

    Returns:
        健康状态信息
    """
    return {"status": "healthy", "service": "h5"}


@router.post("/policy/interpret/stream")
async def policy_interpret_stream(
    request: PolicyInterpretRequest,
    api_key: str = Depends(get_api_key),
):
    """
    政策解读流式接口 - 调用 FastGPT 进行政策解读.

    Args:
        request: 政策解读请求
        api_key: API 密钥

    Returns:
        StreamingResponse: 流式 SSE 响应
    """
    logger.info("政策解读流式请求: policy_name=%s, chat_id=%s", request.policy_name, request.chat_id)

    # 拼接问题
    question = f"{request.policy_name}的主要内容是什么"

    async def event_generator():
        try:
            async for chunk in fastgpt_service.chat_stream(
                message=question,
                chat_id=request.chat_id,
                api_url=settings.FASTGPT_POLICY_API_URL,
                api_key=settings.FASTGPT_POLICY_API_KEY,
            ):
                yield chunk
        except Exception as e:
            logger.error("政策解读流式请求失败: %s", e, exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/policy/guide/stream")
async def policy_guide_stream(
    request: PolicyGuideRequest,
    api_key: str = Depends(get_api_key),
):
    """
    政策申报指南流式接口 - 根据政策和企业信息生成申报指南.

    Args:
        request: 政策申报指南请求
        api_key: API 密钥

    Returns:
        StreamingResponse: 流式 SSE 响应
    """
    logger.info(
        "政策申报指南流式请求: policy_name=%s, policy_level=%s, chat_id=%s",
        request.policy_name, request.policy_level, request.chat_id
    )

    # 构建问题内容
    question_parts = [
        f"政策名称：{request.policy_name}",
        f"政策级别：{request.policy_level}",
    ]

    if request.policy_summary:
        question_parts.append(f"政策摘要：{request.policy_summary}")

    # 添加企业基本信息
    if request.company_info:
        info = request.company_info
        company_info_text = f"""
企业基本信息：
- 企业名称：{info.companyName}
- 企业规模：{info.companyScale or '未提供'}
- 企业类别：{', '.join(info.companyCategory) if info.companyCategory else '未提供'}
- 所属行业：{info.industry or '未提供'}
- 经营范围：{info.businessScope or '未提供'}
- 其他信息：{info.otherInformation or '未提供'}"""
        question_parts.append(company_info_text)

    # 添加企业详细信息
    if request.company_detail:
        detail = request.company_detail
        company_detail_text = f"""
企业详细信息：
- 企业名称：{detail.companyName}
- 企业规模：{detail.scale or '未提供'}
- 所属行业：{detail.industry or '未提供'}
- 企业类别：{', '.join(detail.category) if detail.category else '未提供'}
- 经营范围：{detail.businessScope or '未提供'}
- 知识产权/核心技术：{detail.ipCoreTech or '未提供'}
- 资质证书/荣誉：{detail.certificatesHonors or '未提供'}
- 政策需求：{detail.policyNeeds or '未提供'}
- 其他补充：{detail.otherInfo or '未提供'}"""
        question_parts.append(company_detail_text)

    question_parts.append("\n请根据以上政策和企业信息，生成详细的政策申报指南。")
    question = "\n".join(question_parts)

    async def event_generator():
        try:
            async for chunk in fastgpt_service.chat_stream(
                message=question,
                chat_id=request.chat_id,
                api_url=settings.FASTGPT_POLICY_GUIDE_API_URL,
                api_key=settings.FASTGPT_POLICY_GUIDE_API_KEY,
            ):
                yield chunk
        except Exception as e:
            logger.error("政策申报指南流式请求失败: %s", e, exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chain/node/analyze/stream")
async def chain_node_analyze_stream(
    request: ChainNodeAnalyzeRequest,
    api_key: str = Depends(get_api_key),
):
    """
    产业链节点分析流式接口 - 分析产业链节点信息.

    Args:
        request: 产业链节点分析请求
        api_key: API 密钥

    Returns:
        StreamingResponse: 流式 SSE 响应
    """
    logger.info("产业链节点分析流式请求: node_name=%s, chat_id=%s", request.node_name, request.chat_id)

    question = request.node_name

    async def event_generator():
        try:
            async for chunk in fastgpt_service.chat_stream(
                message=question,
                chat_id=request.chat_id,
                api_url=settings.FASTGPT_NODE_ANALYZE_API_URL,
                api_key=settings.FASTGPT_NODE_ANALYZE_API_KEY,
            ):
                yield chunk
        except Exception as e:
            logger.error("产业链节点分析流式请求失败: %s", e, exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/company/query/simple")
async def simple_company_query(
    request: SimpleCompanyQueryRequest,
    api_key: str = Depends(get_api_key),
):
    """
    企业简单查询接口 - 根据企业信息查询相关政策文件.

    Args:
        request: 企业查询请求
        api_key: API 密钥

    Returns:
        包含相关政策文件列表的响应
    """
    # 参数校验
    if not request.companyName or not request.companyName.strip():
        raise HTTPException(status_code=400, detail="企业名称不能为空")

    logger.info("企业简单查询请求: companyName=%s", request.companyName)

    # 构建请求数据
    request_data = {
        "companyName": request.companyName,
        "companyScale": request.companyScale,
        "companyCategory": request.companyCategory,
        "industry": request.industry,
        "revenueLastYear": request.revenueLastYear,
        "businessScope": request.businessScope,
        "otherInformation": request.otherInformation,
    }

    try:
        # 调用 FastGPT
        result = await fastgpt_service.call_fastgpt_simple(
            request_data=request_data,
            api_url=settings.FASTGPT_API_URL,
            api_key=settings.FASTGPT_API_KEY,
        )
        return result
    except Exception as e:
        logger.error("企业简单查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tianyancha/search")
async def tianyancha_search(
    word: str = Query(..., description="搜索关键词"),
    pageSize: int = Query(20, ge=1, le=20, description="每页条数，默认20，最大20"),
    pageNum: int = Query(1, ge=1, description="当前页数，默认第1页"),
    api_key: str = Depends(get_api_key),
):
    """
    天眼查企业搜索接口 - 通过关键词搜索企业列表.

    Args:
        word: 搜索关键词
        pageSize: 每页条数（默认20，最大20）
        pageNum: 当前页数（默认第1页）
        api_key: API 密钥

    Returns:
        企业列表，包含公司名称、ID、类型、成立日期、经营状态、统一社会信用代码等信息
    """
    if not word or not word.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    if not settings.TIANYANCHA_API_TOKEN:
        raise HTTPException(status_code=500, detail="天眼查 API Token 未配置")

    logger.info("天眼查企业搜索: word=%s, pageSize=%d, pageNum=%d", word, pageSize, pageNum)

    tianyancha_url = "http://open.api.tianyancha.com/services/open/search/2.0"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                tianyancha_url,
                params={"word": word, "pageSize": pageSize, "pageNum": pageNum},
                headers={"Authorization": settings.TIANYANCHA_API_TOKEN},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("error_code") != 0:
            logger.error("天眼查 API 返回错误: %s", data.get("reason", "未知错误"))
            raise HTTPException(status_code=500, detail=f"天眼查查询失败: {data.get('reason', '未知错误')}")

        result = data.get("result", {})
        return TianyanchaSearchResponse(
            total=result.get("total", 0),
            items=[TianyanchaCompanyItem(**item) for item in result.get("items", [])],
        )

    except httpx.HTTPStatusError as e:
        logger.error("天眼查 API HTTP 错误: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail=f"天眼查 API 请求失败: {str(e)}")
    except httpx.RequestError as e:
        logger.error("天眼查 API 请求错误: %s", e)
        raise HTTPException(status_code=500, detail=f"天眼查 API 连接失败: {str(e)}")
    except Exception as e:
        logger.error("天眼查企业搜索失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tianyancha/baseinfo")
async def tianyancha_baseinfo(
    keyword: str = Query(..., description="搜索关键字（公司名称、公司ID、注册号或社会统一信用代码）"),
    api_key: str = Depends(get_api_key),
):
    """
    天眼查企业基本信息接口 - 通过公司名称或ID获取企业基本信息.

    Args:
        keyword: 搜索关键字（公司名称、公司ID、注册号或社会统一信用代码）
        api_key: API 密钥

    Returns:
        企业基本信息，包含公司名称、类型、成立日期、经营状态、注册资本、法人等
    """
    if not keyword or not keyword.strip():
        raise HTTPException(status_code=400, detail="搜索关键字不能为空")

    if not settings.TIANYANCHA_API_TOKEN:
        raise HTTPException(status_code=500, detail="天眼查 API Token 未配置")

    logger.info("天眼查企业基本信息查询: keyword=%s", keyword)

    tianyancha_url = "http://open.api.tianyancha.com/services/open/ic/baseinfo/normal"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                tianyancha_url,
                params={"keyword": keyword},
                headers={"Authorization": settings.TIANYANCHA_API_TOKEN},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("error_code") != 0:
            logger.error("天眼查 API 返回错误: %s", data.get("reason", "未知错误"))
            raise HTTPException(status_code=500, detail=f"天眼查查询失败: {data.get('reason', '未知错误')}")

        result = data.get("result", {})

        # 转换时间戳为日期字符串
        def format_timestamp(ts):
            if ts:
                from datetime import datetime
                return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            return None

        return TianyanchaBaseInfoResponse(
            id=result.get("id"),
            name=result.get("name"),
            type=result.get("type"),
            companyOrgType=result.get("companyOrgType"),
            estiblishTime=format_timestamp(result.get("estiblishTime")),
            regStatus=result.get("regStatus"),
            regCapital=result.get("regCapital"),
            legalPersonName=result.get("legalPersonName"),
            regNumber=result.get("regNumber"),
            creditCode=result.get("creditCode"),
            orgNumber=result.get("orgNumber"),
            taxNumber=result.get("taxNumber"),
            regLocation=result.get("regLocation"),
            regInstitute=result.get("regInstitute"),
            businessScope=result.get("businessScope"),
            industry=result.get("industry"),
            staffNumRange=result.get("staffNumRange"),
            socialStaffNum=result.get("socialStaffNum"),
            base=result.get("base"),
            city=result.get("city"),
            district=result.get("district"),
            approvedTime=format_timestamp(result.get("approvedTime")),
            historyNames=result.get("historyNames"),
            bondName=result.get("bondName"),
            bondNum=result.get("bondNum"),
            bondType=result.get("bondType"),
            actualCapital=result.get("actualCapital"),
        )

    except httpx.HTTPStatusError as e:
        logger.error("天眼查 API HTTP 错误: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail=f"天眼查 API 请求失败: {str(e)}")
    except httpx.RequestError as e:
        logger.error("天眼查 API 请求错误: %s", e)
        raise HTTPException(status_code=500, detail=f"天眼查 API 连接失败: {str(e)}")
    except Exception as e:
        logger.error("天眼查企业基本信息查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tianyancha/patents")
async def tianyancha_patents(
    keyword: str = Query(..., description="搜索关键字（公司名称、公司ID、注册号或社会统一信用代码）"),
    pageSize: int = Query(20, ge=1, le=20, description="每页条数，默认20，最大20"),
    pageNum: int = Query(1, ge=1, description="当前页数，默认第1页"),
    patentType: Optional[int] = Query(None, ge=1, le=3, description="专利类型（1-发明专利 2-实用新型 3-外观专利）"),
    appDateBegin: Optional[str] = Query(None, description="申请开始时间，格式：YYYY-MM-DD"),
    appDateEnd: Optional[str] = Query(None, description="申请结束时间，格式：YYYY-MM-DD"),
    pubDateBegin: Optional[str] = Query(None, description="发布开始时间，格式：YYYY-MM-DD"),
    pubDateEnd: Optional[str] = Query(None, description="发布结束时间，格式：YYYY-MM-DD"),
    api_key: str = Depends(get_api_key),
):
    """
    天眼查企业专利信息接口 - 通过公司名称或ID获取专利信息.

    Args:
        keyword: 搜索关键字（公司名称、公司ID、注册号或社会统一信用代码）
        pageSize: 每页条数（默认20，最大20）
        pageNum: 当前页数（默认第1页）
        patentType: 专利类型（1-发明专利 2-实用新型 3-外观专利）
        appDateBegin: 申请开始时间
        appDateEnd: 申请结束时间
        pubDateBegin: 发布开始时间
        pubDateEnd: 发布结束时间
        api_key: API 密钥

    Returns:
        专利列表，包含专利名称、申请号、申请公布号等信息
    """
    if not keyword or not keyword.strip():
        raise HTTPException(status_code=400, detail="搜索关键字不能为空")

    if not settings.TIANYANCHA_API_TOKEN:
        raise HTTPException(status_code=500, detail="天眼查 API Token 未配置")

    logger.info("天眼查企业专利查询: keyword=%s, pageSize=%d, pageNum=%d", keyword, pageSize, pageNum)

    tianyancha_url = "http://open.api.tianyancha.com/services/open/ipr/patents/3.0"

    # 构建请求参数
    params = {"keyword": keyword, "pageSize": pageSize, "pageNum": pageNum}
    if patentType:
        params["patentType"] = patentType
    if appDateBegin:
        params["appDateBegin"] = appDateBegin
    if appDateEnd:
        params["appDateEnd"] = appDateEnd
    if pubDateBegin:
        params["pubDateBegin"] = pubDateBegin
    if pubDateEnd:
        params["pubDateEnd"] = pubDateEnd

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                tianyancha_url,
                params=params,
                headers={"Authorization": settings.TIANYANCHA_API_TOKEN},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("error_code") != 0:
            logger.error("天眼查 API 返回错误: %s", data.get("reason", "未知错误"))
            raise HTTPException(status_code=500, detail=f"天眼查查询失败: {data.get('reason', '未知错误')}")

        result = data.get("result", {})
        items = []
        for item in result.get("items", []):
            items.append(TianyanchaPatentItem(
                id=item.get("id"),
                patentName=item.get("patentName"),
                patentNum=item.get("patentNum"),
                applicationPublishNum=item.get("applicationPublishNum"),
                patentType=item.get("patentType"),
                patentStatus=item.get("patentStatus"),
                applicationTime=item.get("applicationTime"),
                pubDate=item.get("pubDate"),
                applicantname=item.get("applicantname"),
                inventor=item.get("inventor"),
                agent=item.get("agent"),
                agency=item.get("agency"),
                address=item.get("address"),
                abstracts=item.get("abstracts"),
                mainCatNum=item.get("mainCatNum"),
                cat=item.get("cat"),
            ))

        return TianyanchaPatentResponse(
            total=int(result.get("total", 0)),
            items=items,
        )

    except httpx.HTTPStatusError as e:
        logger.error("天眼查 API HTTP 错误: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail=f"天眼查 API 请求失败: {str(e)}")
    except httpx.RequestError as e:
        logger.error("天眼查 API 请求错误: %s", e)
        raise HTTPException(status_code=500, detail=f"天眼查 API 连接失败: {str(e)}")
    except Exception as e:
        logger.error("天眼查企业专利查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tianyancha/certificates")
async def tianyancha_certificates(
    name: Optional[str] = Query(None, description="公司名称（id与name只需输入其中一个）"),
    id: Optional[int] = Query(None, description="公司ID（id与name只需输入其中一个）"),
    certificateName: Optional[str] = Query(None, description="证书类型"),
    pageSize: int = Query(20, ge=1, le=20, description="每页条数，默认20，最大20"),
    pageNum: int = Query(1, ge=1, description="当前页数，默认第1页"),
    api_key: str = Depends(get_api_key),
):
    """
    天眼查企业资质证书接口 - 通过公司名称或ID获取资质证书信息.

    Args:
        name: 公司名称（id与name只需输入其中一个）
        id: 公司ID（id与name只需输入其中一个）
        certificateName: 证书类型
        pageSize: 每页条数（默认20，最大20）
        pageNum: 当前页数（默认第1页）
        api_key: API 密钥

    Returns:
        资质证书列表，包含证书类型、证书编号、发证日期等信息
    """
    if not name and not id:
        raise HTTPException(status_code=400, detail="公司名称或公司ID至少需要提供一个")

    if not settings.TIANYANCHA_API_TOKEN:
        raise HTTPException(status_code=500, detail="天眼查 API Token 未配置")

    logger.info("天眼查企业资质证书查询: name=%s, id=%s", name, id)

    tianyancha_url = "http://open.api.tianyancha.com/services/open/m/certificate/2.0"

    # 构建请求参数
    params = {"pageSize": pageSize, "pageNum": pageNum}
    if name:
        params["name"] = name
    if id:
        params["id"] = id
    if certificateName:
        params["certificateName"] = certificateName

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                tianyancha_url,
                params=params,
                headers={"Authorization": settings.TIANYANCHA_API_TOKEN},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("error_code") != 0:
            logger.error("天眼查 API 返回错误: %s", data.get("reason", "未知错误"))
            raise HTTPException(status_code=500, detail=f"天眼查查询失败: {data.get('reason', '未知错误')}")

        result = data.get("result", {})
        items = []
        for item in result.get("items", []):
            detail_items = []
            for d in item.get("detail", []):
                detail_items.append(TianyanchaCertificateDetailItem(
                    title=d.get("title"),
                    content=d.get("content"),
                ))
            items.append(TianyanchaCertificateItem(
                id=item.get("id"),
                certNo=item.get("certNo"),
                certificateName=item.get("certificateName"),
                certificateType=item.get("certificateType"),
                startDate=item.get("startDate"),
                endDate=item.get("endDate"),
                detail=detail_items,
            ))

        return TianyanchaCertificateResponse(
            total=result.get("total", 0),
            items=items,
        )

    except httpx.HTTPStatusError as e:
        logger.error("天眼查 API HTTP 错误: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail=f"天眼查 API 请求失败: {str(e)}")
    except httpx.RequestError as e:
        logger.error("天眼查 API 请求错误: %s", e)
        raise HTTPException(status_code=500, detail=f"天眼查 API 连接失败: {str(e)}")
    except Exception as e:
        logger.error("天眼查企业资质证书查询失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
