# 小说日更助手 MVP

## 1. 产品定位

小说日更助手是 `AI小说工厂 v3.0` 外层新增的轻量产品化工作台，面向普通中文网文作者。

它不是承诺爆款、签约或收益的 AI 写文机器，而是帮助作者稳定完成日更创作决策：

- 选题开局
- 人设与金手指
- 黄金三章细纲
- 单章日更包
- 作品开头诊断

第一版目标是本地 MVP + 内测会员使用记录，可给内测作者演示，不做重 SaaS。

## 2. 五个核心功能

### 选题/开局生成器

根据题材、目标读者、关键词、平台和主角方向，生成书名方向、核心钩子、开局困境、金手指、前三章方向和风险提醒。

### 人设与金手指

生成主角、反派、关键配角、金手指机制、成长曲线、情绪发动机和可持续冲突来源。

### 黄金三章细纲

强调第一章 300 字内给钩子、第一章强冲突、第二章强化金手指/反转、第三章第一次爽点兑现，并保证每章结尾有追读钩子。

### 单章日更包

输出本章目标合同、场景细纲、正文草稿、结尾钩子、下一章预告和记忆更新。`generate_full_text=false` 时只生成合同、细纲和钩子。

### 作品开头诊断

按网文编辑视角检查开头钩子、主角目标、矛盾强度、爽点速度、可读性、追读理由和前 300 字吸引力。

## 3. 配置 DeepSeek API

项目使用 OpenAI-compatible 方式接入 DeepSeek。

在项目根目录创建 `.env`：

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的_deepseek_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

如果没有配置 API Key，系统会进入离线模式，并把 Prompt 导出到 `output/prompt_mvp_*.txt`，接口不会崩溃。

## 4. 启动后端

```bash
pip install -r requirements.txt
uvicorn web_api:app --reload --port 8000
```

状态接口：

```http
GET http://localhost:8000/api/mvp/status
```

## 5. 访问前端

浏览器打开：

```text
http://localhost:8000
```

默认进入“小说日更助手”，侧边栏仍保留原有 AI 小说工厂功能。

## 6. 内测会员额度

第一版没有注册、登录和支付系统，只做本地内测额度记录。

默认会员：

```text
default_member
```

默认额度：

```text
每月 30 次
```

配置项：

```bash
MVP_ENFORCE_QUOTA=false
MVP_DEFAULT_MONTHLY_QUOTA=30
```

当 `MVP_ENFORCE_QUOTA=false` 时，即使额度用完也允许继续生成，但仍会记录使用次数。

额度文件：

```text
data/mvp_usage.json
```

调用日志：

```text
data/mvp_generation_log.jsonl
```

## 7. 当前不支持

- 用户注册
- 登录系统
- 真实支付
- 自动续费
- 多租户权限
- SaaS 后台
- 模板商城
- 复杂运营系统

## 8. 后续 SaaS 化路线

可以在保持当前 MVP 工作流稳定的前提下，逐步增加：

- 真实会员系统
- 支付系统
- 多用户隔离
- 云端部署
- 用户作品库
- 模板商城
- 社群陪跑后台
- 平台数据复盘

当前阶段最重要的是验证 5 个功能里，作者最常用、最愿意付费的是哪一个。
