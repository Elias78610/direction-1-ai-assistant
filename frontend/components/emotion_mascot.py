# -*- coding: utf-8 -*-
"""
情绪小球（全局悬浮桌宠）
========================
固定在页面右下角（bottom: 100px; right: 20px），根据预算使用率切换表情、
背景色和动画：

  ratio < 0.6         🥳 浅绿 呼吸放大（pulse）
  0.6 <= ratio < 0.8  😊 浅蓝 上下浮动（float）
  0.8 <= ratio < 1.0  😅 浅黄 左右摇晃（shake）
  ratio >= 1.0        😭 浅红 红色光晕 + 抖动

通过 st.markdown 注入 HTML/CSS，不依赖第三方库；鼠标悬停显示
Tooltip「我是你的记账小助手，随时为你服务~」。
"""

import streamlit as st

_CSS = """
<style>
.emotion-mascot-wrap {
  position: fixed;
  right: 20px;
  bottom: 100px;
  z-index: 9999;
  pointer-events: none;
}
.emotion-mascot {
  position: relative;
  width: 62px;
  height: 62px;
  border-radius: 50%;
  border: 1px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(17, 24, 39, .12);
  pointer-events: auto;
  cursor: default;
  transition: box-shadow .2s ease;
}
.emotion-emoji {
  font-size: 28px;
  line-height: 1;
  user-select: none;
}
.emotion-tooltip {
  position: absolute;
  right: 74px;
  top: 50%;
  transform: translateY(-50%) translateX(6px);
  background: #FFFFFF;
  color: #374151;
  border: 1px solid #EEF1F6;
  border-radius: 10px;
  padding: 7px 11px;
  font-size: .76rem;
  white-space: nowrap;
  box-shadow: 0 6px 18px rgba(17, 24, 39, .08);
  opacity: 0;
  visibility: hidden;
  transition: opacity .18s ease, transform .18s ease, visibility .18s ease;
  pointer-events: none;
}
.emotion-mascot:hover .emotion-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(-50%) translateX(0);
}

/* 各状态动画 */
.emotion-mascot.is-happy { animation: emotionPulse 2.2s ease-in-out infinite; }
.emotion-mascot.is-calm { animation: emotionFloat 3s ease-in-out infinite; }
.emotion-mascot.is-worried { animation: emotionShake 1.4s ease-in-out infinite; }
.emotion-mascot.is-over {
  animation: emotionOverShake .5s linear infinite;
  box-shadow: 0 0 0 10px rgba(239, 68, 68, .14), 0 10px 28px rgba(239, 68, 68, .30);
}

@keyframes emotionPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.12); }
}
@keyframes emotionFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@keyframes emotionShake {
  0%, 100% { transform: rotate(0); }
  25% { transform: rotate(-7deg); }
  75% { transform: rotate(7deg); }
}
@keyframes emotionOverShake {
  0%, 100% { transform: translateX(0) rotate(0); }
  25% { transform: translateX(-3px) rotate(-5deg); }
  75% { transform: translateX(3px) rotate(5deg); }
}

@media (prefers-reduced-motion: reduce) {
  .emotion-mascot { animation: none !important; }
}
</style>
"""


def _state_for(ratio: float):
    """按预算使用率返回 (emoji, css_class, 背景色, 边框色)。"""
    if ratio < 0.6:
        return "🥳", "is-happy", "#E7F8EF", "#BFE8D2"
    if ratio < 0.8:
        return "😊", "is-calm", "#E8F1FE", "#C9D8F7"
    if ratio < 1.0:
        return "😅", "is-worried", "#FFF7D9", "#F1E3A8"
    return "😭", "is-over", "#FDE8E8", "#F5C2C2"


def render(ratio=0.85) -> None:
    """在页面右下角渲染情绪小球；ratio 为预算使用率（0~1+）。"""
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        ratio = 0.85
    ratio = max(0.0, min(ratio, 2.0))

    emoji, css_class, bg, border = _state_for(ratio)
    # 注意：HTML 不能有缩进，否则 Markdown 会把它当成代码块转义显示
    html = (
        '<div class="emotion-mascot-wrap">'
        f'<div class="emotion-mascot {css_class}" '
        f'style="background:{bg}; border-color:{border};" '
        f'role="img" aria-label="预算使用率 {ratio * 100:.0f}%">'
        f'<span class="emotion-emoji">{emoji}</span>'
        '<div class="emotion-tooltip">我是你的记账小助手，随时为你服务~</div>'
        '</div></div>'
    )
    st.markdown(_CSS + html, unsafe_allow_html=True)
