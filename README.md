# 记账 AI 助手（选题A）· Streamlit 前端

> 个人记账与消费分析 AI 助手的前端部分。后端为 **FastAPI（已开发完成，由其他组负责）**，本仓库只包含 Streamlit 前端：需求拆解 → UI 页面开发 → 接口对接与校验 → 本文档输出。
>
> 交付目录：`D:\agent\ledger-frontend\`

## 交付内容导读（按此顺序阅读）

| 顺序 | 内容 | 位置 |
| --- | --- | --- |
| ① 需求与接口梳理 | 功能点、全局契约、页面结构、接口清单（推导默认值） | [`docs\需求与接口梳理.md`](docs/需求与接口梳理.md)（本文档「二」为其摘要） |
| ② 完整前端代码位置与结构 | 目录结构树、模块职责、功能清单与验证方式 | 本文档「三、四」 |
| ③ 运行部署说明 | 虚拟环境 → 装依赖 → 启动 → 联调 → 常见问题排查 | [`docs\前端部署说明.md`](docs/前端部署说明.md)（本文档「六」为快速启动摘要） |
| 附：接口对接说明 | 15 个接口全表、错误映射、12 项核对清单、联调冒烟 | [`docs\接口对接说明.md`](docs/接口对接说明.md) |

---

## 一、项目简介

**记账 AI 助手**让用户用一句话、一张小票照片就能完成记账，并通过图表与预算预警掌握消费状况。前端为单页 Streamlit 应用：左侧固定侧边栏只放全局概览，主区域自上而下排列 6 个功能卡片（不用 tab 导航），覆盖：

1. **自然语言记账**：一句话 → AI 解析 → 可编辑确认卡片 → 入库；
2. **小票 OCR 上传**：上传小票图片 → AI 识别 → 校对保存；
3. **流水列表**：筛选 / 查看 / 编辑 / 删除（删除二次确认）；
4. **消费图表**：分类占比环形图 + 月度趋势柱状图；
5. **自然语言查账**：像聊天一样提问，AI 文字回答 + 统计表格；
6. **预算预警**：预算 banner（80% 黄色预警 / 100% 红色超支）+ 总预算与分类预算设置。

### 技术栈

| 项 | 内容 |
| --- | --- |
| 语言 / 运行环境 | Python 3.9+（推荐 3.10–3.12） |
| 前端框架 | **Streamlit**（锁定 `1.41.1`，详见 requirements.txt 注释） |
| HTTP 客户端 | **requests** `2.32.3`（前端与后端通信的唯一通道） |
| 图表 | **Plotly** `5.24.1`（环形图 + 柱状图，蓝灰配色） |
| 表格 | **pandas** `2.2.3`（流水列表 / 查账统计表 / 预算明细表） |
| 后端 | FastAPI（本仓库不含后端代码；默认地址 `http://127.0.0.1:8000`） |

依赖清单见 [`requirements.txt`](requirements.txt)（已锁定版本并附锁定原因注释）。

---

## 二、需求与接口梳理（摘要）

完整文档：[`docs\需求与接口梳理.md`](docs/需求与接口梳理.md)（344 行，含 7 大功能点交互流程、页面结构树、15 个接口入参/出参 JSON、与后端核对清单、边界降级策略）。

> ⚠️ **重要声明**：接口路径与字段名均为按需求推导的**默认值**，最终一律以**后端 FastAPI 的 `/docs`（Swagger UI）为准**。

### 2.1 全局契约（前后端必须一致遵守）

| 约定项 | 规则 |
| --- | --- |
| 金额 | 一律整数**分**（`amount_cents`），禁止浮点；展示 ÷100、提交 ×100（`utils.py`） |
| 日期 | ISO 格式 `YYYY-MM-DD` |
| 收支方向 | `direction` ∈ `expense` / `income` |
| 数据来源 | `source` ∈ `text`（自然语言）/ `receipt`（小票OCR）/ `manual`（手动） |
| 解析置信度 | `confidence` ∈ [0,1]，低于 0.7 时确认卡片黄色高亮提示复核 |
| 错误结构 | `{"detail": "..."}` 或 `{"code": "...", "message": "..."}`；422 为 FastAPI 默认结构 |
| 分页 | `limit` / `offset`（待与后端核对） |
| 后端地址 | 全局变量 `API_BASE_URL`，默认 `http://127.0.0.1:8000`（见 [`config.py`](config.py)） |

