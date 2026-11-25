# AI 记账与消费分析助手

面向个人用户的智能记账应用：用一句话或一张小票完成记账，用一句话查账，系统自动完成分类、统计与预算提醒。

> 2026 GDUF AI Studio 考核 · 方向一（个人记账与消费分析 AI 助手）

## 功能规划

| 功能 | 状态 |
|---|---|
| 自然语言记账 + 小票 / 截图 OCR 录入 | 待开发 |
| 消费自动分类与统计 | 待开发 |
| 自然语言查账（时间范围 + 类别解析） | 待开发 |
| 月度预算设定与超支提醒 | 已完成（后端 + 前端页面） |
| 环境搭建（前后端 + MySQL + Docker） | 已完成 |

考核要求与交付清单见 [docs/assessment-direction-1.md](direction-1-ai-assistant/docs/assessment-direction-1.md)。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Streamlit |
| 后端 | FastAPI + Uvicorn，SQLAlchemy 2.x |
| 数据库 | MySQL 8.0（utf8mb4） |
| AI 能力 | LangChain，OpenAI 兼容接口（DeepSeek / 通义 / 智谱等），支持小票 OCR 识别 |
| 依赖管理 | uv（Python 3.12，锁文件锁定版本） |
| 部署 | Docker Compose |

## 架构

```
浏览器
  │ HTTP
  ▼
Streamlit 前端 (:8501)
  │ HTTP（容器内网 backend:8000）
  ▼
FastAPI 后端 (:8000) ── LangChain ──► LLM / OCR 服务（OpenAI 兼容接口）
  │
  ▼
MySQL 8.0 (:3306，主机映射 13306)
```

## 目录结构

```
.
├── README.md                     # 本文件
└── direction-1-ai-assistant/
    ├── docker-compose.yml        # mysql + backend + frontend 编排
    ├── .env.example              # 环境变量模板（复制为 .env 后填写）
    ├── docs/
    │   ├── api.md                # 前后端接口契约（唯一约定）
    │   ├── development.md        # 开发环境与常用命令
    │   └── assessment-direction-1.md  # 考核说明（归档）
    ├── backend/                  # FastAPI 服务，uv 管理依赖
    │   ├── Dockerfile
    │   └── app/
    │       ├── main.py           # 应用入口与健康检查
    │       ├── core/config.py    # 环境变量配置
    │       ├── db/session.py     # 数据库连接
    │       └── api/              # 接口路由
    ├── frontend/                 # Streamlit 前端，uv 管理依赖
    │   ├── Dockerfile
    │   └── app.py
    └── data/uploads/             # 小票 / 截图上传目录
```

## 快速开始

```bash
cd direction-1-ai-assistant
cp .env.example .env        # 填写数据库密码与 LLM Key
docker compose up -d --build
```

启动后：

- 前端：http://localhost:8501
- 后端接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health（期望 `{"status":"ok","db":"ok"}`）

> 主机 3306 端口可能已被占用，MySQL 容器默认映射到 **13306**，可在 `.env` 中通过 `MYSQL_HOST_PORT` 调整。

更多命令（日志、重启、新增依赖等）见 [docs/development.md](direction-1-ai-assistant/docs/development.md)。

## 环境变量

| 变量 | 说明 |
|---|---|
| `MYSQL_*` | 数据库账号、密码、库名、主机映射端口 |
| `DATABASE_URL` | 后端连接串（容器内由 compose 自动覆盖为 mysql 服务地址） |
| `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` | OpenAI 兼容接口的密钥、地址与模型名 |
| `VISION_API_KEY` 等 | 小票 OCR 识别服务配置 |
| `CORS_ORIGINS` | 允许跨域的前端地址，多个用逗号分隔 |

**不要提交 `.env` 或任何真实 API Key。** 仓库只包含 `.env.example` 模板。

## 团队分工

共 5 人，分工待补充：

| 成员 | 负责模块 |
|---|---|
| 待填写 | 待填写 |
| 待填写 | 待填写 |
| 待填写 | 待填写 |
| 待填写 | 待填写 |
| 待填写 | 待填写 |

## 提交方式

- 公开仓库地址：待填写
- 提交方式与截止时间：以官方考核通知为准

## 项目文档

- 接口契约：[docs/api.md](direction-1-ai-assistant/docs/api.md)
- 开发环境说明：[docs/development.md](direction-1-ai-assistant/docs/development.md)
- 考核说明：[docs/assessment-direction-1.md](direction-1-ai-assistant/docs/assessment-direction-1.md)
