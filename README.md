# OntoGPT Plus

OntoGPT Plus 是 [OntoGPT](https://github.com/monarch-initiative/ontogpt) 的增强分支：保留上游的
SPIRES 抽取引擎、LinkML 模板体系与全部命令行能力，在此之上补齐一条可落地的工程链路——
**上传文档 → 选择/自动生成模板 → 并行抽取与本体对齐 → 生成 OWL 2 → 合并成知识库 → 同步到 Neo4j**。

上游适合作为库和 CLI 使用；本分支把它做成了一个可交互的工作台，面向中文/英文长文档的
批量知识抽取场景（内置电力行业模板，可扩展到任意领域）。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| Web Studio | 中文界面，文档上传、模板选择、模型配置、SSE 实时进度、任务中止、结果下载 |
| 文档解析 | PDF、DOCX、XLSX、HTML、Markdown、纯文本统一转纯文本，支持 GB18030 回退 |
| 并行分块抽取 | 按字符窗口切块，线程池并发调用模型，分块结果按模板合并 |
| 模板自动生成 | 给一段样例文本或领域提示词，由模型产出 LinkML YAML，编译为 Pydantic 模型并注册 |
| 模板自进化 | 抽取中发现的未归类字段写入 `auto_discovered_features`，可反哺模板并重新编译 |
| OWL 2 构建 | `OWL2Builder` 生成带命名个体、对象属性与数据属性的 OWL 2 DL 图；跨分片同实体自动对齐 IRI |
| 合并知识库 | 把所有已完成任务的 OWL 合并、去噪、升级为一个全局本体文件 |
| Ontology Explorer | 三栏式浏览类层级、个体属性与关系子图，支持关键词关联筛选 |
| 语义查询 API | `/api/ontology/search` 返回结构化实体、属性与关系，供外部系统或 Agent 直接调用 |
| Neo4j 同步 | OWL 幂等写入 Neo4j；抽取阶段可反查图谱复用已沉淀实体，跳过重复 LLM 调用 |
| 任务历史 | SQLite 持久化任务、状态、输入与结果，支持统计、单条删除与清空 |

## 与上游的关系

- 上游的 CLI（`ontogpt extract`、`generate-extract`、`pubmed-annotate` 等）、模板、评测与测试全部保留。
- 新增模块：
  - `src/ontogpt/webapp/`：FastAPI 工作台、`task_storage.py`（SQLite 历史库）、`ontology_inspector.py`（OWL → 图模型）
  - `src/ontogpt/io/owl_builder.py`：OWL 2 构建与规范化
  - `src/ontogpt/io/schema_generator.py`：模板生成、编译注册与自进化
  - `src/ontogpt/clients/neo4j_service.py`：Neo4j 同步与实体反查
  - `src/ontogpt/templates/power_grid.yaml`：电力系统设备、缺陷、保护动作与参量抽取模板
- `src/ontogpt/engines/spires_engine.py` 增加并行分块、进度回调、中止标志与动态特征归一。
- 上游提交保持可合并：本分支的改动集中在上述文件，不重写上游模块结构。

## 安装

需要 Python 3.10 及以上。

```bash
git clone https://github.com/xmsssssss/ontogpt-plus.git
cd ontogpt-plus

# 方式一：uv
uv sync --extra web

# 方式二：pip
pip install -e ".[web]"
```

只使用命令行时不需要 `web` 额外依赖：

```bash
pip install -e .
```

镜像源连接不稳定时，临时切到官方源再同步（PowerShell 用 `$env:UV_DEFAULT_INDEX="https://pypi.org/simple"`）：

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --extra web
```

## 快速开始

### 命令行

```bash
# 配置模型凭据（写入 oaklib 的凭据文件）
runoak set-apikey -e openai <your-api-key>

# 列出模板与模型
ontogpt list-templates
ontogpt list-models

# 抽取
echo "One treatment for high blood pressure is carvedilol." > example.txt
ontogpt extract -i example.txt -t drug
```

输出包含 `extracted_object` 与 `validation`：每个标识符都回到源本体校验过，
无法对齐的名称会带 `AUTO:` 前缀，而不是被模型编造。

### Web Studio

```bash
web-ontogpt                    # 默认 127.0.0.1:8000
web-ontogpt --port 8001        # 端口被占用时换一个
web-ontogpt --no-reload        # 关闭自动重载
uv run web-ontogpt --port 8001
```

浏览器打开 <http://127.0.0.1:8000>（换端口时对应调整）。也可以用
`ONTOGPT_WEB_HOST`、`ONTOGPT_WEB_PORT` 环境变量设置默认值。服务默认只监听回环地址，且**没有身份认证**，
不要直接暴露到公网。

## Web Studio 页面与接口

| 路径 | 作用 |
| --- | --- |
| `/` | 抽取表单：文档上传、模板与模型选择、语言模式、分块大小、并发数、缓存与图谱复用开关 |
| `/task/{task_id}` | 单次任务结果：HTML 报告、YAML、JSON、OWL，可分别下载 |
| `/history` | 任务历史与统计：完成/停止/失败计数、字符总量、删除与清空 |
| `/explorer` | Ontology Explorer：全局融合库或单任务的本体浏览 |
| `POST /api/auto-generate-schema` | 由样例文本或领域提示词生成并注册模板 |
| `POST /api/parse-document` | 上传文档并即时解析为文本 |
| `POST /api/start-task` | 启动抽取任务，返回 `task_id` |
| `GET /api/task-events/{task_id}` | SSE 实时进度流 |
| `POST /api/stop-task/{task_id}` | 中止任务并取消排队中的分块 |
| `GET /api/export-merged-owl` | 下载合并后的全局 OWL 知识库 |
| `GET /api/ontology/search` | 语义知识查询，返回实体、属性与关系 |
| `GET /api/neo4j/status`、`POST /api/neo4j/sync` | 连接测试与 OWL 同步 |
| `GET /api/cache-info`、`POST /api/clear-cache` | 查看/清空本地 LiteLLM 请求缓存 |

语言模式有三种：`auto`（仅约束输出格式）、`zh_ground_en`（中文输入、英文术语对齐）、
`zh_native`（中文术语原样保留，禁止占位符输出）。

## 模板自动生成与自进化

自动生成的模板会写入 `src/ontogpt/templates/<schema_id>.yaml` 并编译出同名 `.py`，
随后立刻出现在模板下拉框中。也就是说，**运行时会修改源码目录**；生产部署请把模板目录挂载为可写卷，
或把生成的模板纳入版本管理。

自进化默认关闭。开启后，模型在抽取时把模板未覆盖的专有字段写入 `auto_discovered_features`，
任务结束前再调用一次模型，把这些字段并入模板并重新编译；下一次任务即使用新模板。

## OWL 2 与 Neo4j

- 每次完成的任务都会生成 OWL；导出链路优先使用 `OWL2Builder`，失败时回退到 RDF 导出再转为 OWL/XML。
- `GET /api/export-merged-owl` 读取最近 500 条已完成任务，合并实体、关系与公理，输出
  `merged_knowledge_base.owl`。
- Neo4j 连接参数全部来自环境变量，未配置时相关功能自动跳过，不影响普通抽取：

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="<your-password>"
export NEO4J_DATABASE="neo4j"
```

抽取表单中的「图谱复用」开关控制是否在子抽取前反查 Neo4j：命中则直接复用已知实体画像，
不发起模型调用；关闭后完全离线，行为与上游一致。

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`MISTRAL_API_KEY`、`GROQ_API_KEY` 等 | 各模型提供方凭据，由 LiteLLM 读取 |
| `AZURE_API_KEY`、`AZURE_API_BASE`、`AZURE_API_VERSION` | Azure OpenAI |
| `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、`NEO4J_DATABASE` | Neo4j 连接 |

兼容上游的 `runoak set-apikey` 凭据文件：当对应提供方的环境变量缺失时，会回退读取 oaklib 的凭据。

## 项目结构

```text
src/ontogpt/
├── cli.py                 # 命令行入口
├── engines/               # SPIRES、映射、推理、同义等引擎
├── io/                    # 导出器、OWL 2 构建、模板生成
├── clients/               # LLM、PubMed、Wikipedia、Neo4j
├── templates/             # LinkML 模板（YAML + 编译产物）
└── webapp/                # FastAPI 工作台、历史库、本体浏览器
tests/                     # 单元测试与输出基线
docs/                      # 文档
skills/                    # Agent Skills（供编码 Agent 调用）
scripts/dev/               # 开发期调试脚本（不参与 CI）
```

## 开发与测试

```bash
uv run pytest                 # 单元测试
uv run tox -e lint            # black + isort
uv run tox -e flake8          # flake8
uv run tox -e mypy            # 类型检查
```

`scripts/dev/` 下是开发期用于排查 OWL、Neo4j 与历史库的手工脚本，运行前请备份
`task_history.db`。

## 引用与许可

抽取方法 SPIRES 见：Caufield JH, Hegde H, Emonet V, Harris NL, Joachimiak MP, Matentzoglu N, et al.
Structured prompt interrogation and recursive extraction of semantics (SPIRES): a method for populating
knowledge bases using zero-shot learning. *Bioinformatics*, Volume 40, Issue 3, March 2024, btae104.
<https://doi.org/10.1093/bioinformatics/btae104>

本项目基于 Monarch Initiative 的 OntoGPT（BSD-3-Clause），原始版权与致谢见 `LICENSE` 与 `CITATION.cff`。
本分支的修改同样以 BSD-3-Clause 发布。
