import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI 记账助手", page_icon="💰")

st.title("💰 AI 记账与消费分析助手")
st.caption("用一句话或一张小票完成记账，用一句话查账。")

with st.sidebar:
    st.subheader("服务状态")
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        data = resp.json()
        if data.get("db") == "ok":
            st.success("后端与数据库连接正常")
        else:
            st.warning("后端正常，但数据库连接失败")
    except requests.RequestException:
        st.error("无法连接后端服务")

st.info("功能页面开发中：自然语言记账、小票 OCR、消费统计、自然语言查账、预算提醒。")
