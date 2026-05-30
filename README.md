# AI Novel Factory

AI Novel Factory 是一个面向中文长篇网文创作的本地工作台。它把世界观资料、套路模板、Prompt 生成、LLM 调用、章节生产和质量检查拆成可维护的模块，让作者可以在离线或在线模式下稳定推进小说项目。

项目当前包含两个入口：

- `main.py`：命令行交互式创作工作台。
- `web_api.py` + `static/index.html`：FastAPI 后端和单页前端，包含“小说日更助手 MVP”功能。

## 功能概览

- 套路库检索：基于 `data/templates_b` 和 `data/trope_index.json` 做关键词检索，可选接入语义搜索。
- Prompt 工厂：按选题、人设、黄金三章、单章日更、开头诊断等场景生成结构化 Prompt。
- LLM 网关：支持 DeepSeek、Anthropic Claude、OpenAI，并提供离线 Prompt 导出兜底。
- 流水线编排：支持从大纲到正文、审查报告、交接记忆的章节生产流程。
- 多项目管理：每个小说项目可拥有独立世界观、数据库、输出目录和模板副本。
- 本地额度记录：MVP 模式下可记录本地会员额度和调用日志，便于内测演示。

## 快速开始

Python 版本建议为 3.8 或更高。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

复制环境变量示例文件并填入自己的 API Key：

```bash
cp .env.example .env
```

如果不配置 API Key，系统会进入离线模式，把可复制到大模型网页端的 Prompt 导出到 `output/`。

启动 Web 版本：

```bash
uvicorn web_api:app --reload --port 8000
```

然后打开：

```text
http://localhost:8000
```

启动命令行版本：

```bash
python main.py
```

## 核心目录

```text
.
├── main.py                  # CLI 入口
├── web_api.py               # FastAPI 入口
├── config.py                # 路径、模型、API 配置
├── static/index.html        # 本地 Web 前端
├── core/
│   ├── data_manager.py      # JSON/SQLite 数据访问
│   ├── llm_gateway.py       # 多模型 LLM 适配和离线导出
│   ├── trope_engine.py      # 套路检索
│   ├── prompt_builder.py    # 工厂主流程 Prompt
│   ├── mvp_prompts.py       # 日更助手 Prompt
│   ├── pipeline.py          # 章节生产流水线
│   ├── autopilot.py         # 批量生产编排
│   ├── project_manager.py   # 多项目管理
│   └── quota_manager.py     # 本地额度和调用日志
├── data/
│   ├── my_world.json        # 示例世界观
│   ├── concept_map.json     # 示例概念映射
│   ├── trope_index.json     # 示例套路索引
│   ├── templates_b/         # 示例单套路逻辑骨架
│   └── templates_c/         # 示例长线任务模板
├── tools/rebuild_index.py   # 重建套路索引
└── docs/ARCHITECTURE.md     # 架构说明
```

## 数据与隐私

开源仓库应只包含通用代码、示例世界观和少量示例模板。完整私有套路库、个人作品和运行数据不建议公开。以下内容默认通过 `.gitignore` 排除：

- `.env` 和所有 API Key。
- `data/*.db`、`*.db`、SQLite 运行数据。
- `data/mvp_usage.json`、`data/mvp_generation_log.jsonl` 等本地内测记录。
- `output/`、`memory_bank/`、`projects/` 中的生成稿、个人作品和项目状态。
- `campaign_outline_*.md`、`generated_story_outline.txt` 等个人大纲产物。

本仓库采用轻量示例数据集：默认只保留少量 `templates_b` 和 `templates_c` 文件，用来展示框架如何加载、检索和编排模板。你可以在本地私有副本中放入完整模板库。

发布前可以运行：

```bash
rg --hidden -n "API_KEY|sk-|secret|password|token|/Users/|身份证|电话|微信|邮箱" .
```

## 配置

常用环境变量见 `.env.example`。

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

支持的 `LLM_PROVIDER`：

- `deepseek`
- `claude`
- `openai`

## 开发说明

重建套路索引：

```bash
python tools/rebuild_index.py
```

运行基础语法检查：

```bash
python -m compileall config.py main.py web_api.py core tools
```

## 许可证

许可证待确认。正式发布到 GitHub 前，请选择并添加 `LICENSE` 文件。常见选择包括 MIT、Apache-2.0、GPL-3.0；如果希望别人自由使用和二次开发，MIT 或 Apache-2.0 通常更轻量。