### 2.2 页面结构（固定顺序，不用 tab 导航）

```
├── 左侧固定侧边栏（仅概览，不放导航）
│   ├── 应用标题 + 当前后端地址
│   ├── 本月概览：收入 / 支出 / 结余 + 笔数        ← GET /api/stats/summary
│   ├── 预算执行进度条                            ← GET /api/budgets/status
│   └── 高级设置：后端地址覆盖 + 演示模式开关
└── 主区域：6 个 Section 卡片，固定顺序
    ① 自然语言记账 → ② 小票 OCR 上传 → ③ 流水列表
    → ④ 消费图表 → ⑤ 自然语言查账 → ⑥ 预算预警
```

### 2.3 接口清单（15 个，推导默认值）

| 类别 | 接口 | 前端函数（`services/api_client.py`） |
| --- | --- | --- |
| 健康检查 | `GET /health` | `check_health()` |
| 分类 | `GET /api/categories` | `fetch_categories()` |
| 自然语言解析 | `POST /api/transactions/parse` | `parse_transaction_text()` |
| 流水 | `POST /api/transactions` | `create_transaction()` |
| 流水 | `GET /api/transactions` | `fetch_transactions()` |
| 流水 | `PUT /api/transactions/{id}` | `update_transaction()` |
| 流水 | `DELETE /api/transactions/{id}` | `delete_transaction()` |
| OCR | `POST /api/receipts/ocr` | `ocr_receipt()` |
| 统计 | `GET /api/stats/summary` | `fetch_stats_summary()` |
| 统计 | `GET /api/stats/category` | `fetch_stats_category()` |
| 统计 | `GET /api/stats/monthly` | `fetch_stats_monthly()` |
| 查账 | `POST /api/query` | `query_accounts()` |
| 预算 | `GET /api/budgets` | `fetch_budgets()` |
| 预算 | `PUT /api/budgets` | `save_budgets()` |
| 预算 | `GET /api/budgets/status` | `fetch_budget_status()` |

每个接口的入参 JSON / 出参 JSON / 错误约定 / 需后端配合点，见 [`docs\接口对接说明.md`](docs/接口对接说明.md) 第 3 节。

---

## 三、完整前端代码位置与结构

```
D:\agent\ledger-frontend\
├── app.py                      # Streamlit 主入口：页面骨架、启动健康探测、6 个 Section 固定顺序
├── config.py                   # 全局配置：后端地址、三级超时(10/60/120s)、阈值、12 个接口路径常量、DEMO_MODE
├── utils.py                    # 纯工具函数：元↔分换算、日期工具、to_error_message 友好错误文案
├── requirements.txt            # 依赖清单（锁定版本，含锁定原因注释）
├── README.md                   # 本文件
├── components\                 # 复用 UI 组件
│   ├── style.py                #   全局 CSS：浅白底 + 柔和蓝 #4A7BE8，卡片 16px / 输入框 10px 圆角
│   ├── banners.py              #   预算 banner（<80% 蓝 / 80%起黄 / ≥100% 红）+ 彩色细进度条
│   ├── charts.py               #   Plotly 环形图 + 柱状图（蓝灰配色、隐藏工具栏、空数据占位）
│   ├── confirm_card.py         #   可编辑确认卡片（解析与 OCR 共用：方向/金额/日期/分类/商户/备注）
│   ├── manual_form.py          #   手动录入降级表单（解析/OCR 失败兜底，source=manual）
│   └── sidebar.py              #   左侧侧边栏：本月概览 + 预算进度 + 高级设置（后端地址/演示模式）
├── sections\                   # 6 个功能 Section 页面逻辑
│   ├── nl_bookkeeping.py       #   ① 自然语言记账
│   ├── receipt_ocr.py          #   ② 小票 OCR 上传
│   ├── transaction_list.py     #   ③ 流水列表
│   ├── charts_section.py       #   ④ 消费图表
│   ├── nl_query.py             #   ⑤ 自然语言查账
│   └── budget.py               #   ⑥ 预算预警
├── services\                   # 数据层
│   ├── api_client.py           #   与后端通信的唯一通道：统一请求封装 + 15 个接口函数
│   └── demo_data.py            #   演示模式内置示例数据（纯内存，无后端/LLM 逻辑）
└── docs\
    ├── 需求与接口梳理.md        #   ① 需求拆解与接口梳理（Agent1 产出）
    ├── 接口对接说明.md          #   接口对接与校验说明（Agent3 产出）
    └── 前端部署说明.md          #   ③ 运行部署说明（Agent4 产出）
```

