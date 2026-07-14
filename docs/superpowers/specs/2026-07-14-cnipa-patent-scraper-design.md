# CNIPA 外观设计专利爬虫 — 设计文档

> 日期：2026-07-14
> 状态：草案，待用户审阅

## 1. 目标

编写一个独立 Python 工具，从中国国家知识产权局（CNIPA）官网拉取**当天公布的外观设计专利**完整数据，原始资料（图片）存入对象存储，元数据索引到 Elasticsearch，供下游 RAG 系统使用。

## 2. 范围

### 包含

- 抓取 CNIPA「专利公布公告」系统中当天公布的外观设计专利（公告日 = 当天）
- 解析详情页所有可获取字段（申请号、名称、申请人、分类号、摘要、权利要求、说明书、图片 URL）
- 下载外观设计专利的代表图与所有视图
- 上传原始图片到 MinIO（后期可切换阿里云 OSS）
- 索引元数据到 Elasticsearch，含 OSS 路径引用
- 处理 CNIPA 滑块验证码（Playwright + GPT-4o 视觉识别）
- 一次性 CLI 入口，可指定日期

### 不包含

- 发明专利、实用新型专利
- 历史数据的批量回溯（仅当天）
- 定时调度（一次性脚本）
- Web UI / 服务化 API
- 增量去重（用 ES 文档 `_id` = 申请号天然幂等）

## 3. 架构

### 3.1 总览

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (Typer)                          │
│              python -m cnipa_scraper run                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       Pipeline.run()                        │
│   1. 搜索当天外观设计专利   2. 逐条抓详情                    │
│   3. 下载图片              4. 上传 MinIO                    │
│   5. 索引到 ES                                              │
└──────┬─────────┬───────────┬─────────────┬───────────────────┘
       │         │           │             │
       ▼         ▼           ▼             ▼
  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
  │Browser │ │Client  │ │ Storage  │ │   ES     │
  │(Play-  │ │(CNIPA  │ │ (MinIO/  │ │ Client   │
  │wright) │ │ adapter│ │ boto3)   │ │ (ES Py)  │
  └────┬───┘ └────┬───┘ └────┬─────┘ └────┬─────┘
       │          │          │            │
       ▼          ▼          ▼            ▼
  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
  │Captcha │ │Parser  │ │  MinIO   │ │  ES 8.x  │
  │Solver  │ │(select-│ │  server  │ │  server  │
  │(GPT-4o)│ │olax)   │ │          │ │          │
  └────────┘ └────────┘ └──────────┘ └──────────┘
```

### 3.2 目录结构

```
cnipa_scraper/
├── pyproject.toml
├── .env.example
├── README.md
├── src/cnipa_scraper/
│   ├── __init__.py
│   ├── __main__.py        # python -m cnipa_scraper
│   ├── cli.py
│   ├── config.py
│   ├── browser.py
│   ├── captcha.py
│   ├── client.py
│   ├── parser.py
│   ├── models.py
│   ├── storage.py
│   ├── searcher.py
│   └── pipeline.py
└── tests/
    ├── fixtures/
    │   ├── search_list.html
    │   └── detail.html
    ├── test_parser.py
    ├── test_models.py
    ├── test_storage.py    # moto mock
    └── test_searcher.py   # elasticsearch mock
```

## 4. 组件职责

| 模块 | 职责 |
|---|---|
| `config.py` | 用 `pydantic-settings` 从 .env / 环境变量读取并校验配置 |
| `browser.py` | Playwright 生命周期管理、上下文复用、反检测 |
| `captcha.py` | 截取滑块图 → GPT-4o 识别缺口 → 模拟人类拖拽 |
| `client.py` | CNIPA 搜索/详情页交互、XHR 拦截、详情页抓取 |
| `parser.py` | HTML / JSON → `PatentDetail` 模型 |
| `models.py` | `PatentDetail`、`PatentImage` 等 Pydantic 模型 |
| `storage.py` | MinIO/OSS 上传、路径生成、URL 返回 |
| `searcher.py` | ES 索引创建、bulk 写入、mapping 管理 |
| `pipeline.py` | 主流程编排：搜索 → 抓 → 解析 → 上传 → 索引 |
| `cli.py` | typer 命令行入口 |

## 5. 数据流

```
1. CLI 启动
   python -m cnipa_scraper run --date 2026-07-14
   ↓
2. Config.from_env()  (启动即校验所有必填项)
   ↓
3. Pipeline.run()
   ├── async with BrowserContext:
   │     page.goto(CNIPA_LIST_URL)
   │     if captcha_detected:
   │         captcha.solve(page)
   │     html = await search_today(date)
   │     patent_ids = parser.parse_search_results(html)
   │
   ├── for patent_id in patent_ids:
   │     detail_html, image_urls = await fetch_detail(patent_id)
   │     if captcha_detected: captcha.solve()
   │     detail = parser.parse_detail(detail_html)
   │
   │     # 并行下载与上传图片
   │     image_keys = await asyncio.gather(*[
   │         download_and_upload(url, patent_id, i)
   │         for i, url in enumerate(image_urls)
   │     ])
   │
   │     doc = detail.to_es_doc(image_keys)
   │     await es.index(index=ES_INDEX, id=patent_id, document=doc)
   │
   └── print summary report
```

## 6. ES 文档结构

```json
{
  "patent_id": "CN202630123456.7",
  "title": "一种包装盒的外观设计",
  "applicant": "某有限公司",
  "applicant_address": "广东省深圳市...",
  "inventor": ["张三"],
  "application_date": "2026-05-10",
  "publication_date": "2026-07-14",
  "main_classification": "09-03",
  "classification": ["09-03"],
  "abstract": "本外观设计涉及...",
  "claims": ["1. 本外观设计..."],
  "description": "...",
  "images": [
    {
      "oss_key": "patents/2026/07/CN202630123456.7/images/0.jpg",
      "oss_url": "https://minio.example.com/...",
      "view_type": "主视图",
      "order": 0
    }
  ],
  "source": "cnipa",
  "scraped_at": "2026-07-14T10:30:00Z"
}
```

Index mapping 关键字段：

- `patent_id`: `keyword`
- `title`, `abstract`, `description`: `text` + `standard` 分词
- `applicant`, `inventor[]`: `keyword`
- `*_date`: `date`
- `classification`: `keyword`（数组）
- `images`: `nested` 类型（便于单独查询）

## 7. OSS 路径规范

```
patents/{YYYY}/{MM}/{patent_id}/
├── images/
│   ├── 0.jpg         # 主视图
│   ├── 1.jpg         # 立体图
│   └── ...
└── metadata.json     # 可选：本地调试时存
```

URL 返回：使用 MinIO 的公开/签名 URL。

## 8. 错误处理

| 错误 | 处理策略 |
|---|---|
| 滑块识别失败 | 重试 3 次，每次调整 GPT-4o 提示词；3 次后保存截图到 `OUTPUT_DIR/failed_captchas/`，继续下一条 |
| 网络 5xx / 超时 | `tenacity` 指数退避：1s, 2s, 4s, 8s, 16s，最多 5 次 |
| HTML 解析失败 | 记录原始 HTML 到 `OUTPUT_DIR/failed_parse/`，跳过该专利 |
| ES 写入失败 | 写入 `OUTPUT_DIR/dlq/{patent_id}.json`，脚本退出码 1 |
| MinIO 上传失败 | 保留本地临时文件，记录 warning，不阻塞流程 |
| SIGINT (Ctrl-C) | 完成当前专利后退出（不丢半条数据） |
| 必填 env 缺失 | 启动时立即报错，列出缺失项，不进入主流程 |

## 9. 测试策略

| 层 | 方式 | 工具 |
|---|---|---|
| Models | 单元测试 | `pytest` |
| Parser | 单元测试 + HTML fixtures | `pytest` + `pytest-asyncio` |
| Storage | mock boto3 | `moto` |
| Searcher | mock elasticsearch | `elasticsearch.helpers.test` |
| Captcha | mock OpenAI | `pytest-mock` |
| Browser/Client | **不测** | CNIPA 验证码无法离线复现 |

CI 跑单元测试；真实跑通由人工触发。

## 10. CNIPA 特有挑战

1. **滑块验证码**：触发条件是短时间内多次请求或带特定 cookie
   - 缓解：每次请求间隔 2-5 秒随机；复用 cookie；用 `playwright-stealth` 减少指纹识别
2. **页面改版**：parser 是脆弱点
   - 缓解：每次抓取后做"健康检查"，关键字段（申请号、标题）都拿不到时记录告警
3. **图片防盗链**：CNIPA 图片 URL 通常带 token 或 referer 检查
   - 缓解：下载时携带来源页 cookie
4. **限速**：单 IP 高频请求会触发风控
   - 缓解：串行 + 随机延时；如需并行则控制并发 ≤ 2

## 11. 依赖清单

```toml
[project]
name = "cnipa-scraper"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "playwright>=1.45",
  "playwright-stealth>=1.0.6",
  "httpx>=0.27",
  "elasticsearch[async]>=8.13",
  "boto3>=1.34",
  "openai>=1.40",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "typer>=0.12",
  "rich>=13.7",
  "tenacity>=8.3",
  "selectolax>=0.3.17",
  "python-dotenv>=1.0",
]
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "moto[s3]>=5", "ruff>=0.5"]
```

## 12. 配置项（.env.example）

```bash
# CNIPA
CNIPA_LIST_URL=https://pss-system.cnipa.gov.cn/sipopublicsearch/portal/ux-simple-design-search!designSearchView.do

