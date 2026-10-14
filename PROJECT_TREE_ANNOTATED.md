# 项目树状图与推仓库说明

项目路径：`E:\Hangzhou\Coze_Dify\智能体平台：Coze平台\project_20260804_230029\projects`

项目名称：毛选 DeepAgent MVP 分析工作流

项目定位：基于 LangGraph / FastAPI / Coze Vibe Coding 的工作流项目，将用户现实问题映射到毛选主题、检索本地知识库、选择方法论、生成并校验结构化 Markdown 分析报告。

## 标注规则

- `推仓库`：源码、配置、脚本、文档、锁文件等，属于项目可复现交付内容，建议纳入版本库。
- `不推仓库/本地生成`：虚拟环境、缓存、数据库、本地密钥、构建产物等，只在本机运行时产生，不建议提交。
- `视情况`：根据交付范围决定；例如教学语料可以提交，真实私有数据或大文件不提交。

## 工作流主链路

```text
GraphInput(user_question, theme_codes, output_mode)
  -> theme_router
  -> source_retrieval
  -> method_planner
  -> analysis
  -> critic
  -> GraphOutput(markdown_answer, citations, methods, action_checklist)
```

- `theme_router`：主题识别节点，使用 `config/theme_router_llm_cfg.json`，把用户问题映射到十大主题中的 1-3 个主题。
- `source_retrieval`：知识库检索节点，读取 `assets/mao_xuan_docs/*.txt`，按关键词切分、打分并返回最多 10 段引用片段。
- `method_planner`：方法选择节点，使用 `config/method_planner_llm_cfg.json`，从五个分析方法中选择 1-3 个。
- `analysis`：结构化分析节点，使用 `config/analysis_llm_cfg.json`，生成完整 Markdown 分析草稿。
- `critic`：引用校验节点，使用 `config/critic_llm_cfg.json`，核验引用真实性并输出最终 Markdown。

## 项目树状图

