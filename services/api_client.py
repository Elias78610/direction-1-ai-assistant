# -*- coding: utf-8 -*-
"""
API 客户端（真实 HTTP 版 · Agent3 接口对接阶段实现）
======================================================

职责边界：
  - 本文件是「页面层」与「后端 FastAPI」之间的唯一通信通道；
  - 所有函数签名与返回值结构严格对齐 docs/需求与接口梳理.md 第 3 节
    （推导默认值，最终以后端 /docs 为准；路径常量统一收口在 config.py）；
  - 统一处理：基地址拼接（get_base_url：运行时覆盖 > 环境变量 > config 默认值）、
    超时分级（普通 10s / LLM 60s / OCR 120s，见 config.py）、
    网络/超时/HTTP/业务错误分类（统一抛 ApiError，页面层按 kind 分级友好展示）、
    FastAPI 422 校验错误定位、错误结构兼容（detail / code+message / error）；
  - DEMO_MODE 开启（config.DEMO_MODE / 环境变量 LEDGER_DEMO_MODE /
    侧边栏「高级设置」运行时勾选）时，全部函数自动切换到内置示例数据
    （services/demo_data.py），页面代码零感知，供后端未启动时的答辩演示兜底。

页面层约定（对 sections/ 与 components/ 的承诺，签名不变）：
  所有函数签名与 Agent2 mock 版完全一致，页面代码无需任何修改。
"""

import requests

import config


class ApiError(Exception):
    """统一的接口异常：页面层捕获后按 kind 分级展示友好提示。"""

    def __init__(self, status_code=0, detail="", kind="http"):
        super().__init__(detail or f"接口调用失败（状态码 {status_code}）")
        self.status_code = status_code
        self.detail = detail
        self.kind = kind  # http / network / timeout


def get_base_url():
    """当前生效的后端地址。

    优先级（与 config.py 约定一致）：
      运行时覆盖 st.session_state["api_base_url"] > 环境变量 > config 默认值。
    所有请求 URL 统一由本函数 + config.PATH_* 拼接，页面禁止硬编码。
    """
    try:
        import streamlit as st
        override = st.session_state.get("api_base_url", "")
    except Exception:
        override = ""
    return (override or config.API_BASE_URL).strip().rstrip("/")


def is_demo_mode():
    """演示模式是否生效。

    优先级：
      st.session_state["demo_mode"]（侧边栏「高级设置」勾选）
      > 环境变量 LEDGER_DEMO_MODE > config.DEMO_MODE（默认 False）。
    演示模式下所有接口返回内置示例数据，不发任何真实 HTTP 请求。
    """
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
    """拼接完整 URL（禁止页面硬编码 URL，一律从本函数 + config 取值）。"""
    return get_base_url() + path


def _extract_error_detail(resp):
    """从错误响应体提取友好文案（兼容 detail / code+message / error / 422 结构）。"""
    try:
        body = resp.json()
    except ValueError:
        body = None

    # FastAPI 422：{"detail": [{"loc": [...], "msg": "..."}]} → 定位到具体字段
    if resp.status_code == 422 and isinstance(body, dict) \
            and isinstance(body.get("detail"), list):
        items = [d for d in body["detail"] if isinstance(d, dict)]
        if items:
            first = items[0]
            loc = ".".join(str(x) for x in first.get("loc", [])
                           if x not in ("body", "query", "path", "json"))
            msg = first.get("msg") or "校验失败"
            if loc:
                return f"输入格式有误：字段 {loc} {msg}。"
            return f"输入格式有误：{msg}。"

    if isinstance(body, dict):
        if isinstance(body.get("detail"), str) and body["detail"].strip():
            return body["detail"]
        if body.get("message"):
            return str(body["message"])
        if body.get("error"):
            return str(body["error"])

    # 通用状态码文案兜底
    if resp.status_code in (502, 503):
        return "AI 服务暂不可用，请稍后重试，或改用手动录入。"
    if resp.status_code >= 500:
        return "服务开小差了，请稍后重试。"
    return f"请求失败（HTTP {resp.status_code}），请稍后重试。"


def _check_response(resp):
    """2xx → 解析后的 JSON（204 无响应体时返回 {}）；否则抛 ApiError(kind="http")。"""
    if 200 <= resp.status_code < 300:
        if resp.status_code == 204:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}
    raise ApiError(resp.status_code, _extract_error_detail(resp), kind="http")