### 分层约定（务必保持）

| 层 | 职责 | 约束 |
| --- | --- | --- |
| `sections/` + `components/` | 页面与组件 | 零 HTTP 逻辑，只调用 `api_client` 函数并捕获 `ApiError`；异常经 `utils.to_error_message()` 友好展示；提交动作必带 `st.spinner` |
| `services/api_client.py` | 与后端通信的**唯一通道** | 统一 `_request()` → `_check_response()` 封装；错误分类 network/timeout/http；兼容 `detail` / `code+message` / `error` / FastAPI 422 |
| `services/demo_data.py` | 演示兜底 | DEMO_MODE 开启时返回内置示例数据，不发真实请求 |
| `utils.py` / `config.py` | 工具与配置 | 纯函数 / 纯常量；页面禁止硬编码 URL，一律取 `config.PATH_*` |

---

## 四、功能清单与验证方式

| Section | 功能 | 验证方式（真实后端环境下） |
| --- | --- | --- |
| ① 自然语言记账 | 输入一句话 + 支出/收入切换 → `POST /api/transactions/parse` 解析 → 确认卡片（金额/日期/分类/商户/备注/方向全可编辑，低置信度黄色提示）→ 确认入库（`source="text"`）；解析失败自动降级手动录入（`source="manual"`） | 输入「昨天在星巴克喝咖啡花了 35」→ 检查解析字段正确、卡片可编辑、入库成功后侧边栏概览刷新；停掉后端再解析 → 出现手动录入表单 |
| ② 小票 OCR 上传 | 上传 jpg/png/webp（≤10MB，前端预校验）→ 上传即识别（长超时 120s）→ 校对卡片（含 OCR 原文折叠区、warnings、疑似重复勾选门禁）→ 保存（`source="receipt"`，带 `receipt_id`）；失败黄色提示 + 手动表单 | 上传一张小票图片 → 核对识别草稿 → 保存成功；传非图片/超 10MB 文件 → 被前端拒绝 |
| ③ 流水列表 | 6 档时间筛选（本月/上月/近3月/近6月/全部/自定义）+ 分类/方向筛选 → dataframe 展示 → 编辑表单（PUT）→ 删除二次确认（DELETE） | 记两笔流水后出现在列表；编辑一笔金额保存后列表刷新；点删除 → 出现二次确认，确认后该笔消失 |
| ④ 消费图表 | 统计范围筛选 + 分类占比环形图 + 月度趋势柱状图；数据全部来自统计接口，前端不做金额计算；空数据显示占位文案 | 有流水后两图正常渲染且配色为蓝灰系；切换「上月」范围图表随之变化；无数据范围显示「暂无数据」 |
| ⑤ 自然语言查账 | 示例问题按钮 + 对话式提问 → 文字回答 + 统计表格；数字全部来自后端，前端只展示；保留最近 6 轮问答历史 | 点示例问题「这个月吃饭花了多少」→ 得到文字回答与统计表格；连续提问出现对话气泡历史 |
| ⑥ 预算预警 | 顶部预算 banner（未设置中性灰 / <80% 蓝 / 80%~100% 黄预警 / ≥100% 红超支高亮 + 彩色进度条）+ 月份选择 + 月度总预算 + 分类预算表单 + 执行明细表 | 设置预算小于本月支出 → banner 变红并显示超支金额；设为支出的 1.5 倍 → banner 蓝色「预算执行良好」 |
| 全局兜底 | 启动健康探测失败显示「无法连接后端服务」引导页；演示模式蓝色提示条；侧边栏改地址/切演示自动重探测；所有异常友好分级文案 | 停后端刷新页面 → 引导页；恢复后端并勾选/取消演示模式 → 自动重探测恢复 |