```text
projects/
|-- .coze                                      [推仓库] Coze 项目元配置：入口、Python 版本、dev/deploy 构建与运行命令。
|-- .gitignore                                 [推仓库] Git 忽略规则：排除虚拟环境、缓存、密钥、大文件、构建产物等。
|-- .python-version                            [推仓库] Python 版本约束；项目当前要求 Python 3.12。
|-- .venv/                                     [不推仓库/本地生成] 本地 uv/pip 虚拟环境，只服务本机开发与调试。
|-- AGENTS.md                                  [推仓库] Agent/工作流说明：项目概述、节点清单、数据流、知识库说明。
|-- PROJECT_TREE_ANNOTATED.md                  [推仓库] 当前文档：项目树状图、分支作用、推仓库建议。
|-- README.md                                  [推仓库] 项目基础说明和本地运行命令。
|-- assets/                                    [视情况] 项目数据资产目录；当前保存毛选知识库文本，教学 demo 可提交，私有/大体积资料不提交。
|   `-- mao_xuan_docs/                         [视情况] 本地检索语料目录，source_retrieval 节点直接读取这里的 txt 文档。
|       |-- 中国革命战争的战略问题.txt          [视情况] 知识库文档，供检索节点引用。
|       |-- 十大主题篇目映射表.txt              [视情况] 主题与篇目映射资料，辅助主题判断和检索。
|       |-- 反对本本主义.txt                    [视情况] 知识库文档，调查研究方法相关。
|       |-- 实践论.txt                          [视情况] 知识库文档，实践-认识-再实践方法相关。
|       |-- 方法论摘要卡.txt                    [视情况] 方法论提炼资料，供检索和分析引用。
|       |-- 矛盾论.txt                          [视情况] 知识库文档，主要矛盾分析相关。
|       `-- 论持久战.txt                        [视情况] 知识库文档，阶段判断和力量对比相关。
|-- config/                                    [推仓库] LLM 节点配置目录，保存模型参数、系统提示词、用户提示词模板。
|   |-- analysis_llm_cfg.json                 [推仓库] AnalysisAgent 配置，控制结构化深度分析报告生成。
|   |-- critic_llm_cfg.json                   [推仓库] CriticAgent 配置，控制引用真实性和判断依据校验。
|   |-- method_planner_llm_cfg.json           [推仓库] MethodPlannerAgent 配置，控制分析方法选择。
|   `-- theme_router_llm_cfg.json              [推仓库] ThemeRouterAgent 配置，控制十大主题识别。
|-- local_demo.db                              [不推仓库/本地生成] SQLite 本地演示数据库；无 DATABASE_URL 时自动使用。
|-- pyproject.toml                             [推仓库] Python 项目元数据、依赖、dev 依赖、pytest 配置、uv 镜像源配置。
|-- scripts/                                   [推仓库] 本地、部署、打包和知识库导入脚本。
|   |-- http_run.sh                            [推仓库] 启动 FastAPI HTTP 服务，默认端口 5000。
|   |-- import_knowledge.py                    [推仓库] 将 `assets/mao_xuan_docs` 批量导入 Coze 知识库 `mao_xuan_deepagent`。
|   |-- load_env.py                            [推仓库] 通过 coze_workload_identity 拉取项目环境变量并输出 export 语句。
|   |-- load_env.sh                            [推仓库] Shell 包装脚本，调用 `load_env.py` 加载环境变量。
|   |-- local_run.sh                           [推仓库] 本地运行入口，支持 `flow`、`node`、`http`、`agent` 模式。
|   |-- pack.sh                                [推仓库] 打包前锁定依赖，执行 `uv lock`。
|   `-- setup.sh                               [推仓库] 安装依赖；部署模式安装到 PIP_TARGET，开发模式同步到 `.venv`。
|-- src/                                       [推仓库] 项目主源码目录。
|   |-- __init__.py                            [推仓库] Python 包标识文件。
|   |-- main.py                                [推仓库] FastAPI 服务入口和 CLI 入口，提供 `/run`、`/stream_run`、`/node_run`、`/async_run`、`/health` 等接口。
|   |-- agents/                                [推仓库] Agent 项目预留包；当前仅有包初始化文件。
|   |   `-- __init__.py                        [推仓库] 包初始化文件。
|   |-- graphs/                                [推仓库] LangGraph 工作流定义、状态模型和节点实现。
|   |   |-- __init__.py                        [推仓库] 包初始化文件。
|   |   |-- graph.py                            [推仓库] 工作流拓扑定义：添加节点、设置入口、连接节点边并编译图。
|   |   |-- state.py                            [推仓库] 全局状态、输入输出模型、各节点输入输出 Pydantic schema。
|   |   `-- nodes/                             [推仓库] 工作流节点实现目录。
|   |       |-- __init__.py                    [推仓库] 包初始化文件。
|   |       |-- analysis_node.py               [推仓库] 分析节点，渲染 prompt 并调用 LLM 生成报告草稿。
|   |       |-- critic_node.py                 [推仓库] 校验节点，调用 LLM 校验报告并构造引用列表。
|   |       |-- local_llm.py                   [推仓库] OpenAI 兼容 LLM 调用封装，读取 OPENAI/LLM 相关环境变量。
|   |       |-- method_planner_node.py         [推仓库] 方法选择节点，解析 LLM JSON 输出并带默认兜底。
|   |       |-- source_retrieval_node.py       [推仓库] 本地文本检索节点，执行切分、关键词打分和结果格式化。
|   |       `-- theme_router_node.py           [推仓库] 主题识别节点，解析 LLM JSON 输出并带默认兜底。
|   |-- storage/                               [推仓库] 存储相关适配层。
|   |   |-- __init__.py                        [推仓库] 包初始化文件。
|   |   |-- database/                          [推仓库] 数据库连接和 ORM 基类。
|   |   |   |-- __init__.py                    [推仓库] 包初始化文件。
|   |   |   |-- db.py                            [推仓库] 数据库 URL 解析、SQLAlchemy engine/session 创建；默认回退到本地 SQLite。
|   |   |   `-- shared/                        [推仓库] 数据库共享模型目录。
|   |   |       |-- __init__.py                    [推仓库] 包初始化文件。
|   |   |       `-- model.py                   [推仓库] SQLAlchemy DeclarativeBase 基类。
|   |   |-- memory/                            [推仓库] LangGraph checkpoint 存储适配。
|   |   |   |-- __init__.py                    [推仓库] 包初始化文件。
|   |   |   `-- memory_saver.py                [推仓库] 优先使用 PostgresSaver，数据库不可用时回退 MemorySaver。
|   |   `-- s3/                                [推仓库] S3 兼容对象存储适配。
|   |       |-- __init__.py                        [推仓库] 包初始化文件。
|   |       `-- s3_storage.py                  [推仓库] 文件上传、下载、列表、签名 URL、分片上传等能力封装。
|   |-- tools/                                 [推仓库] 工具包预留目录；当前仅有包初始化文件。
|   |   `-- __init__.py                        [推仓库] 包初始化文件。
|   `-- utils/                                 [推仓库] 通用工具目录。
|       |-- __init__.py                          [推仓库] 包初始化文件。
|       `-- file/                              [推仓库] 文件处理工具目录。
|           |-- __init__.py                      [推仓库] 包初始化文件。
|           `-- file.py                         [推仓库] 文件类型识别、下载、读取 bytes、抽取 PDF/Office/文本内容。
|-- src/**/__pycache__/                        [不推仓库/本地生成] Python 字节码缓存目录，由运行时自动生成。
|-- src/**/*.pyc                               [不推仓库/本地生成] Python 编译缓存文件，由运行时自动生成。
|-- uv.lock                                    [推仓库] uv 依赖锁文件，保证安装版本可复现。
```

