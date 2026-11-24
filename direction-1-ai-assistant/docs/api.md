# 接口契约 v1

> 状态：v1 已生效（2026-11-24）
> 最后更新：2026-11-24  
> 适用范围：前后端联调、Mock 替换、接口评审

本文档是前后端唯一的接口约定。代码与文档不一致时，以本文档为准，并同步修正代码。
已实现的接口以 `http://localhost:8000/openapi.json` 为自动化校验依据。

## 1. 通用约定

### 1.1 基础信息

| 项 | 约定 |
|---|---|
| 服务地址 | `http://localhost:8000` |
| 接口前缀 | `/api/v1`（健康检查 `/health` 除外） |
| 数据格式 | JSON，UTF-8 |
| 鉴权 | 无，单用户个人应用 |
| 字段命名 | 下划线小写，如 `spent_at` |

### 1.2 金额、时间与月份

| 项 | 约定 | 示例 |
|---|---|---|
| 金额 | 字符串，单位元，固定两位小数 | `"25.50"` |
| 时间 | ISO 8601，本地时间，不带时区 | `2026-11-24T12:30:00` |
| 月份 | `YYYY-MM` | `2026-11` |
| 日期查询参数 | `start`、`end` 可只传日期；`end` 传日期时包含当天 | `end=2026-11-30` |

时间字段**不能带时区**。传 `2026-11-24T12:30:00+08:00` 这类值会返回 `422`，接口不会自动换算时区。

日期参数必须补零为标准格式 `YYYY-MM-DD`；`2026-11-3` 这类写法返回 `422`，不会被当作 11 月 3 日处理。

**金额不使用浮点数**（如 `25.5`），也不使用整数分；前端展示时直接使用字符串，不要 `parseFloat` 后自行累加。

### 1.3 分页与排序

分页列表接口统一使用：

| 参数 | 说明 | 默认 |
|---|---|---|
| `limit` | 每页条数，1–500 | 100 |
| `offset` | 跳过条数，≥0 | 0 |
| `sort_by` | 排序字段，见具体接口 | 见具体接口 |
| `order` | `asc` / `desc` | 见具体接口 |

列表响应统一为：

```json
{
  "total": 12,
  "items": []
}
```

`total` 是过滤后的总条数，不受 `limit` / `offset` 影响。

### 1.4 错误结构

所有错误统一返回：

```json
{
  "code": "NOT_FOUND",
  "message": "账目不存在",
  "request_id": "8f3c2a..."
}
```

参数校验错误额外返回字段明细：

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

| HTTP 状态 | code | 含义 |
|---|---|---|
| 400 | `BAD_REQUEST` | 请求逻辑错误，如时间范围传反、空更新 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 422 | `VALIDATION_ERROR` | 参数校验失败 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误，堆栈只写日志 |

每个响应都带 `X-Request-ID` 头，值与响应体 `request_id` 一致。前端报错时请一并反馈。

### 1.5 请求字段校验

请求体使用严格模式：出现未定义字段会返回 `422 VALIDATION_ERROR`，不会被静默忽略。
前端按旧字段名传参（如 `amount_cents`、`direction`）时会立即报错，而不是返回一个字段缺失的成功结果。

## 2. 数据字典

### 2.1 账目 Expense

| 字段 | 类型 | 可写 | 说明 |
|---|---|---|---|
| `id` | int | 否 | 主键 |
| `amount` | string | 是 | 金额，元，两位小数，必须 > 0 |
| `category` | string | 是 | 消费类别，必须是固定类别之一 |
| `spent_at` | string | 是 | 消费时间，ISO 8601 |
| `note` | string \| null | 是 | 备注，最长 255 |
| `source` | string | 仅创建时 | 来源：`manual` / `nlp` / `ocr`，默认 `manual`；`ocr` 必须带 `image_path`，`nlp` 必须带 `raw_text`；创建后不可修改 |
| `raw_text` | string \| null | 是 | 自然语言原句或 OCR 识别文本 |
| `image_path` | string \| null | 是（仅 OCR 确认时） | 小票图片路径，仅 OCR 确认入库时传；必须是 `data/uploads/` 下的相对路径 |
| `created_time` | string | 否 | 创建时间 |
| `updated_time` | string | 否 | 更新时间 |

### 2.2 消费类别

固定 8 类，只接受以下值：

