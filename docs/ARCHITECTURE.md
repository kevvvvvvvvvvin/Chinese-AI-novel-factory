# Architecture

AI Novel Factory 的核心目标是把“网文生产”拆成稳定的本地模块：资料层负责承载世界观和模板，Prompt 层负责把用户目标翻译成可执行任务，LLM 层负责在线生成或离线导出，流水线层负责把单步能力编排成章节生产。

## 入口层

- `main.py`：命令行工作台，适合本地作者按菜单操作。
- `web_api.py`：FastAPI 服务，暴露项目、世界观、套路、章节生产、MVP 日更助手等接口。
- `static/index.html`：单页前端，直接由 FastAPI 根路径提供。

## 应用服务层

- `core/pipeline.py`：章节生产主流水线，覆盖大纲、正文、审查、交接报告。
- `core/autopilot.py`：批量生产和自动推进逻辑。
- `core/mvp_workflows.py`：小说日更助手的五个轻量工作流。
- `core/project_manager.py`：多项目创建、切换、删除和项目级数据加载。

## 领域能力层

- `core/trope_engine.py`：套路搜索、分类浏览、模板详情读取。
- `core/prompt_builder.py`：完整小说工厂流程的 Prompt 组装。
- `core/mvp_prompts.py`：MVP 产品场景的 Prompt 组装。

## 基础设施层

- `core/llm_gateway.py`：统一 DeepSeek、Claude、OpenAI 的调用方式；没有 API Key 时自动导出离线 Prompt。
- `core/data_manager.py`：JSON 文件、SQLite 表结构、章节/角色/任务日志管理。
- `core/quota_manager.py`：本地内测额度和调用日志。
- `config.py`：集中管理目录、模型、API Key 和生成参数。

## 数据资产层

- `data/my_world.json`：示例世界观。
- `data/concept_map.json`：示例概念映射。
- `data/trope_index.json`：示例模板索引。
- `data/templates_b/*.txt`：示例剧情套路逻辑骨架。
- `data/templates_c/*.json`：示例多章节任务链模板。

## 在线与离线模式

在线模式：

1. 在 `.env` 中设置 `LLM_PROVIDER` 和对应 API Key。
2. `LLMGateway.initialize()` 选择可用模型。
3. 流水线调用模型并写入数据库、日志或前端响应。

离线模式：

1. 不设置 API Key。
2. `LLMGateway.generate()` 不请求网络，而是把完整 Prompt 写入 `output/prompt_*.txt`。
3. 作者可以手动复制 Prompt 到任意模型界面，再把结果回填。

## 开源边界

建议公开：

- `core/`、`tools/`、`static/`、入口文件和示例配置。
- 少量 `data/templates_b`、`data/templates_c`、`data/trope_index.json` 示例模板资产。
- `data/my_world.json`、`data/concept_map.json` 作为示例数据。

不建议公开：

- `.env`、API Key、真实用户资料。
- `projects/` 中的个人小说项目。
- `output/`、`memory_bank/` 中的生成稿和交接记忆。
- `*.db`、`data/mvp_usage.json`、`data/mvp_generation_log.jsonl` 等运行状态。
- 完整私有套路库和未公开创作方法论资产。
