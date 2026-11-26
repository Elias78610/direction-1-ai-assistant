# -*- coding: utf-8 -*-
"""
预算提醒组件（仅负责展示，不计算业务金额）
==========================================
输入来自 app.py 的预算快照，字段与后端 BudgetOut 一致：
    amount / spent / remaining / usage_percent / status / message

展示规则（与后端 BudgetService 保持一致）：
  - normal     不显示提醒，保持原页面干净；
  - warning    ≥80% 且未超过预算，黄色渐变提醒；
  - exceeded   超过预算，红色渐变提醒，并展示超支金额；
  - 超支超过 20%（usage ≥ 120%）时升级为深红色，提示「超太多了」；
  - 未设置预算 / 接口失败不显示，避免误导。

颜色只作用于本组件生成的 .budget-alert，不修改全局 CSS、侧边栏或聊天布局。
"""

import html

import streamlit as st

_CSS = """
<style>
.budget-alert {
  display: flex;
  align-items: flex-start;
  gap: .55rem;
  width: 100%;
  margin: 0 0 .85rem 0;
  padding: .72rem .92rem;
  border: 1px solid transparent;
  border-radius: 12px;
  font-size: .86rem;
  line-height: 1.55;
  box-shadow: 0 4px 12px rgba(17, 24, 39, .05);
}
.budget-alert-icon { flex: 0 0 auto; line-height: 1.45; }
.budget-alert-text { flex: 1 1 auto; white-space: pre-wrap; }
.budget-alert-warning {
  background: linear-gradient(90deg, #FFF9E5 0%, #FDE68A 100%);
  border-color: #F3D26B;
  color: #92400E;
}
.budget-alert-exceeded {
  background: linear-gradient(90deg, #FEE2E2 0%, #F87171 100%);
  border-color: #FCA5A5;
  color: #7F1D1D;
}
.budget-alert-severe {
  background: linear-gradient(90deg, #DC2626 0%, #7F1D1D 100%);
  border-color: #991B1B;
  color: #FFFFFF;
}
</style>
"""


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
        over = abs(remaining)
        if usage >= 120:
            return f"本月已超支 {over:.2f} 元，超出预算 20% 以上，请立即控制支出"
        return f"本月已超支 {over:.2f} 元"
    if snapshot.get("status") == "warning":
        return f"本月预算已使用 {usage:.2f}%，注意控制支出"
    return ""


def _style_for(snapshot: dict) -> tuple:
    """返回 (css_class, emoji, aria_label)。"""
    status = snapshot.get("status")
    usage = float(snapshot.get("usage_percent") or 0)
    if status == "warning":
        return "budget-alert-warning", "⚠️", "预算预警"
    if status == "exceeded":
        if usage >= 120:
            return "budget-alert-severe", "🚨", "严重超支"
        return "budget-alert-exceeded", "🚨", "预算超支"
    return "", "", ""


def render(snapshot: dict) -> None:
    """渲染预算提醒；normal / 未设置预算时不占用页面空间。"""
    snapshot = snapshot or {}
    if snapshot.get("missing"):
        return

    status = snapshot.get("status")
    if status not in ("warning", "exceeded"):
        return

    message = _message(snapshot)
    if not message:
        return

    css_class, emoji, aria_label = _style_for(snapshot)
    safe_message = html.escape(message)
    alert_html = (
        f'<div class="budget-alert {css_class}" role="alert" '
        f'aria-label="{aria_label}">'
        f'<span class="budget-alert-icon" aria-hidden="true">{emoji}</span>'
        f'<span class="budget-alert-text">{safe_message}</span>'
        "</div>"
    )
    st.markdown(_CSS + alert_html, unsafe_allow_html=True)
