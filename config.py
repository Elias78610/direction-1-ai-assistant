# -*- coding: utf-8 -*-
"""
ledger-frontend 全局配置（占位版 · Agent1 需求拆解阶段创建）

项目：记账 AI 助手（选题A）Streamlit 前端
约定：
  1. 金额一律使用整数「分」（amount_cents），展示时由前端 ÷100 格式化为元；
  2. 日期一律使用 ISO 格式（YYYY-MM-DD）；
  3. 后端为 FastAPI，本文件中的接口路径常量是按需求推导的「默认值」，
     接口对接阶段（Agent3）必须对照后端 /docs 逐条核对并修正；
  4. 任何页面代码禁止硬编码 URL，一律从本文件取值；
  5. 演示模式 DEMO_MODE（Agent3 新增）：后端未启动时的答辩演示兜底，
     开启后全部接口走内置示例数据（services/demo_data.py），不发真实请求。
"""

import os

# ─────────────────────────────────────────────────────────────
# 一、后端服务地址（全局变量）
# ─────────────────────────────────────────────────────────────
# 默认指向本机 FastAPI 服务。支持两处覆盖，优先级从高到低：
#   1) 运行时覆盖：Streamlit 会话 st.session_state["api_base_url"]
#      （侧边栏「高级设置」中可修改，便于演示时切换后端）
#   2) 环境变量：LEDGER_API_BASE_URL（如 docker-compose 部署时注入）
API_BASE_URL = os.environ.get("LEDGER_API_BASE_URL", "http://127.0.0.1:8000")

# ─────────────────────────────────────────────────────────────
# 二、演示模式（DEMO_MODE · Agent3 接口对接阶段新增）
# ─────────────────────────────────────────────────────────────
# 后端未启动时的答辩/演示兜底：开启后全部接口返回内置示例数据，
# 不发任何真实 HTTP 请求；关闭（默认）则全部走真实后端接口。
# 开启方式（优先级从高到低）：
#   1) 运行时勾选：侧边栏「高级设置」→「演示模式」复选框；
#   2) 环境变量：LEDGER_DEMO_MODE=1（如答辩演示机提前注入）；
#   3) 修改下面常量 DEMO_MODE = True。
DEMO_MODE = os.environ.get("LEDGER_DEMO_MODE", "0") in ("1", "true", "True", "yes", "on")

# ─────────────────────────────────────────────────────────────
# 三、请求超时（单位：秒）
# ─────────────────────────────────────────────────────────────
# 普通接口超时：列表 / 统计 / 预算 / 健康检查等常规查询
REQUEST_TIMEOUT = 10
# LLM 接口超时：自然语言记账解析、自然语言查账（模型调用较慢）
LLM_REQUEST_TIMEOUT = 60
# OCR 接口超时：小票图片识别（VLM 视觉模型调用最慢）
OCR_REQUEST_TIMEOUT = 120

# ─────────────────────────────────────────────────────────────
# 四、预算预警阈值（首页 banner 展示用，前端只做判断不做金额计算）
# ─────────────────────────────────────────────────────────────
BUDGET_WARN_RATIO = 0.8   # 支出达到预算 80% 时，banner 黄色预警
BUDGET_OVER_RATIO = 1.0   # 支出达到/超过预算 100% 时，banner 红色超支高亮

# 解析置信度阈值：低于该值的确认卡片标黄提示用户复核（0~1）
CONFIDENCE_WARN_THRESHOLD = 0.7

# ─────────────────────────────────────────────────────────────
# 五、接口路径常量（推导默认值，最终以后端 /docs 为准）
# ─────────────────────────────────────────────────────────────
# 健康检查（应用启动时探测后端连通性）
PATH_HEALTH = "/health"

# 分类列表（下拉框 / 筛选器 / 预算分类表格共用）
PATH_CATEGORIES = "/api/categories"

# 自然语言记账解析：一句话 → 结构化草稿（确认卡片展示）
PATH_TRANSACTION_PARSE = "/api/transactions/parse"

# 流水增删改查
PATH_TRANSACTIONS = "/api/transactions"            # GET 列表 / POST 创建
PATH_TRANSACTION_ITEM = "/api/transactions/{id}"   # PUT 编辑 / DELETE 删除

# 小票 OCR 识别（multipart/form-data 上传图片，字段名 file）
PATH_RECEIPT_OCR = "/api/receipts/ocr"

# 统计接口
PATH_STATS_SUMMARY = "/api/stats/summary"          # 侧边栏概览：本月收入/支出/结余
PATH_STATS_CATEGORY = "/api/stats/category"        # 消费分类占比（饼图）
PATH_STATS_MONTHLY = "/api/stats/monthly"          # 月度趋势（柱状图）

# 自然语言查账：问题 → 文字回答 + 统计表格
PATH_QUERY = "/api/query"

# 预算
PATH_BUDGETS = "/api/budgets"                      # GET 查询 / PUT 设置
PATH_BUDGET_STATUS = "/api/budgets/status"         # 预算执行状态（首页 banner 用）
