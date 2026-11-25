# 当前 UI（对话 / 日历 / 情绪球）后端接口对齐清单

> 历史清单（2026-11-24）：接口已统一为 [`接口契约v1.md`](接口契约v1.md)，当前页面支持「演示模式 / 真实接口」双分支；本文旧路径仅作对照记录。

- 核对日期：2026-11-24
- 前端现状：`app.py`、`components/sidebar.py`、`components/calendar_view.py` 目前全部走本地 Mock，尚未真正调用后端。
- 后端现状：本机 `http://127.0.0.1:8000` 当前不可达，无法对照 `/openapi.json` 逐条核验；以下依据 `config.py`、`services/api_client.py`、`docs/接口对接说明.md` 与当前 UI 的实际需要整理。拿到后端 `/docs` 后仍需核对路径、参数名和字段名。

---

## 0. 一句话结论

**当前聊天版 UI 需要：7 个核心现有接口 + 1 个辅助现有接口（categories）+ 1 个新增接口（语音转写）。**

| 优先级 | 接口 | 用途 |
| --- | --- | --- |
| P0 现有 | `GET /health` | 启动探活 |
| P0 辅助 | `GET /api/categories` | 分类 id/name 映射（parse/OCR 已返回两者时可降为备用） |
| P0 现有 | `POST /api/transactions/parse` | 文字/AA 记账解析 |
| P0 现有 | `POST /api/transactions` | 确认入库 |
| P0 现有 | `POST /api/receipts/ocr` | 拍照上传识别 |
| P0 现有 | `GET /api/transactions` | 日历月视图 + 当日明细 |
| P0 现有 | `GET /api/budgets/status` | 侧边栏预算进度 + 情绪球比例 |
| P1 现有 | `GET /api/stats/category` | 「分析消费结构」 |
| P1 新增 | `POST /api/voice/transcribe` | 语音转文字（后端需新增） |

**可选/可暂缓：**

- 可选：`POST /chat`（旧聊天原型用过，当前 `config.py` / 文档未收录）。
- 可选：`POST /api/query`（更自由的自然语言查账；当前 UI 的分析用 stats/category 就够）。
- 当前 UI **不需要**（旧六段式遗留，后端可暂缓）：`GET /api/stats/summary`、`GET /api/stats/monthly`、`GET /api/budgets`、`PUT /api/budgets`、`PUT/DELETE /api/transactions/{id}`。

---

## 1. 接口明细（P0 核心 / P1 增强）

### 1.1 启动探活

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `GET /health` |
| 前端调用点 | 应用启动 / 切换真实模式时 |
| 入参 | 无 |
| 必须返回 | `200 {"status":"ok","version":"0.1.0"}`（version 可选） |
| 备注 | 无需鉴权、响应 <1s；失败时前端回退演示模式 |

### 1.2 分类列表

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `GET /api/categories` |
| 前端调用点 | 解析/OCR 返回分类后做 id/name 映射；创建流水前确认 `category_id` |
| 入参 | 无 |
| 必须返回 | `{"categories":[{"id","name","parent_id","sort_order"},...]}` |
| 备注 | `parent_id=null` 表示一级类目；至少返回「餐饮/交通/购物/娱乐/居住/医疗/其他」。**当前 UI 没有分类下拉**，如果 parse / OCR 已同时返回 `category_id` 与 `category_name`，此接口可只作为兜底，不必阻塞联调 |

### 1.3 自然语言解析

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `POST /api/transactions/parse` |
| 前端调用点 | 文字记账、AA 平摊（前端拿总额/分类后自己除人数） |
| 入参 | `{"text":"今天吃饭花了35块","direction":"expense"}` |
| 必须返回 | `{"draft":{"amount_cents","occurred_at","direction","category_id","category_name","merchant","note","confidence"},"raw_input":"..."}` |
| 备注 | **只解析、不入库**；`amount_cents` 整数分；`occurred_at=YYYY-MM-DD`；`category_id` 必须能在 categories 里找到；不确定字段返回 null |

### 1.4 创建流水

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `POST /api/transactions` |
| 前端调用点 | 解析确认后 / OCR 确认后 / 语音转写解析后 |
| 入参 | `{"amount_cents","occurred_at","direction","category_id","merchant","note","source","raw_input","confidence","receipt_id"}` |
| 必须返回 | `201 {"transaction":{"id","amount_cents","occurred_at","direction","category_id","category_name","merchant","note","source","created_at"}}` |
| 备注 | `source`：文字=`text`、OCR=`receipt`；语音走哪个 source 见待确认问题；重复记录建议 400 + `detail` |

