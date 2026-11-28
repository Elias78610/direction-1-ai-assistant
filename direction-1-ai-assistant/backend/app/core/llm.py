"""OpenAI 兼容大模型客户端（文本对话）。

不引入额外 SDK，仅用标准库发 HTTP；配置来自 ``core/config`` 的 ``llm_*``。
未配置 Key 或调用 / 解析失败时返回 None，由业务层回退到规则解析，
保证模型不可用时接口仍能按规则给出兜底结果。
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15


class LlmClient:
    """文本大模型调用封装；配置在实例化时读取。"""

    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_api_base.rstrip("/")
        self.model = settings.llm_model

    @property
    def is_configured(self) -> bool:
        """是否已配置可用的模型接入（Key 与模型名）。"""
        return bool(self.api_key and self.model)

    def chat_json(self, system: str, user: str) -> dict[str, Any] | None:
        """请求模型返回 JSON 对象；未配置 / 异常 / 解析失败返回 None。

        业务层拿到 None 即应回退规则，不要把异常抛给前端。
        """
        if not self.is_configured:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return _loads_json_object(content)
        except (
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            logger.warning("LLM 调用失败，回退规则解析: %s", exc)
            return None


def _loads_json_object(content: str) -> dict[str, Any] | None:
    """从模型输出中提取 JSON 对象，容忍 ```json 围栏与前后多余文本。"""
    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    obj = json.loads(text[start : end + 1])
    return obj if isinstance(obj, dict) else None