## 应推仓库清单

- `src/`：核心业务代码、LangGraph 图、节点、存储和工具封装。
- `config/`：节点 LLM 配置和 prompt 模板，是工作流行为的一部分。
- `scripts/`：安装、运行、打包、导入知识库脚本。
- `assets/mao_xuan_docs/`：当前 demo 依赖的本地知识库文本；如果这些资料确认可公开和体积可控，建议提交。
- `.coze`：Coze 项目入口与 dev/deploy 命令配置。
- `.python-version`：Python 版本提示。
- `pyproject.toml`、`uv.lock`：依赖声明和锁定版本。
- `README.md`、`AGENTS.md`、`PROJECT_TREE_ANNOTATED.md`：项目说明和协作说明。
- `.gitignore`：忽略规则。

## 不应推仓库清单

- `.venv/`：本机虚拟环境，可通过 `uv sync` 或 `scripts/setup.sh` 重新生成。
- `local_demo.db`：本地 SQLite 演示数据库，包含运行状态或临时数据，不属于源码交付。
- `__pycache__/`、`*.pyc`：Python 运行缓存。
- `.env`、`/.env`：本地密钥和环境变量文件，不能提交。
- `dist/`、`node_modules/`、`vendor/`、`*.egg-info/`：构建或依赖产物。
- `.preview`、`.codegraph`：本地预览和索引文件。
- 大文件或二进制资料：`*.mp4`、`*.zip`、`*.pdf`、`*.docx`、`*.xlsx`、`*.pptx` 等已在 `.gitignore` 中默认排除。

## 视情况处理

- `assets/` 下的文本知识库：当前项目运行依赖这些 txt 文档，本地 demo 建议保留；如果内容涉及版权、内部资料或体积扩大，应改为外部数据导入流程，不直接推仓库。
- `scripts/import_knowledge.py`：脚本可推仓库，但运行脚本所需的 Coze 凭据、token、endpoint 只能放环境变量，不能写入代码或文档。
- S3/数据库相关配置：代码可推仓库；`COZE_BUCKET_*`、`DATABASE_URL`、`PGDATABASE_URL`、`OPENAI_API_KEY`、`LLM_API_KEY` 等真实值不能提交。

## 本地运行入口

```bash
bash scripts/local_run.sh -m flow
bash scripts/local_run.sh -m node -n theme_router
bash scripts/http_run.sh -p 5000
```

运行前通常需要准备：

- Python 3.12 环境。
- 依赖：`uv sync` 或 `bash scripts/setup.sh`。
- LLM 环境变量：`OPENAI_API_KEY` 或 `LLM_API_KEY`，以及可选的 `OPENAI_BASE_URL` / `OPENAI_API_BASE` / `LLM_BASE_URL`、`MODEL_NAME` / `LLM_MODEL`。
- 如果使用持久化 checkpoint，配置 `DATABASE_URL` 或 `PGDATABASE_URL`；否则本地默认回退 `local_demo.db` 和内存 checkpointer。