### 1.5 小票 OCR

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `POST /api/receipts/ocr` |
| 前端调用点 | 聊天输入框上方「📷 拍照上传」 |
| 入参 | `multipart/form-data`，字段名 **`file`**；jpg/png/webp，≤10MB |
| 必须返回 | `{"receipt_id","draft":{"amount_cents","occurred_at","direction","category_id","category_name","merchant","note","confidence"},"ocr_raw":"...","warnings":[],"duplicate_hint":false}` |
| 备注 | 建议两步：OCR 出草稿 → 用户确认 → `POST /api/transactions`；`receipt_id` 随创建请求带上 |

### 1.6 流水列表（日历数据源）

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `GET /api/transactions` |
| 前端调用点 | 日历模式：按月拉取，按 `occurred_at` 分组；点击日期展示明细 |
| 入参 Query | `start_date=2026-11-01`、`end_date=2026-11-30`、`direction=expense`、`limit`、`offset` |
| 必须返回 | `{"transactions":[{"id","amount_cents","occurred_at","direction","category_id","category_name","merchant","note","source"}],"total","limit","offset"}` |
| 备注 | 日历需要当月全部支出；每笔必须有 `occurred_at`、`category_name`、`amount_cents`；按日期倒序；分页上限请确认 |

### 1.7 预算状态（侧边栏 + 情绪球）

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `GET /api/budgets/status?month=2026-11` |
| 前端调用点 | 侧边栏预算进度条；右下角情绪球的 `budget_ratio` |
| 入参 | `month=YYYY-MM` |
| 必须返回 | `{"month","total":{"budget_cents","spent_cents","ratio","level"}}` |
| 备注 | `ratio=spent/budget`（0~1+）；`level` ∈ normal/warn/over；未设预算时 `budget_cents=0`；`ratio=null` 时前端按 0 处理（显示 🥳） |

### 1.8 分类占比统计（分析消费结构）

| 项 | 内容 |
| --- | --- |
| 方法/路径 | `GET /api/stats/category?start_date=2026-11-01&end_date=2026-11-30&direction=expense` |
| 前端调用点 | 用户说「分析一下我的消费结构」时 |
| 必须返回 | `{"total_cents","items":[{"category_id","category_name","amount_cents","ratio"}]}` |
| 备注 | `ratio` 由后端算；无数据 `items=[]`；前端只展示，不自己算金额 |

### 1.9 语音转写（新增）

| 项 | 内容 |
| --- | --- |
| 建议方法/路径 | `POST /api/voice/transcribe`（路径可改，改 `config.py` 即可） |
| 前端调用点 | 聊天输入框上方「🎤 语音上传」（`st.audio_input` 录 WAV 后上传） |
| 入参 | `multipart/form-data`，字段名 **`file`**；建议支持 `audio/wav`（浏览器录音默认 WAV），时长 ≤60s、大小 ≤10MB |
| 建议返回 | `{"text":"今天吃饭花了35块","confidence":0.92,"duration_ms":2300}` |
| 备注 | 前端拿到 `text` 后走与文字相同的 parse → create 流程；也可以合并成 `/api/chat/audio`，但建议先分开，复用现有解析链路 |

---

## 2. 当前 UI 的真实调用流（供后端理解字段用途）

```
文字「今天吃饭35块」
  → POST /api/transactions/parse（text, expense）
  → 展示结构化卡片
  → POST /api/transactions（source=text, amount=3500, ...）

文字「3个人吃火锅300 AA」
  → 前端正则识别 3 人 / 300 元
  → POST /api/transactions/parse（text, expense）拿分类
  → 前端计算人均 100 元
  → POST /api/transactions（amount_cents=10000，note 标明 AA）

「查一下本月预算」
  → GET /api/budgets/status?month=YYYY-MM（不调 LLM）

「分析一下我的消费结构」
  → GET /api/stats/category?start_date&end_date&direction=expense

「拍小票」
  → POST /api/receipts/ocr（file）
  → 展示 draft（金额/分类/商户/置信度）
  → 用户确认 → POST /api/transactions（source=receipt, receipt_id=...）

「语音记账」
  → POST /api/voice/transcribe（file=wav）
  → 用返回 text 走上面的文字链路

日历模式
  → GET /api/transactions?start_date=月初&end_date=月末&direction=expense&limit=...
  → 按 occurred_at 分组，渲染每日金额/当日明细

侧边栏进度 + 情绪球
  → GET /api/budgets/status → total.ratio
```

---

## 3. 字段与通用约定（需要一次说清）

