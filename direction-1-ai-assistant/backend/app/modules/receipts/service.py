"""小票 OCR 业务层：图片落盘、文本规则解析与待确认账目组装。

规则解析移植自早期原型脚本；视觉识别本身由 ``vision.py`` 封装，
接入真实多模态模型后，本层只负责把文本行结构化。
"""

import logging
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.core.exceptions import AppException
from app.modules.receipts.vision import VisionClient

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB，与契约一致
UPLOAD_ROOT = Path("data/uploads")

TWO_PLACES = Decimal("0.01")

TIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?")
MONEY_RE = re.compile(r"-?\d+(?:\.\d+)?")
QTY_RE = re.compile(r"^[×xX]\s*(\d+)$")
PRICE_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

# 合计 / 金额类行，不作为商品名
TOTAL_KEYWORDS = ("合计", "应付", "实付", "优惠", "金额", "总计", "小计")


def _format_amount(value: Decimal) -> str:
    return str(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def _to_decimal(text: str | None) -> Decimal | None:
    if text is None:
        return None
    match = MONEY_RE.search(str(text))
    if not match:
        return None
    try:
        return Decimal(match.group())
    except ArithmeticError:
        return None


def _parse_time(lines: list[str]) -> datetime | None:
    """从小票文本行提取日期时间；识别不出返回 None。"""
    for line in lines:
        match = TIME_RE.search(line)
        if match:
            date_part = match.group(1)
            time_part = match.group(2) or "12:00"
            try:
                return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
    return None


class ReceiptService:
    """小票识别业务层。"""

    def __init__(self, vision: VisionClient | None = None) -> None:
        self.vision = vision or VisionClient()

    def recognize(self, content: bytes, filename: str) -> dict:
        # 1. 校验类型与大小
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise AppException(
                code="BAD_REQUEST",
                message="仅支持 jpg / jpeg / png / webp 格式的小票图片",
                status_code=400,
            )
        if len(content) > MAX_SIZE:
            raise AppException(
                code="BAD_REQUEST",
                message="图片大小不能超过 10MB",
                status_code=400,
            )

        # 2. 图片落盘到 data/uploads/YYYYMMDD/，路径写相对路径
        image_path = self._save_upload(content, filename, ext)

        # 3. 调视觉模型取文本行（未配置 / 未接入时抛 503）
        lines = self.vision.recognize_lines(content, filename)
        raw_text = "\n".join(line for line in lines if line.strip())

        # 4. 规则结构化
        spent_at = _parse_time(lines)
        items, warnings = self._parse_items(lines, spent_at)

        if not items:
            warnings.append("未能从小票识别出可入账的商品或金额，请手动录入")

        return {
            "image_path": image_path,
            "raw_text": raw_text,
            "items": items,
            "warnings": warnings,
        }

    def _save_upload(self, content: bytes, filename: str, ext: str) -> str:
        """保存图片并返回 data/uploads/ 下的相对路径；文件名做防穿越清洗。"""
        safe_name = Path(filename).name.replace("/", "_").replace("\\", "_")
        day_dir = UPLOAD_ROOT / datetime.now().strftime("%Y%m%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%H%M%S%f")
        dest = day_dir / f"{stamp}_{safe_name}"
        dest.write_bytes(content)
        return dest.as_posix()

    def _parse_items(
        self, lines: list[str], spent_at: datetime | None
    ) -> tuple[list[dict], list[str]]:
        """把文本行拆成待确认账目；金额 / 商品名识别不出时给 null。"""
        warnings: list[str] = []
        cleaned = [line.strip() for line in lines if line.strip()]

        current: dict | None = None
        items: list[dict] = []
        total_amount: Decimal | None = None

        for line in cleaned:
            if any(k in line for k in TOTAL_KEYWORDS):
                amount = _to_decimal(line)
                if amount is not None:
                    total_amount = amount
                continue

            qty = QTY_RE.match(line)
            price = PRICE_RE.match(line)
            if qty and current is not None:
                current["quantity"] = int(qty.group(1))
            elif price and current is not None:
                current["price"] = _to_decimal(line)
            elif not price:
                current = {"name": line, "quantity": None, "price": None}
                items.append(current)

        # 商品行带单价的，逐笔组装；只有合计金额的，组装成一笔
        result: list[dict] = []
        for item in items:
            price = item.get("price")
            result.append(
                {
                    "amount": _format_amount(price) if price is not None else None,
                    "category": None,
                    "spent_at": spent_at,
                    "note": item.get("name"),
                    "source": "ocr",
                    "confidence": 0.85,
                }
            )

        if not result and total_amount is not None:
            result.append(
                {
                    "amount": _format_amount(total_amount),
                    "category": None,
                    "spent_at": spent_at,
                    "note": None,
                    "source": "ocr",
                    "confidence": 0.8,
                }
            )

        if result and any(i["amount"] is None for i in result):
            warnings.append("部分商品金额未能识别，请在确认卡片中补填")

        return result, warnings