---

## 五、UI 设计规范

> 规范出处：[`docs\需求与接口梳理.md`](docs/需求与接口梳理.md) 第 2 节；实现文件：`components/style.py`（CSS）、`components/banners.py`（预警）、`components/charts.py`（图表配色）、`app.py`（布局与顺序）。以下均与当前代码实现一致。

| 维度 | 规范与实现 |
| --- | --- |
| 整体风格 | Modern SaaS 极简风、开发者工作台感；无复杂动画与花哨特效 |
| 配色 | 整体 ≤3 色系：浅白底色 `#F5F7FB` + 柔和蓝主色 `#4A7BE8` + 中性灰阶；预警黄/红仅用于状态提示 |
| 布局 | 左侧固定侧边栏仅概览（收入/支出/结余 + 预算进度 + 高级设置）；主区域 6 个 Section 卡片自上而下**固定顺序**（①自然语言记账→②小票OCR→③流水列表→④消费图表→⑤自然语言查账→⑥预算预警），不用 tab 导航 |
| 卡片 / 控件 | 卡片白底 + 16px 圆角 + 细边框 + 轻阴影；输入框/按钮/下拉 10px 圆角；卡片间留白充足 |
| 预警色 | 预算使用率 <80% 蓝色「预算执行良好」；**80% 起黄色预警**「请注意控制」；**≥100% 红色超支高亮**（含超支金额）；未设置预算中性灰提示。阈值见 `config.py`（`BUDGET_WARN_RATIO=0.8` / `BUDGET_OVER_RATIO=1.0`） |
| 交互反馈 | 每个提交动作必带 loading（代码中 11 处 `st.spinner`，含启动探测 1 处、手动降级保存 2 处）；解析卡片（自然语言、OCR）**全部字段可编辑**后再确认；低置信度（<0.7）卡片黄色提示复核 |
| 图表 | 蓝灰渐变调色板（主色蓝 + 中性灰，不超 3 个色系）、隐藏工具栏、仅保留 hover 提示 |

---

## 六、运行部署说明（快速启动）

> 完整部署与联调步骤（含常见问题排查）见 [`docs\前端部署说明.md`](docs/前端部署说明.md)。

### 环境依赖

- Python 3.9+（推荐 3.10–3.12），`python` / `pip` 已加入 PATH；
- 可访问 PyPI（安装依赖）；
- 联调需后端 FastAPI 已启动（默认 `http://127.0.0.1:8000`）；仅演示可不开后端（演示模式）。

### 快速启动（5 步）

```bash
# ① 进入项目目录，创建并激活虚拟环境
cd D:\agent\ledger-frontend
python -m venv .venv
.venv\Scripts\activate            # Windows；macOS/Linux 用 source .venv/bin/activate

# ② 安装依赖（版本已锁定）
pip install -r requirements.txt

# ③ 启动后端 FastAPI（按后端项目实际启动方式，以下为示例）
uvicorn main:app --host 127.0.0.1 --port 8000
#    验证：浏览器打开 http://127.0.0.1:8000/docs 应能看到全部接口

# ④ 另开终端，启动前端
streamlit run app.py
#    浏览器打开 http://localhost:8501

# ⑤ 无后端答辩演示兜底（可选，二选一）
set LEDGER_DEMO_MODE=1 && streamlit run app.py        # Windows CMD
# $env:LEDGER_DEMO_MODE="1"; streamlit run app.py     # PowerShell
# 或在页面左侧「高级设置」勾选「演示模式」
```

### 后端地址配置（三种方式，优先级从高到低）

1. **运行时覆盖**：左侧「高级设置」→「后端地址」文本框（修改后自动重新探测连通性）；
2. **环境变量** `LEDGER_API_BASE_URL`（如 `set LEDGER_API_BASE_URL=http://192.168.1.10:8000`）；
3. **`config.py`** 常量 `API_BASE_URL`（默认 `http://127.0.0.1:8000`）。

---

## 七、接口对接说明

完整文档：[`docs\接口对接说明.md`](docs/接口对接说明.md)。要点：

