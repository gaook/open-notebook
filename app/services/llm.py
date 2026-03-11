"""LLM 服务 — OpenAI 兼容 API 流式调用"""

import json
import re
from collections.abc import AsyncGenerator

import httpx


def _strip_think_tags(text: str) -> str:
    """移除 <think>...</think> 思维链标签（部分模型如 MiniMax-M2.5 会输出）"""
    return re.sub(r"<think>[\s\S]*?</think>\s*", "", text)


class LLMService:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM，逐块 yield 文本，自动过滤思维链标签"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            ) as response:
                response.raise_for_status()
                # 用缓冲区处理跨块的 <think> 标签
                buffer = ""
                in_think = False

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" not in delta or not delta["content"]:
                            continue

                        chunk = delta["content"]

                        # 过滤 <think>...</think> 块
                        for char in chunk:
                            buffer += char
                            if not in_think:
                                if buffer.endswith("<think>"):
                                    # 进入思维链，丢弃标签
                                    buffer = buffer[:-7]
                                    if buffer:
                                        yield buffer
                                        buffer = ""
                                    in_think = True
                                elif len(buffer) > 7:
                                    # 安全输出非标签部分
                                    safe = buffer[:-6]
                                    buffer = buffer[-6:]
                                    yield safe
                            else:
                                if buffer.endswith("</think>"):
                                    buffer = ""
                                    in_think = False

                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                # 输出剩余缓冲区
                if buffer and not in_think:
                    # 清除可能残留的思维链
                    cleaned = _strip_think_tags(buffer)
                    if cleaned.strip():
                        yield cleaned

    async def test_connection(self) -> dict:
        """测试 LLM 连接（发送简短对话测试）"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 先尝试 /models（OpenAI 标准）
                resp = await client.get(
                    f"{self.base_url}/models", headers=headers
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "连接成功"}

                # /models 不可用则发一条测试消息
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5,
                    },
                )
                resp.raise_for_status()
                return {"success": True, "message": f"连接成功 (模型: {self.model})"}
        except Exception as e:
            return {"success": False, "message": f"连接失败: {e}"}
