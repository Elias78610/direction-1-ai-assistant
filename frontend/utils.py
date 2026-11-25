# -*- coding: utf-8 -*-
"""
通用工具函数（Agent2 UI 开发阶段创建）

全局约定（见 docs/需求与接口梳理.md 第 0 节）：
  - 金额一律整数「分」（amount_cents），展示时 ÷100 为元；
  - 日期一律 ISO 格式 YYYY-MM-DD；
  - 本文件只放纯工具函数，不含任何网络请求与业务逻辑。
"""

from datetime import date, timedelta


# ─────────────────────────────────────────────
# 一、金额换算（元 ↔ 分）
# ─────────────────────────────────────────────

def cents_to_yuan(cents):
    """分 → 元（浮点数，仅用于展示与输入控件）。"""
    return (cents or 0) / 100.0


def yuan_to_cents(yuan):
    """元 → 分（四舍五入取整，提交给后端前调用）。"""
    try:
        return int(round(float(yuan or 0) * 100))
    except (TypeError, ValueError):
        return 0


def format_yuan(cents):
    """分 → 带千分位与两位小数的元字符串，如 123450 → '1,234.50'。"""
    return f"{cents_to_yuan(cents):,.2f}"


# ─────────────────────────────────────────────
# 二、日期工具
# ─────────────────────────────────────────────

def today():
    """今天。单独封装便于演示数据始终新鲜，也便于测试替换。"""
    return date.today()


def today_iso():
    """今天的 ISO 日期字符串 YYYY-MM-DD。"""
    return today().isoformat()


def parse_iso_date(s):
    """把 'YYYY-MM-DD' 解析为 date；失败或为空返回 None。"""
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def current_month_key(d=None):
    """当前（或指定日期）所在月份的键 YYYY-MM，用于概览/预算接口。"""
    return (d or today()).strftime("%Y-%m")


def shift_month_key(month_key, delta):
    """月份键前后移动 delta 个月，如 shift_month_key('2026-11', -1) -> '2026-10'。"""
    year, month = int(month_key[:4]), int(month_key[5:7])
    total = year * 12 + (month - 1) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def month_range(month_key):
    """某月份键 → (该月第一天, 该月最后一天) 两个 date 对象。"""
    year, month = int(month_key[:4]), int(month_key[5:7])
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def range_for_preset(preset):
    """日期筛选快捷项 → (start_iso, end_iso)。

    快捷项：本月 / 上月 / 近3月 / 近6月 / 全部 / 自定义。
    「全部」与「自定义」返回 (None, None)，由调用方自行处理。
    """
    t = today()
    if preset == "本月":
        return t.replace(day=1).isoformat(), t.isoformat()
    if preset == "上月":
        first, last = month_range(shift_month_key(current_month_key(t), -1))
        return first.isoformat(), last.isoformat()
    if preset in ("近3月", "近6月"):
        n = 3 if preset == "近3月" else 6
        start = t.replace(day=1)
        for _ in range(n - 1):
            start = (start - timedelta(days=1)).replace(day=1)
        return start.isoformat(), t.isoformat()
    return None, None


# ─────────────────────────────────────────────
# 三、错误文案（页面层统一调用，保证提示友好一致）
# ─────────────────────────────────────────────

def to_error_message(e):
    """把异常统一转成对用户友好的错误文案（分级：超时/网络/业务 detail/未知）。

    业务错误（ApiError）展示后端 detail；网络异常统一提示检查服务；
    页面层所有 try/except 都应调用本函数，避免直接抛出英文堆栈。
    """
    from services.api_client import ApiError  # 局部导入，避免循环依赖

    if isinstance(e, ApiError):
        if getattr(e, "kind", None) == "timeout":
            return "请求超时了，请稍后重试。"
        if getattr(e, "kind", None) == "network":
            return e.detail or "无法连接后端服务，请确认服务已启动。"
        return e.detail or "操作失败，请稍后重试。"
    return "无法连接后端服务，请确认服务已启动，或到左侧「高级设置」检查后端地址。"