- **架构**：页面层（零 HTTP）→ `services/api_client.py`（唯一通道）→ FastAPI 后端；
- **15 个接口全表**：方法 / 路径（`config.PATH_*`）/ 入参 / 出参 / 错误约定 / 需后端配合点；
- **统一错误处理**：network（连接失败）/ timeout（超时）/ http（业务 detail、404、422 定位字段、500、502/503 LLM 不可用）→ 友好中文文案；
- **超时分级**：普通 10s / LLM 60s / OCR 120s（`config.py`）；
- **12 项联调核对清单**：因后端 `/docs` 在本组环境不可达，全部标注「待后端确认」，并给出每项不一致时的修改位置（只需改 `config.py` 与 `services/api_client.py`，页面无需改动）；
- **联调冒烟步骤**：静态编译 → 6 个 Section 顺序冒烟 → 错误场景 → 演示兜底。

---

## 八、注意事项与已知问题

1. **接口为推导默认值**：15 个接口的路径与字段尚未与真实后端核对（后端 `/docs` 在本组开发环境不可达）。首次联调请先按 [`docs\接口对接说明.md`](docs/接口对接说明.md) 第 5 节 12 项清单对照 `/docs` 核对；不一致只需改 `config.py`（`PATH_*`）与 `services/api_client.py`（参数/字段），页面代码无需改动。
2. **运行冒烟未在本组环境执行**：开发环境的 pwsh 沙箱 ACL 限制导致 `py_compile` 与 `streamlit run` 冒烟无法运行（与 t1~t3 相同环境问题）。已做全文件回读 + 静态引用检查；**交付/答辩前请在真实终端执行** [`docs\前端部署说明.md`](docs/前端部署说明.md) 第 9 节校验步骤。
3. **Streamlit 锁定 1.41.1**：1.49+ 中 `use_container_width` 弃用会产生满屏警告；若升级需全局替换该参数（改用 `width="stretch"`）。
4. **演示模式（DEMO_MODE，默认关闭）**：仅作答辩演示兜底，数据为内置示例、存于内存，刷新页面即重置；开启优先级：侧边栏勾选 > 环境变量 `LEDGER_DEMO_MODE=1` > `config.DEMO_MODE`。真实数据永远走 HTTP。
5. **OCR 上传限制**：仅 jpg / png / webp，≤10MB（前端预校验，超限直接拒绝不上传）。
6. **金额与日期契约**：金额整数分（`amount_cents`）、日期 `YYYY-MM-DD`，前后端必须一致；前端展示层由 `utils.py` 统一换算。
7. **前端不做金额计算**：图表与查账的数字全部来自后端统计接口，前端只负责展示。
8. **无鉴权设计**：接口默认无鉴权（按 FastAPI 惯例推导），如后端加了鉴权需在 `api_client._request()` 统一补 header。

---

## 九、团队分工说明

| 角色 | 成员（Agent） | 职责与产出 |
| --- | --- | --- |
| 队长 | lead | 任务拆解、UI 设计规范追加（Modern SaaS 极简风 / ≤3 色 / 80%黄 / 100%红预警等）、质量把关与环境问题诊断 |
| ① 需求拆解与接口梳理 | Agent1（req-breakdown） | [`docs\需求与接口梳理.md`](docs/需求与接口梳理.md)：全局契约、7 大功能点、页面结构树、15 个接口清单、核对清单、降级策略；[`config.py`](config.py) 占位 |
| ② UI 页面开发 | Agent2（ui-pages） | [`app.py`](app.py)、[`components\`](components/)、[`sections\`](sections/)、[`utils.py`](utils.py)、requirements.txt 初版（MOCK 版页面，签名对齐接口文档） |
| ③ 接口对接与校验 | Agent3（api-integration） | [`services\api_client.py`](services/api_client.py)（真实 HTTP 统一封装）、[`services\demo_data.py`](services/demo_data.py)、DEMO_MODE、requirements.txt 锁版本、budget.py 表单回填修复、[`docs\接口对接说明.md`](docs/接口对接说明.md) |
| ④ 文档输出 | Agent4（doc-writer，本阶段） | 本 README 与 [`docs\前端部署说明.md`](docs/前端部署说明.md)：汇总交付、命令与路径逐一对照实际代码校验 |
