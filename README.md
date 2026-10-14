# 毛选 DeepAgent（Mao's Wisdom）

一个可以从毛选中寻找答案的 RAG 项目：把用户提出的现实问题映射到毛选主题、检索本地知识库、挑选分析方法论，生成并校验**带引用的结构化 Markdown 分析报告**。基于 LangGraph 原生编排 + FastAPI 服务（原为 Coze 工作流导出，已改造成本地可跑）。

## 工作流主链路

```text
GraphInput(user_question, theme_codes, output_mode)
  → theme_router      主题识别：把问题映射到 1-3 个主题
  → source_retrieval  知识库检索：向量 + 关键词，返回最多 10 段引用
  → method_planner    方法选择：从若干分析方法中挑 1-3 个
  → analysis          结构化分析：生成 Markdown 报告草稿
  → critic            引用校验：核验引用真实性，输出终稿
  → GraphOutput(markdown_answer, citations, methods, selected_themes)
```

节点拓扑定义在 `src/graphs/graph.py`（直线图，五节点顺序执行）。

## 目录导览

| 目录 / 文件 | 内容 |
|---|---|
| `src/` | 主源码：FastAPI 入口、LangGraph 图与五个节点、存储适配与通用工具 |
| `config/` | 四个节点的 LLM 配置（模型参数 + 系统/用户提示词），属于工作流行为的一部分 |
| `assets/` | 项目数据资产：知识库文本、预建向量库、教员人格提示词、讲课文字稿 |
| `scripts/` | 知识库构建 / 导入、环境变量加载、端到端测试脚本 |
| `chat.html` | 前端对话页（流式展示各节点进度，默认连 `127.0.0.1:5000`） |
| `pyproject.toml` + `uv.lock` | 依赖声明与锁定版本（uv 管理，Python 3.12） |
| `requests.http` | 接口调用示例 |
| `PROJECT_TREE_ANNOTATED.md` | 项目树逐文件标注与「推 / 不推仓库」建议（部分内容已过时，见文末说明） |
| `毛选工作流实施包.md` | 工作流设计实施包文档 |
| `codegraph/` | 预留包占位（当前仅空 `__init__.py`） |

## 各目录细说

### src/ — 源码

- `main.py` FastAPI 服务入口：`GET /` 返回前端页面、`GET /health` 健康检查、`GET /graph_parameter` 返回工作流输入输出 schema、`POST /run` 完整分析、`POST /stream_run` SSE 流式（逐节点推送进度）
- `graphs/graph.py` 工作流拓扑：五个节点串联并 `compile()` 成 `main_graph`
- `graphs/state.py` 全局状态与各节点输入输出 Pydantic 模型
- `graphs/nodes/`
  - `theme_router_node.py` 主题识别（解析 LLM JSON，带默认兜底）
  - `source_node.py` 本地检索：Chroma 持久库 + Ollama `bge-m3` 查询向量化 + RRF 融合与关键词打分，取 Top 10
  - `method_node.py` 方法选择（解析 LLM JSON，带默认兜底）
  - `analysis_node.py` 渲染 prompt 生成分析草稿
  - `critic_node.py` 核验引用并输出终稿
  - `local_llm.py` OpenAI 兼容 LLM 调用封装（key / base_url / 模型名均来自环境变量）
- `storage/database/` SQLAlchemy 连接与 ORM 基类（无 `DATABASE_URL` 时回退本地 SQLite）
- `storage/memory/memory_saver.py` LangGraph checkpoint：优先 `PostgresSaver`，数据库不可用时回退 `MemorySaver`
- `storage/s3/s3_storage.py` S3 兼容对象存储封装（上传 / 下载 / 列表 / 签名 URL / 分片）
- `utils/file/file.py` 文件类型识别与文本、PDF、Office 内容抽取

### assets/ — 数据资产

- `mao_xuan_docs/` 7 篇精编知识库文本（矛盾论、实践论、论持久战、反对本本主义、中国革命战争的战略问题、方法论摘要卡、十大主题篇目映射表）
- `mao_xuan_db/` 预建的 Chroma 持久化向量库（集合 `mao_xuan`，由 `scripts/build_knowledge.py` 生成；**已随仓库提交，克隆后可直接检索**）
- `persona/persona_mao.md` 教员人格提示词
- `教员/` 156 篇讲课文字稿（教学语料，按专题分目录）