```
餐饮、交通、购物、娱乐、居住、医疗、教育、其他
```

不接受自由文本。新增类别需要同时修改后端常量与前端下拉框。

### 2.3 来源 source

| 值 | 含义 |
|---|---|
| `manual` | 用户手动录入 |
| `nlp` | 自然语言解析后确认入库 |
| `ocr` | 小票 / 截图识别后确认入库 |

## 3. 已实现接口

### 3.1 健康检查

```
GET /health
```

```json
{"status": "ok", "db": "ok"}
```

数据库不可用时 `db` 为 `"error"`。无论数据库是否正常，该接口的 HTTP 状态码都是 `200`，是否健康要看响应体。

### 3.2 类别列表

```
GET /api/v1/categories
```

```json
["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "教育", "其他"]
```

### 3.3 新增账目

```
POST /api/v1/expenses
```

请求：

```json
{
  "amount": "25.50",
  "category": "餐饮",
  "spent_at": "2026-11-24T12:30:00",
  "note": "午饭",
  "source": "manual",
  "raw_text": null,
  "image_path": null
}
```

`image_path` 可选，仅 OCR 确认入库时传；普通手动记账不传。

`source` 默认 `manual`；传 `ocr` 必须同时提供 `image_path`，传 `nlp` 必须同时提供 `raw_text`，否则返回 `422`。

成功：`201`

```json
{
  "id": 1,
  "amount": "25.50",
  "category": "餐饮",
  "spent_at": "2026-11-24T12:30:00",
  "note": "午饭",
  "source": "manual",
  "raw_text": null,
  "image_path": null,
  "created_time": "2026-11-24T12:31:00",
  "updated_time": "2026-11-24T12:31:00"
}
```

错误：`422 VALIDATION_ERROR`

### 3.4 查询账目列表

