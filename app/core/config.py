"""应用配置管理 - 环境变量和 API Keys."""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


def get_project_root() -> Path:
    """获取项目根目录（langchain-megumi）."""
    # 从当前文件位置向上查找，找到包含 app 目录的项目根目录
    current_file = Path(__file__).resolve()
    # config.py 在 app/core/ 目录下，向上两级到项目根目录
    project_root = current_file.parent.parent.parent
    return project_root


class Settings(BaseSettings):
    """应用配置类 - 从环境变量加载配置."""
    
    # 应用基础配置
    APP_NAME: str = "Megumi AI Servive"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API 服务配置
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None  # 可选的自定义 API 地址
    OPENAI_MODEL: str = "gpt-4"
    
    # FastGPT 配置
    FASTGPT_API_URL: Optional[str] = None
    FASTGPT_API_KEY: Optional[str] = None
    FASTGPT_POLICY_API_URL: Optional[str] = None  # 政策解读专用 API URL
    FASTGPT_POLICY_API_KEY: Optional[str] = None  # 政策解读专用 API Key
    FASTGPT_POLICY_GUIDE_API_URL: Optional[str] = None  # 政策导读助手 API URL
    FASTGPT_POLICY_GUIDE_API_KEY: Optional[str] = None  # 政策导读助手 API Key
    FASTGPT_NODE_ANALYZE_API_URL: Optional[str] = None  # 产业链节点分析 API URL
    FASTGPT_NODE_ANALYZE_API_KEY: Optional[str] = None  # 产业链节点分析 API Key
    
    # 绘图服务配置（例如：DALL-E, Stable Diffusion）
    DRAWING_API_KEY: Optional[str] = None
    DRAWING_API_URL: Optional[str] = None
    
    # DashScope (阿里云通义千问) OCR 配置
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: Optional[str] = None
    DASHSCOPE_OCR_MODEL: str = "qwen-vl-ocr-latest"
    DASHSCOPE_CHAT_MODEL: str = "qwen3-max"
    
    # DeepSeek API 配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: Optional[str] = None
    DEEPSEEK_SSL_VERIFY: bool = True
    DEEPSEEK_CA_BUNDLE: Optional[str] = None
    
    # 博查搜索 API 配置
    BOCHA_API_KEY: Optional[str] = None
    
    # 天眼查 API 配置
    TIANYANCHA_API_TOKEN: Optional[str] = None

    # 标签代理 API 配置
    TAG_AGENT_API_URL: Optional[str] = None
    TAG_AGENT_AUTHORIZATION: Optional[str] = None
    
    # Gemini API 配置
    GEMINI_API_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-pro"  # Gemini 模型名称
    
    # RuoYi 后端认证配置
    RUOYI_API_KEY: Optional[str] = None  # 用于验证来自 RuoYi 的请求
    
    # CORS 配置
    ALLOW_ORIGINS: str = "*"  # 允许的域名列表，用逗号分隔，如 "https://example.com,https://app.example.com"
    
    # 其他配置
    TIMEOUT: int = 30  # 请求超时时间（秒）
    MAX_RETRIES: int = 3  # 最大重试次数
    API_TIMEOUT: int = 600  # API 请求超时时间（秒），默认10分钟，用于 DeepSearch 等长时间任务
    
    # 深度网页抓取配置
    WEB_SCRAPE_TOP_K: int = 8  # 深度抓取的网页数量
    WEB_SCRAPE_CONCURRENCY: int = 8  # 并发抓取数量
    WEB_SCRAPE_TIMEOUT: int = 20  # 单个网页抓取超时时间（秒）
    WEB_SCRAPE_MAX_TOTAL_CHARS: int = 80000  # 所有抓取内容的总字符数上限
    WEB_SCRAPE_MAX_PER_DOC_CHARS: int = 20000  # 单个网页内容的字符数上限
    WEB_SCRAPE_USER_AGENT: str = "Mozilla/5.0 (MegumiBot/1.0; +https://example.com/bot)"  # User-Agent
    
    # DeepSearch 配置
    DEEPSEARCH_USE_ZH_QUERY_FOR_SEARCH: bool = False  # 是否优先使用中文查询作为真实搜索关键词

    model_config = {
        "env_file": str(get_project_root() / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


# 创建全局配置实例
settings = Settings()

