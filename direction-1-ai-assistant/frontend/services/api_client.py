# -*- coding: utf-8 -*-
"""
API 客户端（接口契约 v1）
=========================

职责边界：
  - 本文件是「页面层」与「后端 FastAPI」之间的唯一通信通道；
  - 普通接口统一前缀 /api/v1，健康检查 /health 不带前缀；
  - 金额使用「元字符串」（如 "25.50"），不使用整数分或浮点数；
  - 时间使用 ISO 8601 本地时间（如 "2026-11-24T12:30:00"）；
  - 统一处理基地址拼接、超时、网络/超时/HTTP/业务错误分类；
  - 演示模式（DEMO_MODE / 侧边栏勾选）沿用 services/demo_data.py，
    不发真实请求。

接口契约来源：docs/接口契约 v1（以 /openapi.json 为最终校验依据）。
"""

import calendar
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests

import config

logger = logging.getLogger("ledger.api")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [API] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class ApiError(Exception):
    """统一的接口异常：页面层捕获后按 kind 分级展示友好提示。"""

    def __init__(self, status_code=0, detail="", kind="http", code="", request_id=""):
        super().__init__(detail or f"接口调用失败（状态码 {status_code}）")
        self.status_code = status_code
        self.detail = detail
        self.kind = kind  # http / network / timeout
        self.code = code
        self.request_id = request_id


def get_base_url():
    """当前生效的后端地址（契约 v1 固定为 http://localhost:8000）。"""
    return config.API_BASE_URL.strip().rstrip("/")


def is_demo_mode():
    """演示模式是否生效（侧边栏 > 环境变量 > config 默认值）。"""
    try:
        import streamlit as st
        if "demo_mode" in st.session_state:
            return bool(st.session_state["demo_mode"])
    except Exception:
        pass
    return config.DEMO_MODE


def _demo_api():
    """懒加载演示数据模块（仅在演示模式下导入，非演示模式零开销）。"""
    from services import demo_data
    return demo_data


# ═══════════════════════════════════════════════════════════════════
# 统一请求封装：URL 拼接 / 超时 / 异常分类 / 错误文案
# ═══════════════════════════════════════════════════════════════════

def _url(path):
    return get_base_url() + path


def _extract_error_detail(resp):
    """解析契约统一错误结构：{code, message, errors, request_id}。"""
    try:
        body = resp.json()
    except ValueError:
        body = None

    request_id = ""
    if isinstance(body, dict):
        request_id = str(body.get("request_id") or "")
    request_id = request_id or (resp.headers.get("X-Request-ID") or "")

    if isinstance(body, dict):
        message = body.get("message") or body.get("detail") or body.get("error")
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0] if isinstance(errors[0], dict) else {}
            field = first.get("field") or ""
            item_msg = first.get("message") or ""
            if field or item_msg:
                detail = f"{message or '参数校验失败'}：{field} {item_msg}".strip()
                if request_id:
                    detail += f"（request_id: {request_id}）"
                return detail
        if message:
            detail = str(message)
            if request_id:
                detail += f"（request_id: {request_id}）"
            return detail

    if resp.status_code == 404:
        return "请求的接口或资源不存在（404），请核对契约路径。"
    if resp.status_code == 422:
        return "参数校验失败（422），请核对字段格式与必填项。"
    if resp.status_code in (502, 503):
        return "AI 服务暂不可用，请稍后重试，或改用手动录入。"
    if resp.status_code >= 500:
        return "服务开小差了（500），请稍后重试。"
    return f"请求失败（HTTP {resp.status_code}），请稍后重试。"


def _check_response(resp):
    """2xx → JSON；204 → {}；否则抛 ApiError(kind="http")。"""
    if 200 <= resp.status_code < 300:
        if resp.status_code == 204:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}
    body = {}
    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        body = {}
    code = body.get("code", "") if isinstance(body, dict) else ""
    request_id = ""
    if isinstance(body, dict):
        request_id = str(body.get("request_id") or "")
    request_id = request_id or (resp.headers.get("X-Request-ID") or "")
    raise ApiError(resp.status_code, _extract_error_detail(resp), kind="http",
                   code=str(code), request_id=request_id)


