"""视觉模型客户端：封装小票图片识别调用。

工程统一走 OpenAI 兼容的视觉接口（配置见 ``core/config`` 的 ``vision_*``）；
早期原型使用本地 PaddleOCR，正式工程不再引入本地 OCR 模型。
本轮先做好配置检查与调用占位，多模态识别联调待环境与 Key 接入。
"""

import logging

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class VisionClient:
    """视觉模型调用封装；延迟导入 SDK，避免未配置时拖慢启动。"""

    def __init__(self) -> None:
        self.api_key = settings.vision_api_key
        self.base_url = settings.vision_api_base
        self.model = settings.vision_model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def recognize_lines(self, image_bytes: bytes, filename: str) -> list[str]:
        """识别小票图片，返回文本行列表。

        未配置视觉模型或多模态调用未接入时抛 503，由前端降级为手动录入。
        """
        if not self.is_configured:
            raise AppException(
                code="OCR_UNAVAILABLE",
                message="OCR 视觉模型未配置，请检查 VISION_API_KEY / VISION_MODEL",
                status_code=503,
            )

        # TODO(联调): 在此接入 OpenAI 兼容多模态接口，图片按 base64 传入，
        # 解析返回文本行；当前骨架尚未接入真实模型调用。
        raise AppException(
            code="OCR_UNAVAILABLE",
            message="OCR 识别服务暂未接入，当前降级为手动录入",
            status_code=503,
        )
