# -*- coding: utf-8 -*-
"""
ledger-frontend 全局配置（接口契约 v1）

项目：记账 AI 助手（选题A）Streamlit 前端
约定：
  1. 金额使用「元字符串」（如 "25.50"），不使用整数分、不使用浮点数；
  2. 时间使用 ISO 8601 本地时间（如 "2026-11-24T12:30:00"）；
  3. 普通接口统一前缀 /api/v1，健康检查 /health 不带前缀；
  4. 页面代码禁止硬编码 URL，一律从本文件取值；
  5. 演示模式 DEMO_MODE：后端未启动时由 services/demo_data.py 提供
     内置示例数据，不发真实请求。
"""

import os

# ─────────────────────────────────────────────────────────────
# 一、后端服务地址（全局变量）
# ─────────────────────────────────────────────────────────────
# 接口契约 v1 固定服务地址（不再允许页面运行时覆盖）
API_BASE_URL = "http://localhost:8000"

# 普通接口统一前缀；/health 例外，单独定义。
API_PREFIX = "/api/v1"

# ─────────────────────────────────────────────────────────────
# 二、演示模式（DEMO_MODE）
# ─────────────────────────────────────────────────────────────
# 后端未启动时的答辩/演示兜底：开启后全部接口返回内置示例数据，
# 不发任何真实 HTTP 请求。
# 开启方式（优先级从高到低）：
#   1) 运行时勾选：侧边栏「高级设置」→「演示模式」复选框；
#   2) 环境变量：LEDGER_DEMO_MODE=1；
#   3) 修改下面常量 DEMO_MODE = True。
DEMO_MODE = os.environ.get("LEDGER_DEMO_MODE", "0") in ("1", "true", "True", "yes", "on")

# ─────────────────────────────────────────────────────────────
# 三、请求超时（单位：秒）
# ─────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 10        # 普通接口：列表 / 统计 / 预算 / 健康检查
LLM_REQUEST_TIMEOUT = 60    # LLM 接口：自然语言解析 / 查账
OCR_REQUEST_TIMEOUT = 120   # OCR 接口：小票图片识别

# ─────────────────────────────────────────────────────────────
# 四、预算与解析阈值
# ─────────────────────────────────────────────────────────────
BUDGET_WARN_RATIO = 0.8     # 使用率达到 80% 为 warning
BUDGET_OVER_RATIO = 1.0     # 使用率达到/超过 100% 为 exceeded

CONFIDENCE_WARN_THRESHOLD = 0.7  # 低于该值提示用户复核

# 接口契约 v1 固定类别（后端不再接受自由文本）
CATEGORY_NAMES = ("餐饮", "交通", "购物", "娱乐", "居住", "医疗", "教育", "其他")

# ─────────────────────────────────────────────────────────────
# 五、接口路径常量（接口契约 v1）
# ─────────────────────────────────────────────────────────────
# 健康检查：不带 /api/v1 前缀
PATH_HEALTH = "/health"

# 类别列表
PATH_CATEGORIES = f"{API_PREFIX}/categories"

# 自然语言记账解析（只解析不入库）
PATH_EXPENSE_PARSE = f"{API_PREFIX}/expenses/parse"

# 账目增删改查
PATH_EXPENSES = f"{API_PREFIX}/expenses"
PATH_EXPENSE_ITEM = f"{API_PREFIX}/expenses/{{id}}"

# 小票 OCR（multipart/form-data，字段名 file）
PATH_RECEIPT_OCR = f"{API_PREFIX}/receipts/ocr"

# 统计：总览 / 分类 / 趋势
PATH_STATS_SUMMARY = f"{API_PREFIX}/stats/summary"
PATH_STATS_CATEGORIES = f"{API_PREFIX}/stats/categories"
PATH_STATS_TREND = f"{API_PREFIX}/stats/trend"

# 自然语言查账
PATH_QUERY = f"{API_PREFIX}/query"

# 预算：GET/PUT /api/v1/budgets/{month}
PATH_BUDGET_ITEM = f"{API_PREFIX}/budgets/{{month}}"