def _debug_payload(kwargs):
    """生成可安全打印的请求参数（文件只打印文件名/字节数）。"""
    payload = {}
    for key in ("params", "json", "data"):
        if key in kwargs:
            payload[key] = kwargs[key]
    if "files" in kwargs:
        files = kwargs["files"]
        if isinstance(files, dict):
            summary = {}
            for name, value in files.items():
                if isinstance(value, (tuple, list)) and len(value) >= 2:
                    content = value[1]
                    size = len(content) if isinstance(content, (bytes, bytearray)) else "?"
                    summary[name] = (value[0], size)
                else:
                    summary[name] = repr(value)
            payload["files"] = summary
        else:
            payload["files"] = "<multipart>"
    return payload


def _request(method, path, timeout=None, **kwargs):
    """统一请求入口：调试日志 + 超时分级 + 网络异常分类 + 业务错误转 ApiError。"""
    url = _url(path)
    logger.info("请求 %s %s payload=%s", method, url, _debug_payload(kwargs))
    try:
        resp = requests.request(method, url,
                                timeout=timeout or config.REQUEST_TIMEOUT,
                                **kwargs)
    except requests.exceptions.Timeout:
        logger.warning("响应超时 %s %s", method, url)
        raise ApiError(0, "请求超时（后端处理时间过长），请稍后重试。", kind="timeout")
    except requests.exceptions.ConnectionError:
        logger.warning("连接失败 %s %s（请检查后端是否启动/端口/CORS）", method, url)
        raise ApiError(0, "无法连接后端服务，请确认服务已启动（localhost:8000），"
                          "如为浏览器直连请检查 CORS 配置。", kind="network")
    except requests.exceptions.RequestException as exc:
        logger.warning("请求异常 %s %s：%s", method, url, exc)
        raise ApiError(0, "请求发送失败，请检查后端地址与网络。", kind="network")
    logger.info("响应 %s %s status=%s body=%s",
                method, getattr(resp, "url", url), resp.status_code,
                (resp.text or "")[:2000])
    return _check_response(resp)


# ═══════════════════════════════════════════════════════════════════
# 金额 / 时间 / 来源字段转换（发送前严格按契约格式化）
# ═══════════════════════════════════════════════════════════════════

_SOURCE_MAP = {
    "text": "nlp",
    "nlp": "nlp",
    "receipt": "ocr",
    "ocr": "ocr",
    "manual": "manual",
}


def _amount_str(value):
    """把元金额转换为契约要求的两位小数字符串。"""
    if value is None:
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ApiError(422, "金额格式不正确，应为大于 0 的元金额。")
    if amount <= 0:
        raise ApiError(422, "金额必须大于 0。")
    return f"{amount:.2f}"


