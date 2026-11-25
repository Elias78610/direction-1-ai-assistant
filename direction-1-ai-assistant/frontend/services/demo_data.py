# -*- coding: utf-8 -*-
"""
内置示例数据模块（DEMO_MODE 兜底 · Agent3 接口对接阶段从 api_client.py 迁入）

用途：
  后端 FastAPI 未启动时的答辩/演示兜底。DEMO_MODE 开启时，
  services/api_client.py 的全部接口函数转由本模块提供数据，页面层完全无感知
  （函数签名与返回值结构和真实后端响应 JSON 保持一致）。

注意：
  - 本模块不含任何真实后端 / LLM / DB 逻辑，纯内存假数据（应用重启即重置）；
  - 演示流水按「今天」动态生成近 6 个月数据，保证任意日期演示都有内容；
  - 演示预算按本月 mock 支出反推，使用率稳定落在 80%~100%（黄色预警区间），
    便于演示预算 banner 效果；餐饮分类预算故意设低，演示分类超支场景；
  - 演示模式下增/删/改操作全部在内存中生效，侧边栏 / 列表 / 图表随之联动。
"""

import re
from datetime import date, datetime, timedelta

import config
from services.api_client import ApiError

# ─────────────────────────────────────────────
# 固定演示分类（与需求文档约定的 9 个一级类目一致）
# ─────────────────────────────────────────────
_MOCK_CATEGORIES = [
    {"id": 1, "name": "餐饮", "parent_id": None, "sort_order": 1},
    {"id": 2, "name": "交通", "parent_id": None, "sort_order": 2},
    {"id": 3, "name": "购物", "parent_id": None, "sort_order": 3},
    {"id": 4, "name": "居家日用", "parent_id": None, "sort_order": 4},
    {"id": 5, "name": "娱乐休闲", "parent_id": None, "sort_order": 5},
    {"id": 6, "name": "医疗健康", "parent_id": None, "sort_order": 6},
    {"id": 7, "name": "学习教育", "parent_id": None, "sort_order": 7},
    {"id": 8, "name": "人情往来", "parent_id": None, "sort_order": 8},
    {"id": 9, "name": "其他", "parent_id": None, "sort_order": 9},
]
_CAT_NAME = {c["id"]: c["name"] for c in _MOCK_CATEGORIES}

# ─────────────────────────────────────────────
# 内存假流水（页面增删改会读写它，模拟后端数据库）
# ─────────────────────────────────────────────
_MOCK_TX = []
_NEXT_ID = 1


