# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

langchain-megumi 是基于 FastAPI + LangChain 的 AI 服务项目，专为与 RuoYi 后端集成设计。提供 DeepSearch 深度研究、绘图、OCR、FastGPT 对话、天眼查企业查询等 AI 功能。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
python -m app.main
# 或
uvicorn app.main:app --reload

# Docker 构建与运行
docker build -t langchain-megumi .
docker run -d -p 8000:8000 --env-file .env langchain-megumi

# 安全检查
python scripts/security_check.py
```

## 架构概览

### 分层结构

- **apis/v1/**: API 路由层，每个 `endpoint_*.py` 对应一个功能模块
- **services/**: 业务逻辑层，服务类使用单例模式，方法为 `async def`
- **models/**: Pydantic v2 数据模型
- **chains/**: LangChain 链定义（Runnable）
- **core/**: 配置管理（`config.py`）、日志（`logger.py`）、安全认证（`security.py`）

### DeepSearch 引擎（核心模块）

位于 `app/services/deepsearch_engine.py`，基于 LangGraph 状态图实现：

1. 研究计划生成 → 查询生成 → 网络搜索 → 反思评估（循环）→ 质量增强 → 报告生成
2. 支持 SSE 流式输出，15 种事件类型
3. 模型降级机制：Gemini 异常时自动降级至 Qwen3Max
4. 连接级取消：基于 `asyncio.Event` 实现

### 认证机制

- 使用 `X-API-Key` 请求头认证
- 生产环境（DEBUG=false）强制要求配置 `RUOYI_API_KEY`
- 开发环境可跳过认证

## 开发规范

- 路由使用 `APIRouter`，在 `main.py` 统一注册
- 异常处理使用 `HTTPException`
- 日志使用 `app/core/logger.py` 中的 `jinfo`、`jerror` 等结构化日志函数
- 配置通过 `app.core.config.settings` 访问，从 `.env` 加载

## 环境配置

复制 `.env.example` 为 `.env`，关键配置：

- `DEBUG`: 生产环境设为 `false`
- `RUOYI_API_KEY`: API 认证密钥
- `GEMINI_API_KEY` / `DASHSCOPE_API_KEY`: AI 模型 API
- `BOCHA_API_KEY`: 博查搜索（DeepSearch 必需）
- `ALLOW_ORIGINS`: CORS 白名单（生产环境必须配置具体域名）