def _spent_at_str(value):
    """转换为 ISO 8601 本地时间（不带时区）；只有日期时补 T00:00:00。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone().replace(tzinfo=None)
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat() + "T00:00:00"
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 10:
        return text + "T00:00:00"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed.isoformat(timespec="seconds")
    except ValueError:
        return text


def _date_str(value):
    """日期查询参数统一补零为 YYYY-MM-DD。"""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return text


def _source_value(value):
    if value is None:
        return None
    return _SOURCE_MAP.get(str(value).lower(), str(value).lower())


def _expense_payload(payload, partial=False):
    """把页面数据转换成契约允许的账目字段。

    只发送契约定义字段；旧页面遗留的 direction / merchant / amount_cents
    会在这一层被转换为 amount / spent_at / category，不会传给后端。
    更新接口只允许 amount / category / spent_at / note / raw_text。
    """
    payload = payload or {}
    data = {}

    amount = payload.get("amount")
    if amount is None and "amount_cents" in payload:
        amount = Decimal(str(payload["amount_cents"])) / Decimal("100")
    if amount is not None:
        data["amount"] = _amount_str(amount)

    category = payload.get("category")
    if category is None:
        category = payload.get("category_name")
    if category is not None:
        data["category"] = str(category)

    spent_at = payload.get("spent_at")
    if spent_at is None:
        spent_at = payload.get("occurred_at")
    if spent_at is not None:
        data["spent_at"] = _spent_at_str(spent_at)

    if "note" in payload:
        data["note"] = payload.get("note")
    if "raw_text" in payload:
        data["raw_text"] = payload.get("raw_text")
    elif "raw_input" in payload:
        data["raw_text"] = payload.get("raw_input")

    if not partial:
        if payload.get("source") is not None:
            data["source"] = _source_value(payload.get("source"))
        # 注意：后端当前 ExpenseCreate 没有 image_path 字段（模型/ExpenseOut 有），
        # 因此创建请求暂不发送 image_path；后端 Schema 补充后再恢复。
        allowed = {"amount", "category", "spent_at", "note",
                   "source", "raw_text"}
    else:
        # source / image_path 只在创建时确定，更新接口传了会 422。
        allowed = {"amount", "category", "spent_at", "note", "raw_text"}

    return {key: value for key, value in data.items() if key in allowed}


def _month_range(month):
    """YYYY-MM → (start_date, end_date)，end 包含当月最后一天。"""
    year, mon = int(month[:4]), int(month[5:7])
    last_day = calendar.monthrange(year, mon)[1]
    return f"{month}-01", f"{month}-{last_day:02d}"


def _months_ago_start(months):
    """近 N 个月（含本月）的起始日期。"""
    today = date.today()
    month_index = today.year * 12 + today.month - 1 - (max(months, 1) - 1)
    year, mon = divmod(month_index, 12)
    return f"{year:04d}-{mon + 1:02d}-01"


# ═══════════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════════

def check_health():
    """GET /health —— 返回 {status, db}；db 为 error 表示数据库不可用。"""
    if is_demo_mode():
        return _demo_api().check_health()
    return _request("GET", config.PATH_HEALTH)


# ═══════════════════════════════════════════════════════════════════
# 类别
# ═══════════════════════════════════════════════════════════════════

def fetch_categories():
    """GET /api/v1/categories —— 返回类别名称数组（固定 8 类）。"""
    if is_demo_mode():
        return _demo_api().fetch_categories()
    return _request("GET", config.PATH_CATEGORIES)


# ═══════════════════════════════════════════════════════════════════
# 自然语言解析
# ═══════════════════════════════════════════════════════════════════

def parse_transaction_text(text, direction=None):
    """POST /api/v1/expenses/parse —— 只解析不入库。

    请求体严格为 {"text": "..."}；响应为扁平账目字段：
    amount / category / spent_at / note / source / raw_text / confidence。
    direction 参数仅为兼容旧页面保留，不发送给 v1 契约。
    """
    if is_demo_mode():
        return _demo_api().parse_transaction_text(text, direction or "expense")
    return _request("POST", config.PATH_EXPENSE_PARSE,
                    timeout=config.LLM_REQUEST_TIMEOUT,
                    json={"text": text})


# ═══════════════════════════════════════════════════════════════════
# 账目 CRUD
# ═══════════════════════════════════════════════════════════════════

def create_transaction(payload):
    """POST /api/v1/expenses —— 新增账目。

    请求字段与后端 ExpenseCreate 完全一致：
    amount / category / spent_at / note / source / raw_text。
    后端当前未在 ExpenseCreate 中声明 image_path，因此暂不发送该字段。
    """
    if is_demo_mode():
        return _demo_api().create_transaction(payload)
    return _request("POST", config.PATH_EXPENSES,
                    json=_expense_payload(payload, partial=False))


def fetch_transactions(start_date=None, end_date=None, category_id=None,
                       direction=None, limit=200, offset=0):
    """GET /api/v1/expenses —— 查询账目列表。

    v1 参数：category / start / end / limit / offset / sort_by / order。
    旧页面的 start_date/end_date 会映射到 start/end；direction 本期不参与过滤。
    """
    if is_demo_mode():
        return _demo_api().fetch_transactions(start_date, end_date, category_id,
                                              direction, limit, offset)
    params = {
        "start": _date_str(start_date),
        "end": _date_str(end_date),
        "category": category_id,
        "limit": min(max(int(limit), 1), 500),
        "offset": max(int(offset), 0),
        "sort_by": "spent_at",
        "order": "desc",
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}
    return _request("GET", config.PATH_EXPENSES, params=params)


def get_transaction(tx_id):
    """GET /api/v1/expenses/{id} —— 查询单笔账目详情。"""
    if is_demo_mode():
        rows = _demo_api().fetch_transactions(limit=500)["transactions"]
        for row in rows:
            if row.get("id") == tx_id:
                return row
        raise ApiError(404, "账目不存在。")
    return _request("GET", config.PATH_EXPENSE_ITEM.format(id=tx_id))


def update_transaction(tx_id, payload):
    """PUT /api/v1/expenses/{id} —— 部分更新账目（image_path 不可更新）。"""
    if is_demo_mode():
        return _demo_api().update_transaction(tx_id, payload)
    return _request("PUT", config.PATH_EXPENSE_ITEM.format(id=tx_id),
                    json=_expense_payload(payload, partial=True))


def delete_transaction(tx_id):
    """DELETE /api/v1/expenses/{id} —— 成功返回 204，无响应体。"""
    if is_demo_mode():
        return _demo_api().delete_transaction(tx_id)
    return _request("DELETE", config.PATH_EXPENSE_ITEM.format(id=tx_id))


# ═══════════════════════════════════════════════════════════════════
# 小票 OCR
# ═══════════════════════════════════════════════════════════════════

def ocr_receipt(file_bytes, filename=""):
    """POST /api/v1/receipts/ocr —— multipart 上传，字段名 file。"""
    if is_demo_mode():
        return _demo_api().ocr_receipt(file_bytes, filename)
    if not file_bytes:
        raise ApiError(400, "请先选择一张小票图片。")
    name = (filename or "").lower()
    if not name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise ApiError(400, "仅支持 jpg / png / webp 格式的图片。")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise ApiError(400, "图片大小不能超过 10MB。")
    ext = name.rsplit(".", 1)[-1]
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext, "application/octet-stream")
    files = {"file": (filename or f"receipt.{ext}", file_bytes, mime)}
    return _request("POST", config.PATH_RECEIPT_OCR,
                    timeout=config.OCR_REQUEST_TIMEOUT, files=files)


# ═══════════════════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════════════════

def fetch_stats_summary(month):
    """GET /api/v1/stats/summary?start&end —— 月度总览。"""
    if is_demo_mode():
        return _demo_api().fetch_stats_summary(month)
    start, end = _month_range(month)
    return _request("GET", config.PATH_STATS_SUMMARY,
                    params={"start": start, "end": end})


def fetch_stats_category(start_date=None, end_date=None, direction=None):
    """GET /api/v1/stats/categories?start&end —— 分类统计。"""
    if is_demo_mode():
        return _demo_api().fetch_stats_category(start_date, end_date, direction or "expense")
    params = {"start": _date_str(start_date), "end": _date_str(end_date)}
    params = {k: v for k, v in params.items() if v not in (None, "")}
    return _request("GET", config.PATH_STATS_CATEGORIES, params=params)


def fetch_stats_trend(start_date, end_date, granularity="month"):
    """GET /api/v1/stats/trend?start&end&granularity —— 趋势统计。"""
    if is_demo_mode():
        return _demo_api().fetch_stats_monthly(6, "expense")
    params = {
        "start": _date_str(start_date),
        "end": _date_str(end_date),
        "granularity": granularity,
    }
    return _request("GET", config.PATH_STATS_TREND, params=params)


def fetch_stats_monthly(months=6, direction=None):
    """GET /api/v1/stats/trend?start&end&granularity=month —— 月度趋势。"""
    if is_demo_mode():
        return _demo_api().fetch_stats_monthly(months, direction or "expense")
    params = {
        "start": _months_ago_start(months),
        "end": date.today().isoformat(),
        "granularity": "month",
    }
    return _request("GET", config.PATH_STATS_TREND, params=params)


# ═══════════════════════════════════════════════════════════════════
# 自然语言查账
# ═══════════════════════════════════════════════════════════════════

def query_accounts(question):
    """POST /api/v1/query —— 自然语言查账。"""
    if is_demo_mode():
        return _demo_api().query_accounts(question)
    return _request("POST", config.PATH_QUERY,
                    timeout=config.LLM_REQUEST_TIMEOUT,
                    json={"question": question})


# ═══════════════════════════════════════════════════════════════════
# 预算
# ═══════════════════════════════════════════════════════════════════

def fetch_budgets(month):
    """GET /api/v1/budgets/{month} —— 查询预算与执行情况。"""
    if is_demo_mode():
        return _demo_api().fetch_budgets(month)
    return _request("GET", config.PATH_BUDGET_ITEM.format(month=month))


def save_budget(month, amount):
    """PUT /api/v1/budgets/{month} —— 设置/更新月度总预算。

    金额 <= 0 表示取消该月预算，改为调用 DELETE 接口。
    """
    if amount is None:
        raise ApiError(422, "预算金额不能为空。")
    if Decimal(str(amount)) <= 0:
        try:
            delete_budget(month)
        except ApiError as exc:
            # 本来就没有预算，视为取消成功
            if exc.status_code != 404:
                raise
        return {}
    if is_demo_mode():
        payload = {"month": month, "total_budget_cents": int(Decimal(str(amount)) * 100)}
        return _demo_api().save_budgets(payload)
    return _request("PUT", config.PATH_BUDGET_ITEM.format(month=month),
                    json={"amount": _amount_str(amount)})


def delete_budget(month):
    """DELETE /api/v1/budgets/{month} —— 取消月度预算。"""
    if is_demo_mode():
        return _demo_api().delete_budgets(month)
    return _request("DELETE", config.PATH_BUDGET_ITEM.format(month=month))


def save_budgets(payload):
    """兼容旧页面入口：从旧 payload 提取 month / 总预算，调用 v1 契约接口。"""
    payload = payload or {}
    month = payload.get("month")
    amount = payload.get("amount")
    if amount is None and payload.get("total_budget_cents") is not None:
        amount = Decimal(str(payload["total_budget_cents"])) / Decimal("100")
    if not month:
        raise ApiError(422, "缺少预算月份。")
    return save_budget(month, amount)


def fetch_budget_status(month):
    """兼容 banner 组件：把 v1 预算结构转成 total/level 结构。"""
    if is_demo_mode():
        return _demo_api().fetch_budget_status(month)
    try:
        data = fetch_budgets(month)
    except ApiError as exc:
        if exc.status_code == 404:
            # 未设置预算：banner 显示中性提示，支出取统计总览
            spent = Decimal("0")
            try:
                summary = fetch_stats_summary(month)
                spent = Decimal(str(summary.get("total_amount") or 0))
            except Exception:
                pass
            return {"month": month,
                    "total": {"budget_cents": 0,
                              "spent_cents": int(spent * 100),
                              "ratio": None, "level": None}}
        raise

    amount = Decimal(str(data.get("amount") or 0))
    spent = Decimal(str(data.get("spent") or 0))
    usage = data.get("usage_percent")
    if usage is not None:
        ratio = float(usage) / 100
    else:
        ratio = float(spent / amount) if amount else 0.0
    level = {"normal": "normal", "warning": "warn", "exceeded": "over"}.get(
        data.get("status"))

    return {"month": month,
            "total": {"budget_cents": int(amount * 100),
                      "spent_cents": int(spent * 100),
                      "ratio": ratio,
                      "level": level}}