```
GET /api/v1/expenses
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `category` | 按类别过滤 | 不限 |
| `start` | 消费时间下限（含），不能带时区 | 不限 |
| `end` | 消费时间上限（含），传日期包含当天，不能带时区 | 不限 |
| `limit` | 每页条数，1–500 | 100 |
| `offset` | 跳过条数 | 0 |
| `sort_by` | `id` / `spent_at` / `amount` / `category` / `created_time` | `spent_at` |
| `order` | `asc` / `desc` | `desc` |

```json
{
  "total": 1,
  "items": [
    {
      "id": 2,
      "amount": "12.80",
      "category": "交通",
      "spent_at": "2026-11-21T08:15:00",
      "note": "地铁",
      "source": "manual",
      "raw_text": null,
      "image_path": null,
      "created_time": "2026-11-21T08:20:00",
      "updated_time": "2026-11-21T08:20:00"
    }
  ]
}
```

错误：`400 BAD_REQUEST`（`start` 晚于 `end`）

### 3.5 账目详情

```
GET /api/v1/expenses/{id}
```

成功：`200`，返回单个账目对象。  
错误：`404 NOT_FOUND`

### 3.6 修改账目（部分更新）

```
PUT /api/v1/expenses/{id}
```

只传需要修改的字段，未传字段保持原值。显式传 `null` 会清空 `note` / `raw_text`。

`amount`、`category`、`spent_at` 不能显式传 `null`，否则返回 `422`；省略这些字段表示不修改。
`source`、`image_path` 在创建时确定，修改接口不接受，传了会返回 `422`。

修改接口只接受以下字段：`amount`、`category`、`spent_at`、`note`、`raw_text`。
不要把详情接口返回的对象原样回传；`id`、`created_time`、`updated_time`、`source`、`image_path` 等只读字段会触发 `422`。

```json
{
  "amount": "30.00",
  "note": "改成了晚饭"
}
```

成功：`200`，返回更新后的完整账目。  
错误：`404`（id 不存在，优先于空请求体）、`400`（账目存在但请求体为空）、`422`

### 3.7 删除账目

```
DELETE /api/v1/expenses/{id}
```

成功：`204`，无响应体。  
错误：`404 NOT_FOUND`

硬删除：记录直接从数据库删除，没有回收站，删除后不可恢复。

### 3.8 调试接口

```
GET /api/v1/ping
```

```json
{"message": "pong"}
```

仅用于连通性检查，不属于业务接口。

## 4. 规划接口

以下接口尚未实现，先约定结构，前端按此开发，后端实现后以 `/openapi.json` 核对。

### 4.1 统计

状态：开发中，由统计模块负责人实现。

#### 总览

```
GET /api/v1/stats/summary?start=2026-11-01&end=2026-11-30
```

```json
{
  "start": "2026-11-01T00:00:00",
  "end": "2026-11-30T23:59:59",
  "total_amount": "128.50",
  "count": 12,
  "avg_amount": "10.71"
}
```

#### 分类统计

```
GET /api/v1/stats/categories?start=2026-11-01&end=2026-11-30
```

```json
{
  "start": "2026-11-01T00:00:00",
  "end": "2026-11-30T23:59:59",
  "total_amount": "128.50",
  "items": [
    {"category": "餐饮", "amount": "80.00", "count": 5, "ratio": 0.6226},
    {"category": "交通", "amount": "48.50", "count": 7, "ratio": 0.3774}
  ]
}
```

#### 趋势

```
GET /api/v1/stats/trend?start=2026-11-01&end=2026-11-30&granularity=day
```

`granularity`：`day` / `month`，默认 `day`。

```json
{
  "granularity": "day",
  "start": "2026-11-01T00:00:00",
  "end": "2026-11-30T23:59:59",
  "points": [
    {"period": "2026-11-01", "amount": "30.00", "count": 2},
    {"period": "2026-11-02", "amount": "0.00", "count": 0}
  ]
}
```

时间范围规则：

| 参数情况 | 处理 |
|---|---|
| 都不传 | 当前自然月 |
| 只传 `start` | `end` 取当前时间 |
| 只传 `end` | `start` 取 `end` 所在月 1 日 |
| `start > end` | 400 |

### 4.2 预算

状态：未实现，由预算模块负责人实现。

| 方法 | 路径 | 说明 |
|---|---|---|
| `PUT` | `/api/v1/budgets/{month}` | 设置或更新某月预算 |
| `GET` | `/api/v1/budgets/{month}` | 查询预算与执行情况 |

设置请求：

```json
{"amount": "1000.00"}
```

成功返回：

```json
{
  "month": "2026-11",
  "amount": "1000.00",
  "spent": "820.50",
  "remaining": "179.50",
  "usage_percent": 82.05,
  "status": "warning",
  "message": "本月预算已使用 82%，剩余 179.50 元"
}
```

规则：

- 仅月度总预算，不做分类预算
- `status`：`normal` / `warning`（≥80%）/ `exceeded`（超支）
- 超支时 `remaining` 为负数
- 未设置预算返回 `404 NOT_FOUND`
- 预算金额必须 > 0，两位小数

### 4.3 自然语言记账

状态：未实现。

```
POST /api/v1/expenses/parse
```

请求：

```json
{"text": "昨天午饭花了 25"}
```

成功：`200`，只解析不入库

```json
{
  "amount": "25.00",
  "category": "餐饮",
  "spent_at": "2026-11-23T12:00:00",
  "note": "午饭",
  "source": "nlp",
  "raw_text": "昨天午饭花了 25",
  "confidence": 0.92
}
```

- 无法识别的字段返回 `null` 并给出 `message` 提示，不猜测
- 前端展示确认卡片，用户确认后调用 `POST /api/v1/expenses` 入库
- 实现时该路由必须注册在 `/api/v1/expenses/{expense_id}` 之前，否则 `parse` 会被当成账目 id 解析

### 4.4 自然语言查账

状态：未实现。

```
POST /api/v1/query
```

请求：

```json
{"question": "这个月吃饭花了多少"}
```

成功：`200`

```json
{
  "answer": "2026-11 月餐饮共花费 80.00 元，共 5 笔。",
  "filters": {
    "start": "2026-11-01T00:00:00",
    "end": "2026-11-30T23:59:59",
    "category": "餐饮"
  },
  "result": {
    "total_amount": "80.00",
    "count": 5
  }
}
```

金额由后端计算，前端只展示，不自行累加。

### 4.5 小票 OCR

状态：未实现。

```
POST /api/v1/receipts/ocr
Content-Type: multipart/form-data
```

| 项 | 约定 |
|---|---|
| 表单字段 | `file` |
| 格式 | jpg / jpeg / png / webp |
| 大小 | ≤ 10MB |

成功：`200`

```json
{
  "image_path": "data/uploads/20261124/xxx.jpg",
  "raw_text": "星巴克 拿铁 35.00 ...",
  "items": [
    {
      "amount": "35.00",
      "category": "餐饮",
      "spent_at": "2026-11-24T09:30:00",
      "note": "拿铁",
      "source": "ocr",
      "confidence": 0.88
    }
  ],
  "warnings": []
}
```

- 一张小票可能识别出多笔，`items` 为数组
- 每笔都需要用户确认后再入库
- 确认入库时调用 `POST /api/v1/expenses`，可选携带 `image_path`（OCR 接口返回的路径）；后端校验路径必须位于 `data/uploads/` 下
- 识别失败返回 `400` 或 `503`，前端降级为手动录入

## 5. 前端现有调用与契约差异

前端待合入分支 `feat/frontend-ledger-ui`（尚未合入 `main`）当前使用 Mock 数据，调用路径与本文档不一致。接入后端时需要修改如下：

| 前端分支当前调用 | v1 契约 | 需要修改 |
|---|---|---|
| `GET /api/categories` | `GET /api/v1/categories` | 补 `/v1` |
| `POST /api/transactions` | `POST /api/v1/expenses` | 路径；`amount_cents` → `amount`（元字符串）；`occurred_at` → `spent_at`；`category_id` → `category`（中文名）；`source` 的 text/receipt/manual 改为 manual/nlp/ocr；去掉 `direction`、`merchant` |
| `GET /api/transactions` | `GET /api/v1/expenses` | 路径；`start_date/end_date` → `start/end`；`category_id` → `category`；响应 `{transactions,total}` → `{total,items}` |
| `PUT/DELETE /api/transactions/{id}` | `/api/v1/expenses/{id}` | 路径；删除成功为 `204` |
| `POST /api/transactions/parse` | `POST /api/v1/expenses/parse` | 路径；响应结构调整为扁平账目字段 |
| `POST /api/receipts/ocr` | `POST /api/v1/receipts/ocr` | 路径；上传字段仍为 `file` |
| `GET /api/stats/summary?month=` | `GET /api/v1/stats/summary?start&end` | 路径；月份参数改为时间范围；金额元字符串；不再返回 `income_cents`、`balance_cents` 等收入字段 |
| `GET /api/stats/category` | `GET /api/v1/stats/categories` | 路径；参数改为 `start/end`；字段 `category`、`amount`、`ratio` |
| `GET /api/stats/monthly?months=` | `GET /api/v1/stats/trend?granularity=month` | 路径；时间范围参数；`points` 结构 |
| `POST /api/query` | `POST /api/v1/query` | 补 `/v1`；响应结构按 4.4 |
| `GET /api/budgets?month=` | `GET /api/v1/budgets/{month}` | 路径参数；仅总预算，无分类预算 |
| `PUT /api/budgets` | `PUT /api/v1/budgets/{month}` | 路径参数；请求体 `{amount}` |
| `GET /api/budgets/status` | 合并到 `GET /api/v1/budgets/{month}` | 不再单独提供状态接口 |
| `POST /api/voice/transcribe` | 未规划 | 本期不实现 |

## 6. 待双方确认的分歧

| 分歧 | 当前契约 | 备选 | 建议 |
|---|---|---|---|
| 是否支持收入 | 只记支出 | 增加 `direction = expense/income` | 本期只做支出，收入以后扩展 |
| 金额单位 | 元字符串 | 整数分 `amount_cents` | 元字符串，避免前端重复换算 |
| 类别标识 | 中文名称 | 类别 ID + 名称 | 名称，类别固定且数量少 |
| 预算粒度 | 月度总额 | 总额 + 分类预算 | 先总额，分类预算以后扩展 |
| 商户字段 | 无 | 增加 `merchant` | 暂不增加，可写进备注 |

以上任一项确认变更后，需要同时修改本文档、后端模型与接口、前端调用，不能只改一侧。

## 7. 变更流程

1. 修改契约先提 PR，同一 PR 内更新本文档
2. 后端实现后，用 `/openapi.json` 核对字段与状态码
3. 前端 Mock 切换顺序：类别 → 账目 CRUD → 统计 → 预算 → NLP / OCR
4. 联调发现不一致时，以本文档为准，修正代码而不是口头约定