def _request(method, path, timeout=None, **kwargs):
    """统一请求入口：超时分级 + 网络异常分类（连接失败/超时）+ 业务错误转 ApiError。

    参数：
      method    HTTP 方法（GET/POST/PUT/DELETE）
      path      config.PATH_* 中的路径常量
      timeout   超时秒数，缺省用 config.REQUEST_TIMEOUT（10s）
      kwargs    透传给 requests（json= / params= / files= 等）
    """
    try:
        resp = requests.request(method, _url(path),
                                timeout=timeout or config.REQUEST_TIMEOUT,
                                **kwargs)
    except requests.exceptions.Timeout:
        raise ApiError(0, "请求超时（后端处理时间过长），请稍后重试。", kind="timeout")
    except requests.exceptions.ConnectionError:
        raise ApiError(0, "无法连接后端服务，请确认服务已启动。", kind="network")
    except requests.exceptions.RequestException:
        raise ApiError(0, "无法连接后端服务，请确认服务已启动。", kind="network")
    return _check_response(resp)


# ═══════════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════════

def check_health():
    """健康检查 —— GET /health（无入参，普通超时 10s）

    出参（200）：{"status": "ok", "version": "0.1.0"}
    用途：应用启动时探测后端连通性；失败时首页显示「无法连接后端服务」引导页。
    需后端配合：/health 无需鉴权、响应应 <1s；version 字段可选。
    """
    if is_demo_mode():
        return _demo_api().check_health()
    return _request("GET", config.PATH_HEALTH)


# ═══════════════════════════════════════════════════════════════════
# 分类
# ═══════════════════════════════════════════════════════════════════

def fetch_categories():
    """分类列表 —— GET /api/categories（无入参，普通超时）

    出参（200）：{"categories": [{"id", "name", "parent_id", "sort_order"}, ...]}
    用途：记一笔 / 编辑 / 筛选 / 预算设置中的分类下拉与表格；不硬编码在页面里。
    需后端配合：返回全部一级（及可选二级）类目；parent_id 为空表示一级类目；
    若含二级类目，前端下拉暂按平铺展示（层级展示可后续增强）。
    """
    if is_demo_mode():
        return _demo_api().fetch_categories()
    return _request("GET", config.PATH_CATEGORIES)


# ═══════════════════════════════════════════════════════════════════
# 自然语言记账解析
# ═══════════════════════════════════════════════════════════════════

def parse_transaction_text(text, direction="expense"):
    """自然语言记账解析 —— POST /api/transactions/parse（LLM 超时 60s）

    入参 JSON：{"text": "昨天在星巴克喝咖啡花了35", "direction": "expense"}
    出参（200）：{"draft": {"amount_cents", "occurred_at", "direction", "category_id",
                            "category_name", "merchant", "note", "confidence"},
                  "raw_input": "..."}
    错误：400 文本为空 / 无法解析（页面自动降级为手动录入）。
    需后端配合：amount_cents 为整数分、occurred_at 为 YYYY-MM-DD、
    direction ∈ expense/income、category_id 必须能在 /api/categories 中找到、
    confidence ∈ [0,1]；无法确定的字段返回 null 而不是猜测。
    """
    if is_demo_mode():
        return _demo_api().parse_transaction_text(text, direction)
    payload = {"text": text, "direction": direction or "expense"}
    return _request("POST", config.PATH_TRANSACTION_PARSE,
                    timeout=config.LLM_REQUEST_TIMEOUT, json=payload)


# ═══════════════════════════════════════════════════════════════════
# 流水创建（text / receipt / manual 三来源统一入口）
# ═══════════════════════════════════════════════════════════════════

def create_transaction(payload):
    """创建流水 —— POST /api/transactions（普通超时）

    入参 JSON：{"amount_cents", "occurred_at", "direction", "category_id", "merchant",
                "note", "source", "raw_input", "confidence", "receipt_id"}
    出参（201）：{"transaction": {"id", "amount_cents", "occurred_at", "direction",
                                  "category_id", "category_name", "merchant", "note",
                                  "source", "created_at"}}
    错误：400 疑似重复（页面弹「是否仍要添加」）/ 422 字段校验失败。
    需后端配合：source 取值 text/receipt/manual；OCR 来源带 receipt_id、其余传 null；
    返回体必须回填 id 与 category_name（列表/图表渲染依赖）。
    """
    if is_demo_mode():
        return _demo_api().create_transaction(payload)
    return _request("POST", config.PATH_TRANSACTIONS, json=payload or {})


# ═══════════════════════════════════════════════════════════════════
# 流水列表 / 编辑 / 删除
# ═══════════════════════════════════════════════════════════════════

