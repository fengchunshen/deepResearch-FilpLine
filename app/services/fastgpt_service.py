"""FastGPT 服务 - 与 FastGPT API 通信."""
from typing import Dict, Any, Optional, AsyncIterator, List
from app.core.config import settings
import httpx
import logging
import json
import asyncio
import re

logger = logging.getLogger(__name__)

# 并发控制信号量
_fastgpt_semaphore: Optional[asyncio.Semaphore] = None


def get_fastgpt_concurrency_manager(max_concurrent: int = 5) -> asyncio.Semaphore:
    """获取 FastGPT 并发控制信号量."""
    global _fastgpt_semaphore
    if _fastgpt_semaphore is None:
        _fastgpt_semaphore = asyncio.Semaphore(max_concurrent)
    return _fastgpt_semaphore


def parse_ai_json_response(response_text: str) -> Dict[str, Any]:
    """
    解析 AI 返回的 JSON 响应.

    尝试从响应文本中提取 JSON 数据，支持 markdown 代码块格式。
    """
    # 尝试直接解析
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(json_pattern, response_text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # 尝试查找 JSON 对象
    brace_pattern = r'\{[\s\S]*\}'
    brace_matches = re.findall(brace_pattern, response_text)
    for match in brace_matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"无法从响应中解析 JSON: {response_text[:200]}...")


class FastGPTService:
    """FastGPT 服务类."""
    
    def __init__(self):
        """初始化 FastGPT 服务."""
        self.api_url = settings.FASTGPT_API_URL
        self.api_key = settings.FASTGPT_API_KEY
        self.timeout = settings.TIMEOUT
    
    async def chat(
        self,
        message: str,
        chat_id: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        与 FastGPT 进行对话.
        
        Args:
            message: 用户消息
            chat_id: 会话 ID（可选）
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: FastGPT 响应
        """
        try:
            if not self.api_url or not self.api_key:
                raise ValueError("FastGPT API URL 或 API Key 未配置")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "message": message,
                    "chatId": chat_id,
                    "stream": stream,
                    **kwargs
                }
                
                response = await client.post(
                    f"{self.api_url}/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"FastGPT HTTP 错误: {e}")
            raise Exception(f"FastGPT 请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"FastGPT 调用时发生错误: {e}")
            raise
    
    async def get_chat_history(self, chat_id: str) -> Dict[str, Any]:
        """
        获取聊天历史记录.

        Args:
            chat_id: 会话 ID

        Returns:
            Dict[str, Any]: 聊天历史
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                response = await client.get(
                    f"{self.api_url}/api/v1/chat/history/{chat_id}",
                    headers=headers
                )
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"获取聊天历史失败: {e}")
            raise

    async def chat_stream(
        self,
        message: str,
        chat_id: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        与 FastGPT 进行流式对话.

        Args:
            message: 用户消息
            chat_id: 会话 ID（可选）
            api_url: 自定义 API URL（可选，默认使用全局配置）
            api_key: 自定义 API Key（可选，默认使用全局配置）
            **kwargs: 其他参数

        Yields:
            str: SSE 格式的流式数据块
        """
        try:
            use_api_url = api_url or self.api_url
            if not use_api_url:
                raise ValueError("FastGPT API URL 未配置")

            use_api_key = api_key or self.api_key
            if not use_api_key:
                raise ValueError("FastGPT API Key 未配置")

            headers = {
                "Authorization": f"Bearer {use_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "chatId": chat_id,
                "stream": True,
                "detail": False,
                "messages": [
                    {"role": "user", "content": message}
                ],
                **kwargs
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{use_api_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if chunk:
                            yield chunk

        except httpx.HTTPError as e:
            logger.error(f"FastGPT 流式请求 HTTP 错误: {e}")
            raise Exception(f"FastGPT 流式请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"FastGPT 流式调用时发生错误: {e}")
            raise

    async def call_fastgpt_simple(
        self,
        request_data: Dict[str, Any],
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        """
        简单调用 FastGPT，直接将 JSON 数据作为消息发送.

        Args:
            request_data: 企业信息字典
            api_url: 自定义 API URL（可选）
            api_key: 自定义 API Key（可选）
            max_retries: 最大重试次数

        Returns:
            Dict[str, Any]: 包含 relevantFiles 的响应
        """
        use_api_url = api_url or self.api_url
        use_api_key = api_key or self.api_key

        if not use_api_url or not use_api_key:
            raise ValueError("FastGPT API URL 或 API Key 未配置")

        # 将企业信息 JSON 直接作为消息内容
        message_content = json.dumps(request_data, ensure_ascii=False)

        semaphore = get_fastgpt_concurrency_manager()
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                async with semaphore:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        headers = {
                            "Authorization": f"Bearer {use_api_key}",
                            "Content-Type": "application/json"
                        }

                        payload = {
                            "stream": False,
                            "detail": False,
                            "messages": [
                                {"role": "user", "content": message_content}
                            ]
                        }

                        response = await client.post(
                            f"{use_api_url}/v1/chat/completions",
                            headers=headers,
                            json=payload
                        )
                        response.raise_for_status()

                        result = response.json()

                        # 提取 AI 响应内容
                        # 支持两种格式：
                        # 1. OpenAI 格式: {"choices": [{"message": {"content": "..."}}]}
                        # 2. 直接 JSON 格式: {"relevantFiles": [...]}
                        if "choices" in result and len(result["choices"]) > 0:
                            ai_content = result["choices"][0].get("message", {}).get("content", "")
                            parsed = parse_ai_json_response(ai_content)
                        elif "relevantFiles" in result:
                            # FastGPT 直接返回 JSON 对象
                            parsed = result
                        else:
                            raise ValueError(f"无法识别的响应格式: {str(result)[:200]}")

                        # 获取 relevantFiles 并移除文件扩展名
                        relevant_files = parsed.get("relevantFiles", [])
                        cleaned_files = self._remove_file_extensions(relevant_files)

                        return {"relevantFiles": cleaned_files}

            except Exception as e:
                last_error = e
                error_msg = str(e) if str(e) else type(e).__name__
                logger.warning(f"FastGPT 简单调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                if attempt < max_retries:
                    # 指数退避
                    await asyncio.sleep(2 ** attempt)

        raise Exception(f"FastGPT 简单调用失败，已重试 {max_retries} 次: {last_error}")

    def _remove_file_extensions(self, files: List[str]) -> List[str]:
        """移除文件扩展名 (.md, .pdf, .docx, .html)."""
        extensions = ('.md', '.pdf', '.docx', '.html')
        result = []
        for f in files:
            for ext in extensions:
                if f.lower().endswith(ext):
                    f = f[:-len(ext)]
                    break
            result.append(f)
        return result


# 创建全局服务实例
fastgpt_service = FastGPTService()

