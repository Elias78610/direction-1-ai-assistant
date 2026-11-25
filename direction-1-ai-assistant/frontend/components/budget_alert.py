# -*- coding: utf-8 -*-
"""
预算提醒组件（仅负责展示，不计算业务金额）
==========================================
输入来自 app.py 的预算快照，字段与后端 BudgetOut 一致：
    amount / spent / remaining / usage_percent / status / message

展示规则（与后端 BudgetService 保持一致）：
  - normal     不显示提醒，保持原页面干净；
  - warning    ≥80% 且未超过预算，黄色 st.warning；
  - exceeded   超过预算，红色 st.error，并展示超支金额；
  - 未设置预算 / 接口失败不显示，避免误导。

该组件不修改侧边栏、聊天布局或全局 CSS。
"""

import streamlit as st


def _message(snapshot: dict) -> str:
    """优先使用后端 message；缺失时按契约字段兜底。"""
    message = (snapshot.get("message") or "").strip()
    if message:
        return message

    amount = float(snapshot.get("amount") or 0)
    spent = float(snapshot.get("spent") or 0)
    remaining = float(snapshot.get("remaining") or (amount - spent))
    usage = float(snapshot.get("usage_percent") or 0)
    if snapshot.get("status") == "exceeded":
        return f"本月已超支 {abs(remaining):.2f} 元"
    if snapshot.get("status") == "warning":
        return f"本月预算已使用 {usage:.2f}%，注意控制支出"
    return ""


def render(snapshot: dict) -> None:
    """渲染预算提醒；normal / 未设置预算时不占用页面空间。"""
    snapshot = snapshot or {}
    if snapshot.get("missing"):
        return

    status = snapshot.get("status")
    message = _message(snapshot)

    if status == "warning":
        st.warning(f"⚠️ {message}")
    elif status == "exceeded":
        st.error(f"⚠️ {message}")