def fetch_transactions(start_date=None, end_date=None, category_id=None,
                       direction=None, limit=200, offset=0):
    """流水列表 —— GET /api/transactions（普通超时）

    入参 Query：start_date、end_date（YYYY-MM-DD，可选）、category_id（可选）、
                direction（expense/income，可选）、limit、offset
    出参（200）：{"transactions": [...], "total": N, "limit": ..., "offset": ...}
    需后端配合：分页参数确认为 limit/offset（若后端实为 page/page_size，
    需同步修改本函数与 docs/接口对接说明.md）；每笔流水必须含
    id/amount_cents/occurred_at/direction/category_id/category_name/
    merchant/note/source 字段；按日期倒序返回。
    """
    if is_demo_mode():
        return _demo_api().fetch_transactions(start_date, end_date, category_id,
                                              direction, limit, offset)
    params = {"start_date": start_date, "end_date": end_date,
              "category_id": category_id, "direction": direction,
              "limit": limit, "offset": offset}
    params = {k: v for k, v in params.items() if v not in (None, "")}
    return _request("GET", config.PATH_TRANSACTIONS, params=params)


def update_transaction(tx_id, payload):
    """编辑流水 —— PUT /api/transactions/{id}（普通超时）

    入参 JSON：与创建入参同构（可部分更新，具体字段以后端 /docs 为准）
    出参（200）：{"transaction": {...}}
    错误：404 不存在 / 422 校验失败。
    需后端配合：tx_id 拼入路径；返回体与列表项结构一致（含 category_name）。
    """
    if is_demo_mode():
        return _demo_api().update_transaction(tx_id, payload)
    return _request("PUT", config.PATH_TRANSACTION_ITEM.format(id=tx_id),
                    json=payload or {})


def delete_transaction(tx_id):
    """删除流水 —— DELETE /api/transactions/{id}（普通超时）

    出参：200 {"deleted": true, "id": 123} 或 204 无响应体
          （本函数统一返回 {"deleted": True, "id": tx_id}，页面无需区分）
    错误：404 不存在。
    需后端配合：200+body 与 204 两种成功返回前端均已兼容。
    """
    if is_demo_mode():
        return _demo_api().delete_transaction(tx_id)
    result = _request("DELETE", config.PATH_TRANSACTION_ITEM.format(id=tx_id))
    return result if result else {"deleted": True, "id": tx_id}


# ═══════════════════════════════════════════════════════════════════
# 小票 OCR 识别
# ═══════════════════════════════════════════════════════════════════

def ocr_receipt(file_bytes, filename=""):
    """小票 OCR 识别 —— POST /api/receipts/ocr（OCR 超时 120s，multipart 上传）

    入参：multipart/form-data，字段 file（图片 jpg/png/webp，≤10MB）
    出参（200）：{"receipt_id", "draft": {...同 parse 草稿结构},
                  "ocr_raw": "...", "warnings": [...], "duplicate_hint": bool}
    错误：400 文件格式/大小不支持；500/503 识别失败（页面降级手动录入）。
    需后端配合：表单字段名必须为 file；draft 结构与 parse 接口一致；
    warnings 为字符串数组（可为空）；duplicate_hint 为 true 时页面要求用户二次确认。
    """
    if is_demo_mode():
        return _demo_api().ocr_receipt(file_bytes, filename)
    # 前端预校验：快速给出友好提示，避免无效上传占用后端（最终校验以后端为准）
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
# 统计：概览 / 分类占比 / 月度趋势
# ═══════════════════════════════════════════════════════════════════

def fetch_stats_summary(month):
    """侧边栏概览 —— GET /api/stats/summary?month=YYYY-MM（普通超时）

    入参 Query：month=YYYY-MM
    出参（200）：{"month", "income_cents", "expense_cents",
                  "balance_cents", "transaction_count"}
    用途：侧边栏「本月收入/支出/结余/笔数」。
    需后端配合：月份参数名确认为 month（若后端用 month_key 等其他参数名，
    需同步修改本函数与 docs/接口对接说明.md）；金额均为整数分，balance 由后端计算。
    """
    if is_demo_mode():
        return _demo_api().fetch_stats_summary(month)
    return _request("GET", config.PATH_STATS_SUMMARY, params={"month": month})