def _seed_mock_tx():
    """按「今天」动态生成近 6 个月的演示流水（含收入），保证任何一天演示都有数据。

    行结构：(days_ago, amount_cents, direction, category_id, merchant, note, source)
    """
    rows = [
        (0, 3500, "expense", 1, "星巴克", "拿铁 + 蛋糕", "text"),
        (1, 12000, "expense", 1, "海底捞", "朋友聚餐", "manual"),
        (2, 8800, "expense", 2, "滴滴出行", "打车上班", "text"),
        (3, 29900, "expense", 3, "优衣库", "秋装卫衣", "receipt"),
        (4, 4500, "expense", 1, "全家便利店", "早餐", "receipt"),
        (6, 5600, "expense", 4, "盒马鲜生", "水果蔬菜", "text"),
        (9, 15000, "expense", 5, "万达影城", "电影双人票", "manual"),
        (12, 26000, "expense", 6, "社区医院", "感冒药", "manual"),
        (15, 49900, "expense", 7, "京东图书", "专业书籍", "text"),
        (18, 20000, "expense", 8, "随份子", "同学婚礼", "manual"),
        (25, 36000, "expense", 3, "京东", "机械键盘", "text"),
        (32, 7000, "expense", 1, "麦当劳", "午餐", "text"),
        (40, 95000, "expense", 4, "宜家", "台灯 + 收纳", "receipt"),
        (55, 20000, "expense", 2, "高铁票", "回家往返", "text"),
        (75, 12000, "expense", 5, "腾讯视频", "季度会员", "text"),
        (95, 58000, "expense", 7, "B站课程", "网课年卡", "manual"),
        (120, 88000, "expense", 3, "Apple", "AirPods", "receipt"),
        (150, 16000, "expense", 1, "喜茶", "下午茶", "text"),
        (1, 800000, "income", None, "公司", "本月工资", "manual"),
        (33, 800000, "income", None, "公司", "上月工资", "manual"),
        (64, 800000, "income", None, "公司", "前月工资", "manual"),
    ]
    t = date.today()
    out = []
    for i, (days_ago, amount, direction, cat_id, merchant, note, source) in enumerate(rows, start=1):
        out.append({
            "id": i,
            "amount_cents": amount,
            "occurred_at": (t - timedelta(days=days_ago)).isoformat(),
            "direction": direction,
            "category_id": cat_id,
            "category_name": _CAT_NAME.get(cat_id, ""),
            "merchant": merchant,
            "note": note,
            "source": source,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
    return out


_MOCK_TX = _seed_mock_tx()
_NEXT_ID = max(t["id"] for t in _MOCK_TX) + 1

# 已保存的预算（按月份键）；未保存过的月份使用 _default_budget 生成的演示预算
_MOCK_BUDGETS = {}


def _default_budget(month_key):
    """演示预算：总预算按本月 mock 支出反推，使使用率落在 80%~100% 黄色预警区间。"""

    def month_expense(cat_id=None):
        s = 0
        for tx in _MOCK_TX:
            if tx["direction"] != "expense" or not tx["occurred_at"].startswith(month_key):
                continue
            if cat_id is None or tx["category_id"] == cat_id:
                s += tx["amount_cents"]
        return s

    spent = month_expense()
    total = max(int(spent / 0.85) if spent else 300000, 10000)
    food = month_expense(1)
    return {
        "month": month_key,
        "total_budget_cents": total,
        "category_budgets": [
            {"category_id": 1, "budget_cents": max(int(food * 0.8), 5000) if food else 80000},
            {"category_id": 2, "budget_cents": 30000},
            {"category_id": 3, "budget_cents": 50000},
        ],
    }


def _in_range(occurred_at, start_date, end_date):
    """判断日期字符串是否落在 [start_date, end_date] 区间内（含边界）。"""
    if start_date and occurred_at < start_date:
        return False
    if end_date and occurred_at > end_date:
        return False
    return True


# ─────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────

def check_health():
    """GET /health —— 演示模式恒返回 ok（version 标记 demo）。"""
    return {"status": "ok", "version": "demo"}


# ─────────────────────────────────────────────
# 分类
# ─────────────────────────────────────────────

def fetch_categories():
    """GET /api/categories —— 返回固定 9 个一级类目。"""
    return {"categories": list(_MOCK_CATEGORIES)}


# ─────────────────────────────────────────────
# 自然语言记账解析
# ─────────────────────────────────────────────

def parse_transaction_text(text, direction="expense"):
    """POST /api/transactions/parse —— 演示版解析（提取数字当金额，非真实 NLP）。"""
    text = (text or "").strip()
    if not text:
        raise ApiError(400, "请先输入一句话，例如「昨天在星巴克喝咖啡花了 35」。")
    m = re.search(r"(\d+(?:\.\d{1,2})?)", text)
    if not m:
        raise ApiError(400, "抱歉，没有从这句话里识别出金额，请换一种说法，或改用手动录入。")
    amount_yuan = float(m.group(1))
    if amount_yuan <= 0:
        raise ApiError(400, "识别出的金额无效，请核对后重试，或改用手动录入。")
    draft = {
        "amount_cents": int(round(amount_yuan * 100)),
        "occurred_at": (date.today() - timedelta(days=1)).isoformat(),
        "direction": direction or "expense",
        "category_id": 1,
        "category_name": "餐饮",
        "merchant": text.replace(m.group(1), "").strip()[:16] or "（未识别商户）",
        "note": "",
        "confidence": 0.92,
    }
    return {"draft": draft, "raw_input": text}


# ─────────────────────────────────────────────
# 流水创建 / 列表 / 编辑 / 删除
# ─────────────────────────────────────────────

def create_transaction(payload):
    """POST /api/transactions —— 写入内存假数据（页面各区块随之联动）。"""
    global _NEXT_ID
    payload = payload or {}
    tx = {
        "id": _NEXT_ID,
        "amount_cents": int(payload.get("amount_cents") or 0),
        "occurred_at": payload.get("occurred_at") or date.today().isoformat(),
        "direction": payload.get("direction") or "expense",
        "category_id": payload.get("category_id"),
        "category_name": _CAT_NAME.get(payload.get("category_id"), ""),
        "merchant": payload.get("merchant") or "",
        "note": payload.get("note") or "",
        "source": payload.get("source") or "manual",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _NEXT_ID += 1
    _MOCK_TX.append(tx)
    return {"transaction": tx}


def fetch_transactions(start_date=None, end_date=None, category_id=None,
                       direction=None, limit=200, offset=0):
    """GET /api/transactions —— 内存过滤 + 按日期倒序。"""
    rows = [t for t in _MOCK_TX
            if _in_range(t["occurred_at"], start_date, end_date)
            and (category_id is None or t["category_id"] == category_id)
            and (direction in (None, "", "全部") or t["direction"] == direction)]
    rows = sorted(rows, key=lambda t: (t["occurred_at"], t["id"]), reverse=True)
    total = len(rows)
    return {"transactions": rows[offset:offset + limit],
            "total": total, "limit": limit, "offset": offset}


def update_transaction(tx_id, payload):
    """PUT /api/transactions/{id} —— 更新内存假数据（可部分更新）。"""
    for t in _MOCK_TX:
        if t["id"] == tx_id:
            for k in ("amount_cents", "occurred_at", "direction",
                      "category_id", "merchant", "note"):
                if k in payload:
                    t[k] = payload[k]
            t["category_name"] = _CAT_NAME.get(t.get("category_id"), "")
            return {"transaction": t}
    raise ApiError(404, "这笔流水不存在，可能已被删除，请刷新列表。")


def delete_transaction(tx_id):
    """DELETE /api/transactions/{id} —— 从内存移除。"""
    for t in _MOCK_TX:
        if t["id"] == tx_id:
            _MOCK_TX.remove(t)
            return {"deleted": True, "id": tx_id}
    raise ApiError(404, "这笔流水不存在，可能已被删除，请刷新列表。")


# ─────────────────────────────────────────────
# 小票 OCR 识别
# ─────────────────────────────────────────────

def ocr_receipt(file_bytes, filename=""):
    """POST /api/receipts/ocr —— 演示版不真正识别图片，返回固定低置信度草稿。"""
    name = (filename or "").lower()
    if not file_bytes:
        raise ApiError(400, "请先选择一张小票图片。")
    if not name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise ApiError(400, "仅支持 jpg / png / webp 格式的图片。")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise ApiError(400, "图片大小不能超过 10MB。")
    occurred = (date.today() - timedelta(days=1)).isoformat()
    return {
        "receipt_id": 1001,
        "draft": {
            "amount_cents": 4500,
            "occurred_at": occurred,
            "direction": "expense",
            "category_id": 1,
            "category_name": "餐饮",
            "merchant": "全家便利店",
            "note": "",
            "confidence": 0.61,
        },
        "ocr_raw": (f"全家便利店 FAMILY MART\n"
                    f"商品合计：¥45.00\n实付金额：¥45.00\n找零：¥0.00\n"
                    f"收银员：0032\n时间：{occurred} 08:12:33"),
        "warnings": ["金额识别不确定，请核对"],
        "duplicate_hint": False,
    }


# ─────────────────────────────────────────────
# 统计：概览 / 分类占比 / 月度趋势
# ─────────────────────────────────────────────

def fetch_stats_summary(month):
    """GET /api/stats/summary?month=YYYY-MM —— 内存汇总本月收支。"""
    income = expense = cnt = 0
    for t in _MOCK_TX:
        if t["occurred_at"].startswith(month):
            cnt += 1
            if t["direction"] == "income":
                income += t["amount_cents"]
            else:
                expense += t["amount_cents"]
    return {"month": month, "income_cents": income, "expense_cents": expense,
            "balance_cents": income - expense, "transaction_count": cnt}


def fetch_stats_category(start_date=None, end_date=None, direction="expense"):
    """GET /api/stats/category —— 内存按分类聚合（ratio 计算好返回，按金额降序）。"""
    bucket = {}
    for t in _MOCK_TX:
        if t["direction"] != direction or not _in_range(t["occurred_at"], start_date, end_date):
            continue
        bucket[t["category_id"]] = bucket.get(t["category_id"], 0) + t["amount_cents"]
    total = sum(bucket.values())
    items = [{"category_id": cid, "category_name": _CAT_NAME.get(cid, "未分类"),
              "amount_cents": amt, "ratio": round(amt / total, 4) if total else 0.0}
             for cid, amt in sorted(bucket.items(), key=lambda kv: -kv[1])]
    return {"total_cents": total, "items": items}


def fetch_stats_monthly(months=6, direction="expense"):
    """GET /api/stats/monthly —— 内存按月份聚合（月份连续、空月补 0）。"""
    t = date.today()
    items = []
    for back in range(months - 1, -1, -1):
        y, m = t.year, t.month - back
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        amount, cnt = 0, 0
        for tx in _MOCK_TX:
            if tx["direction"] == direction and tx["occurred_at"].startswith(key):
                amount += tx["amount_cents"]
                cnt += 1
        items.append({"month": key, "amount_cents": amount, "transaction_count": cnt})
    return {"items": items}


# ─────────────────────────────────────────────
# 自然语言查账
# ─────────────────────────────────────────────

def query_accounts(question):
    """POST /api/query —— 演示版按关键词映射到内存统计本月支出（非真实 LLM+SQL）。"""
    q = (question or "").strip()
    if not q:
        raise ApiError(400, "请先输入要查询的问题。")
    t = date.today()
    start, end = t.replace(day=1).isoformat(), t.isoformat()

    if "餐饮" in q or "吃" in q or "饭" in q:
        cids = [1]
    elif "交通" in q or "出行" in q or "打车" in q:
        cids = [2]
    elif "购物" in q or "买" in q:
        cids = [3]
    else:
        cids = None  # 未命中关键词：统计本月全部支出

    bucket = {}
    for tx in _MOCK_TX:
        if tx["direction"] != "expense" or not _in_range(tx["occurred_at"], start, end):
            continue
        if cids and tx["category_id"] not in cids:
            continue
        cid = tx["category_id"] or 0
        r = bucket.setdefault(cid, {"category_name": _CAT_NAME.get(cid, "其他"),
                                    "amount_cents": 0, "transaction_count": 0})
        r["amount_cents"] += tx["amount_cents"]
        r["transaction_count"] += 1

    rows = [[r["category_name"], r["amount_cents"], r["transaction_count"]]
            for r in bucket.values()]
    rows.sort(key=lambda r: -r[1])
    total_cents = sum(r[1] for r in rows)
    total_cnt = sum(r[2] for r in rows)
    label = "、".join(_CAT_NAME.get(c, "其他") for c in cids) if cids else "全部支出"
    answer = (f"{t.year} 年 {t.month} 月，{label}类共支出 ¥{total_cents / 100:,.2f}，"
              f"共 {total_cnt} 笔。")
    return {"answer": answer,
            "time_range": {"start": start, "end": end},
            "table": {"columns": ["category_name", "amount_cents", "transaction_count"],
                      "rows": rows}}


# ─────────────────────────────────────────────
# 预算查询 / 设置 / 状态
# ─────────────────────────────────────────────

def fetch_budgets(month):
    """GET /api/v1/budgets/{month} —— 演示预算，返回 v1 结构。"""
    raw = _budgets_with_status(month)
    total = raw["items"][0]
    amount = total["budget_cents"] / 100
    spent = total["spent_cents"] / 100
    remaining = amount - spent
    ratio = total["ratio"]
    if ratio is None:
        status = "normal"
        usage = 0.0
    elif ratio > 1:
        status = "exceeded"
        usage = ratio * 100
    elif ratio >= config.BUDGET_WARN_RATIO:
        status = "warning"
        usage = ratio * 100
    else:
        status = "normal"
        usage = ratio * 100
    return {"month": month,
            "amount": f"{amount:.2f}",
            "spent": f"{spent:.2f}",
            "remaining": f"{remaining:.2f}",
            "usage_percent": round(usage, 2),
            "status": status,
            "message": ""}


def save_budgets(payload):
    """PUT /api/budgets —— 写入内存预算（重复 PUT 视为更新）。"""
    payload = payload or {}
    month = payload.get("month") or date.today().strftime("%Y-%m")
    _MOCK_BUDGETS[month] = {
        "month": month,
        "total_budget_cents": int(payload.get("total_budget_cents") or 0),
        "category_budgets": [{"category_id": int(c["category_id"]),
                              "budget_cents": int(c.get("budget_cents") or 0)}
                             for c in (payload.get("category_budgets") or [])],
    }
    return _budgets_with_status(month)


def delete_budgets(month):
    """DELETE —— 演示中把该月预算置为 0。

    不能直接 pop，否则 _budgets_with_status 会回落到默认演示预算，
    看起来像「取消没生效」。
    """
    _MOCK_BUDGETS[month] = {
        "month": month,
        "total_budget_cents": 0,
        "category_budgets": [],
    }
    return {}


def _budgets_with_status(month):
    """按月份键组装「预算 + 执行情况」的完整结构（spent/ratio 计算好返回）。"""
    b = _MOCK_BUDGETS.get(month) or _default_budget(month)
    cat_map = {c["category_id"]: c["budget_cents"] for c in b["category_budgets"]}
    spent_map, total_spent = {}, 0
    for tx in _MOCK_TX:
        if tx["direction"] == "expense" and tx["occurred_at"].startswith(month):
            cid = tx["category_id"]
            spent_map[cid] = spent_map.get(cid, 0) + tx["amount_cents"]
            total_spent += tx["amount_cents"]

    items = [{"category_id": None, "category_name": "总预算",
              "budget_cents": b["total_budget_cents"], "spent_cents": total_spent,
              "ratio": round(total_spent / b["total_budget_cents"], 4)
              if b["total_budget_cents"] else None}]
    for cat in _MOCK_CATEGORIES:
        budget = cat_map.get(cat["id"], 0)
        spent = spent_map.get(cat["id"], 0)
        items.append({"category_id": cat["id"], "category_name": cat["name"],
                      "budget_cents": budget, "spent_cents": spent,
                      "ratio": round(spent / budget, 4) if budget else None})
    return {"month": month, "total_budget_cents": b["total_budget_cents"], "items": items}


def fetch_budget_status(month):
    """GET /api/budgets/status?month=YYYY-MM —— 总预算执行状态（含 level）。"""
    b = _budgets_with_status(month)
    total = b["items"][0]
    ratio = total["ratio"]
    if ratio is None:
        level = None
    elif ratio >= config.BUDGET_OVER_RATIO:
        level = "over"
    elif ratio >= config.BUDGET_WARN_RATIO:
        level = "warn"
    else:
        level = "normal"
    return {"month": month,
            "total": {"budget_cents": total["budget_cents"],
                      "spent_cents": total["spent_cents"],
                      "ratio": ratio, "level": level}}
