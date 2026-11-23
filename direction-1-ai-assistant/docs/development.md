# 开发环境说明

## 前置要求

- Docker + Docker Compose
- uv（本地非 Docker 开发时需要）
- Python 3.12（由 uv 管理，无需手动安装）

## 首次启动

```bash
cd direction-1-ai-assistant
cp .env.example .env        # Windows: copy .env.example .env
# 编辑 .env，填写数据库密码与 LLM Key
docker compose up -d --build
```

## 常用命令

| 操作 | 命令 |
|---|---|
| 查看日志 | `docker compose logs -f backend` |
| 重启单个服务 | `docker compose restart backend` |
| 停止并删除容器 | `docker compose down` |
| 重建并启动 | `docker compose up -d --build` |
| 安装/更新后端依赖 | 改 `backend/pyproject.toml` 后 `docker compose up -d --build backend` |

## 本地非 Docker 开发（可选）

前提：本地已有 MySQL 且在 `.env` 的 `DATABASE_URL` 中配置正确。

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

cd frontend
uv sync
uv run streamlit run app.py
```

## 新增后端依赖

```bash
cd backend
uv add 包名            # 自动更新 pyproject.toml 与 uv.lock
```

改完依赖后需重新构建镜像：`docker compose up -d --build backend`。

## 健康检查

```bash
curl http://localhost:8000/health
# 期望：{"status":"ok","db":"ok"}
```

## 端口

| 服务 | 端口 |
|---|---|
| Streamlit 前端 | 8501 |
| FastAPI 后端 | 8000 |
| MySQL（主机映射） | 13306 |

## 错误响应格式

所有接口错误统一返回 JSON，并附带 `request_id`：

```json
{
  "code": "EXPENSE_NOT_FOUND",
  "message": "账目不存在",
  "request_id": "8f3c2a..."
}
```

参数校验失败（422）额外带字段明细：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数校验失败",
  "errors": [
    {"field": "body.amount", "message": "Input should be greater than 0"}
  ],
  "request_id": "8f3c2a..."
}
```

常见错误码：

| code | 含义 |
|---|---|
| `VALIDATION_ERROR` | 请求参数不合法（422） |
| `BAD_REQUEST` | 请求逻辑错误，如时间范围传反（400） |
| `NOT_FOUND` | 资源不存在（404） |
| `INTERNAL_ERROR` | 服务器内部错误（500），详细堆栈只在日志中 |

## 日志

日志输出到控制台，容器内用 `docker compose logs -f backend` 查看。

- 每个请求生成 `X-Request-ID` 响应头，日志里带同一个 ID
- 前端报错时把 `request_id` 一并反馈，后端可直接搜日志
- 日志级别通过环境变量 `LOG_LEVEL` 控制，默认 `INFO`

```
2026-11-23 16:00:00 | INFO | app.core.middleware | 8f3c2a... | GET /api/v1/expenses -> 200 12.3ms
```