# MinIO（后续切阿里云 OSS 时改 endpoint 与 boto3 config）
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=changeme
MINIO_SECRET_KEY=changeme
MINIO_BUCKET=patents
MINIO_SECURE=true

# Elasticsearch
ES_URL=http://es.example.com:9200
ES_INDEX=cnipa-design-patents
ES_USERNAME=
ES_PASSWORD=

# OpenAI (GPT-4o)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# 输出
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

## 13. CLI 接口

```bash
# 抓取当天
python -m cnipa_scraper run

# 指定日期
python -m cnipa_scraper run --date 2026-07-14

# 限制条数（测试用）
python -m cnipa_scraper run --limit 5

# Dry run（不写入 ES，仅输出解析结果到 stdout）
python -m cnipa_scraper run --dry-run

# 健康检查（不抓详情，只搜列表）
python -m cnipa_scraper healthcheck
```

## 14. 风险与缓解

| 风险 | 缓解 |
|---|---|
| CNIPA 网站改版 | parser 失败时保存原始 HTML；告警而非静默失败 |
| GPT-4o 识别失败 | 重试 + 保存截图供手动处理；后续可替换为本地视觉模型 |
| MinIO 上传慢 | `asyncio.gather` 并行上传图片 |
| 重复爬取 | 用 ES `_id` = 申请号天然幂等；`op_type=index` 覆盖 |
| 单 IP 被封 | 串行 + 随机延时；支持 `HTTP_PROXY` 环境变量 |
| GPT-4o 成本 | 每天首次请求才调用，搜索阶段不需要视觉识别 |

## 15. 后续扩展

- 增加增量去重表（SQLite）记录已爬申请号
- 接入定时调度（cron / systemd timer）
- 替换为本地视觉模型（Qwen-VL）降低成本
- 支持发明专利 / 实用新型专利
- 切到阿里云 OSS（仅改 endpoint + 用 oss2 SDK）