| 约定 | 建议 |
| --- | --- |
| 金额 | 全部 `amount_cents` 整数分；前端负责 ÷100 展示 |
| 日期 | `occurred_at` 用 `YYYY-MM-DD`；`created_at` ISO 8601 带时区（+08:00） |
| 方向 | `direction` ∈ `expense` / `income` |
| 分类 | `category_id` + `category_name` 最好同时返回；分类以 `/api/categories` 为准 |
| 分页 | 列表统一 `limit` / `offset`，返回 `total`；日历月数据建议允许 `limit=500` 或支持循环分页 |
| 错误 | 优先 `{"detail":"友好文案"}`；422 用 FastAPI 默认结构；502/503 表示 LLM/VLM/ASR 不可用 |
| 跨域 | 前端 8501 → 后端 8000，需要允许 `http://localhost:8501` / `http://127.0.0.1:8501` |
| 鉴权 | 当前无用户体系；如果要多用户/登录，请提前说 |
| 时区 | 以 `Asia/Shanghai` 为准，「今天/本月」按后端本地日期 |

---

## 4. 需要和后端组员确认的问题（按优先级）

1. **对话形态**：文字聊天用「parse + create + budgets/status + stats/category」这套现有接口拼，还是额外提供一个 `POST /chat`？如果已有 `/chat`，请给出入参/出参、是否自动入库、是否返回结构化 `intent/draft`、是否支持流式。
2. **AA 平摊**：是否由前端做除法？约定 `/api/transactions/parse` 对「3个人吃火锅300 AA」返回 **总额 300 元**、分类餐饮、**不自动入库**，前端再创建人均 100 元——是否可行？
3. **OCR 入库策略**：走「OCR 出 draft → 用户确认 → POST /api/transactions（带 receipt_id）」两步，还是后端提供 `confirm` 接口直接入库？`duplicate_hint=true` 时前端如何提示？
4. **语音转写**：新接口路径、表单字段名、支持的音频格式/时长上限、返回字段；语音创建的流水 `source` 用 `text` 还是新增 `voice`（当前枚举只有 text/receipt/manual）？
5. **日历数据**：按月拉 `GET /api/transactions` 是否支持足够大的 limit / 稳定分页？`start_date/end_date` 是否包含边界？如果没有 `category_name`，是否可以用 categories 映射？是否有必要加 `GET /api/stats/daily`？
6. **预算状态**：`GET /api/budgets/status` 是否已实现？未设预算时 `ratio` 返回 `null` 还是 `0`？`level` 的取值集合是什么？真实模式下前端会隐藏「模拟预算使用率」滑杆，情绪球改读接口 ratio——是否确认？
7. **分析意图**：用 `GET /api/stats/category` 还是 `POST /api/query`？`query` 的 `table.columns/rows` 结构是否稳定？
8. **分类**：parse / OCR 返回值里 `category_id` 和 `category_name` 是否都提供？`category_id` 是否与 `/api/categories` 一致？
9. **金额/日期/时区**：是否确认为 `amount_cents` 整数分、`occurred_at=YYYY-MM-DD`、`Asia/Shanghai`？
10. **错误与跨域**：错误体统一 `detail`？CORS 是否允许 8501？是否需要鉴权？
11. **健康检查与演示模式**：`/health` 是否无需鉴权且 <1s？后端不可达时前端走演示模式是否可接受？
12. **聊天历史**：当前只存在 Streamlit session_state；如果要做多端历史/会话列表，是否需要新增 `/api/chat/sessions` 等接口？（当前不阻塞）

---

## 5. 建议联调顺序

1. `GET /health` + `GET /api/categories`
2. `POST /api/transactions/parse` + `POST /api/transactions`
3. `GET /api/budgets/status`（侧边栏 + 情绪球）
4. `GET /api/transactions`（日历月视图/明细）
5. `POST /api/receipts/ocr`（图片链路）
6. `GET /api/stats/category`（分析）
7. `POST /api/voice/transcribe`（语音链路，新增）
8. 可选：`POST /chat` / `POST /api/query`

---

## 6. 可直接发给组员的短消息

> 我们对一下当前聊天版前端需要的接口。
>
> **P0 已有**：`GET /health`、`GET /api/categories`、`POST /api/transactions/parse`、`POST /api/transactions`、`POST /api/receipts/ocr`、`GET /api/transactions?start_date&end_date&direction=expense&limit&offset`、`GET /api/budgets/status`、`GET /api/stats/category`。
>
> **P1 新增**：`POST /api/voice/transcribe`（multipart `file`，WAV，返回 `text`）。
>
> **当前 UI 不需要、可暂缓**：`stats/summary`、`stats/monthly`、`budgets` GET/PUT、`transactions` PUT/DELETE。
>
> 想确认：① 用现有 parse/统计拼对话，还是额外做 `/chat`？② AA 人均是否前端算？③ OCR 是草稿确认还是直接入库？④ 语音接口字段/格式，流水 `source` 用 text 还是新增 voice？⑤ 日历按月拉 transactions 的分页/日期边界？⑥ 未设预算时 `budgets/status.ratio` 返回 null 还是 0？⑦ 金额分、日期、时区、错误体、CORS 是否都按文档来？