### scripts/

- `build_knowledge.py` 构建向量库：毛选四卷 TXT → 700 字 / 120 重叠切块 → Ollama `bge-m3` → Chroma 持久化
- `import_knowledge.py` 批量导入到 Coze 知识库（Coze 凭据只走环境变量）
- `load_env.py` 通过 Coze 工作负载身份拉取环境变量
- `test_pipeline.py` 端到端跑一遍五个节点（可用）
- `setup.sh` / `local_run.sh` / `http_run.sh` / `pack.sh` / `load_env.sh` 目前是**零字节空文件**（历史占位），请改用下面的 uv 命令

## 快速开始

前置：Python 3.12、[uv](https://docs.astral.sh/uv/)、本地 Ollama（检索侧需要 `bge-m3` 做查询向量化）。

```bash
uv sync          # 安装依赖（uv.lock 已锁定版本；pyproject 默认走阿里云 PyPI 镜像）
```

### LLM 环境变量

本地 Ollama（最省事）：

```powershell
$env:OPENAI_API_KEY="ollama"
$env:OPENAI_BASE_URL="http://127.0.0.1:11434/v1"
$env:MODEL_NAME="qwen3.5:2b"
$env:LOCAL_LLM_MAX_TOKENS="900"
```

任意 OpenAI 兼容服务：

```powershell
$env:OPENAI_API_KEY="你的 key"
$env:OPENAI_BASE_URL="你的 OpenAI 兼容地址"
$env:MODEL_NAME="你的模型名"
```

也支持 `LLM_API_KEY` / `DEEPSEEK_API_KEY` 作为 key 的兜底环境变量。默认本地演示模式里，主题识别与方法选择用规则节点加速、只有分析和校验走 LLM；要全链路都走 LLM 时设置 `$env:LOCAL_DEMO_FULL_LLM="1"`。

### 启动服务

```bash
uv run python src/main.py          # 监听 http://127.0.0.1:5000
```

浏览器打开 <http://127.0.0.1:5000> 即为对话页（`chat.html`）；手机 / 局域网可访问 `http://<本机IP>:5000/static/chat.html`。

### 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 返回前端页面 |
| GET | `/health` | 健康检查 |
| GET | `/graph_parameter` | 工作流输入输出 schema（前端动态渲染用） |
| POST | `/run` | 完整分析，返回 `markdown_answer` / `citations` / `methods` / `selected_themes` |
| POST | `/stream_run` | SSE 流式，逐节点推送进度 |

请求体：`{"user_question": "...", "theme_codes": [], "output_mode": "analysis"}`（示例见 `requests.http`）。

### 端到端测试

```bash
uv run python scripts/test_pipeline.py "团队执行力差，主要问题应该怎么找？"
```

### PyCharm 运行

- Project：本目录
- Interpreter：`.venv\Scripts\python.exe`
- Working directory：项目根目录
- Script path：`src/main.py`（端口 5000 已写在脚本内）

## 说明

- **检索依赖两件事**：`assets/mao_xuan_db`（已提交）与本地 Ollama 的 `bge-m3` 模型。换机器或想重建索引时，先 `ollama pull bge-m3`，再运行 `python scripts/build_knowledge.py`。
- `config/*.json` 里的 `model` 仍是 Coze 侧导出时用的豆包模型名（`doubao-seed-2-0-*`），本地演示实际以环境变量 `MODEL_NAME` 为准。
- 所有密钥（`OPENAI_API_KEY`、`LLM_API_KEY`、`DATABASE_URL`、`COZE_BUCKET_*` 等）一律走环境变量，不写进代码或配置。
- `local_demo.db`、`.venv/`、缓存与 `.env` 已由 `.gitignore` 排除，不在版本库内。
- `PROJECT_TREE_ANNOTATED.md` 是早期项目树标注，其中 `.coze`、`AGENTS.md`、`assets/mao_xuan_docs` 为唯一数据源等描述与现状已不一致（现为 `assets/mao_xuan_db` 向量库 + `assets/教员` 语料），阅读时以本 README 为准。