def fetch_stats_category(start_date=None, end_date=None, direction="expense"):
    """消费分类占比 —— GET /api/stats/category（普通超时）

    入参 Query：start_date、end_date（可选）、direction=expense
    出参（200）：{"total_cents": N, "items": [{"category_id", "category_name",
                  "amount_cents", "ratio"}, ...]}（按金额降序）
    用途：消费分类饼图。
    需后端配合：ratio 由后端算好（前端只展示，不自行计算金额）；
    无数据时 items 返回空数组（前端显示「暂无数据」占位）。
    """
    if is_demo_mode():
        return _demo_api().fetch_stats_category(start_date, end_date, direction)
    params = {"start_date": start_date, "end_date": end_date,
              "direction": direction}
    params = {k: v for k, v in params.items() if v not in (None, "")}
    return _request("GET", config.PATH_STATS_CATEGORY, params=params)


def fetch_stats_monthly(months=6, direction="expense"):
    """月度消费趋势 —— GET /api/stats/monthly?months=6&direction=expense（普通超时）

    入参 Query：months=6、direction=expense
    出参（200）：{"items": [{"month": "YYYY-MM", "amount_cents",
                             "transaction_count"}, ...]}
    需后端配合：月份连续、空月补 0（amount_cents=0）由后端保证，前端直接画图。
    """
    if is_demo_mode():
        return _demo_api().fetch_stats_monthly(months, direction)
    return _request("GET", config.PATH_STATS_MONTHLY,
                    params={"months": months, "direction": direction})


# ═══════════════════════════════════════════════════════════════════
# 自然语言查账
# ═══════════════════════════════════════════════════════════════════

def query_accounts(question):
    """自然语言查账 —— POST /api/query（LLM 超时 60s）

    入参 JSON：{"question": "这个月吃饭花了多少"}
    出参（200）：{"answer": "文字回答", "time_range": {"start", "end"},
                  "table": {"columns": [...], "rows": [[...]]}}
    错误：400 无法解析 / 超出记账范围（detail 为友好拒绝文案，页面直接展示）。
    需后端配合：answer 为面向用户的文字回答；table.columns 与 rows 行列对齐；
    金额数字全部来自后端统计，前端只展示 answer 与 table，绝不自行计算。
    """
    if is_demo_mode():
        return _demo_api().query_accounts(question)
    return _request("POST", config.PATH_QUERY,
                    timeout=config.LLM_REQUEST_TIMEOUT,
                    json={"question": question})


# ═══════════════════════════════════════════════════════════════════
# 预算查询 / 设置 / 状态
# ═══════════════════════════════════════════════════════════════════

def fetch_budgets(month):
    """查询某月预算（含执行情况）—— GET /api/budgets?month=YYYY-MM（普通超时）

    出参（200）：{"month", "total_budget_cents", "items": [
                  {"category_id", "category_name", "budget_cents",
                   "spent_cents", "ratio"}, ...]}
    约定：首行 category_id=null 为总预算；未设置分类的 budget_cents=0；
    spent/ratio 由后端计算（预算为 0 时 ratio 返回 null）。
    需后端配合：items 顺序稳定（总预算行在前），category_name 由后端回填。
    """
    if is_demo_mode():
        return _demo_api().fetch_budgets(month)
    return _request("GET", config.PATH_BUDGETS, params={"month": month})


def save_budgets(payload):
    """设置/更新某月预算 —— PUT /api/budgets（普通超时，重复 PUT 视为更新）

    入参 JSON：{"month": "YYYY-MM", "total_budget_cents": N,
                "category_budgets": [{"category_id", "budget_cents"}, ...]}
    出参（200）：与 GET /api/budgets 同结构。
    需后端配合：PUT 语义为「整月覆盖更新」，重复 PUT 不产生重复记录；
    0 表示该分类不设置预算。
    """
    if is_demo_mode():
        return _demo_api().save_budgets(payload)
    return _request("PUT", config.PATH_BUDGETS, json=payload or {})


def fetch_budget_status(month):
    """预算执行状态 —— GET /api/budgets/status?month=YYYY-MM（普通超时）

    出参（200）：{"month", "total": {"budget_cents", "spent_cents", "ratio", "level"}}
    level 建议取值 normal / warn / over；若后端不返回 level 或取值不合约定，
    页面按 ratio 与 config 阈值（0.8 / 1.0）自行判断配色。
    需后端配合：本月未设置预算时 budget_cents=0（页面显示「本月未设置预算」）；
    ratio 由后端计算（spent/budget），预算为 0 时返回 null。
    """
    if is_demo_mode():
        return _demo_api().fetch_budget_status(month)
    return _request("GET", config.PATH_BUDGET_STATUS, params={"month": month})
