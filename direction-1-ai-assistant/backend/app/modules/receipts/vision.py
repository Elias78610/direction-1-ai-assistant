"""视觉模型客户端：封装小票图片识别调用。

工程统一走 OpenAI 兼容的多模态接口（配置见 ``core/config`` 的 ``vision_*``）；
早期原型使用本地 PaddleOCR，正式工程不再引入本地 OCR 模型。
未配置 Key 或调用失败时抛 503，由前端降级为手动录入。
"""

import base64
import json
import logging
import mimetypes
import urllib.error
import urllib.request

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

_TIMEOUT = 20

_OCR_PROMPT = (
    "识别这张消费小票或截图，逐行输出上面的文字，每行一条，"
    "保留商品名、单价、数量、日期时间、合计金额；不要解释、不要汇总、不要加序号。"
)


class VisionClient:
    """视觉模型调用封装；延迟读取配置，未配置时不拖慢启动。"""

    def __init__(self) -> None:
        self.api_key = settings.vision_api_key
        self.base_url = settings.vision_api_base.rstrip("/")
        self.model = settings.vision_model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def recognize_lines(self, image_bytes: bytes, filename: str) -> list[str]:
        """识别小票图片，返回文本行列表。

        未配置视觉模型或调用失败时抛 503，由前端降级为手动录入。
        """
        if not self.is_configured:
            raise AppException(
                code="OCR_UNAVAILABLE",
                message="OCR 视觉模型未配置，请检查 VISION_API_KEY / VISION_API_BASE / VISION_MODEL",
                status_code=503,
            )

        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0.1,
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
            content = data["choices"][0]["message"]["content"] or ""
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("视觉模型调用失败: %s", exc)
            raise AppException(
                code="OCR_UNAVAILABLE",
                message="OCR 识别服务暂时不可用，请稍后重试或手动录入",
                status_code=503,
            ) from exc

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            raise AppException(
                code="OCR_UNAVAILABLE",
                message="未能从小票识别出文字，请手动录入",
                status_code=503,
            )
        return lines
