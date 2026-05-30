# Open Source Checklist

发布前建议按这个清单过一遍。

## 1. 选择许可证

当前仓库尚未添加正式 `LICENSE`。请在发布前选择一种许可证：

- MIT：简洁宽松，适合希望别人自由使用和二次开发的项目。
- Apache-2.0：同样宽松，并包含较明确的专利授权条款。
- GPL-3.0：要求衍生项目继续开源，约束更强。

## 2. 检查不会提交的内容

确认这些路径没有进入 Git 暂存区：

- `.env`
- `.venv/`
- `projects/`
- `output/`
- `memory_bank/`
- `*.db`
- `data/mvp_usage.json`
- `data/mvp_generation_log.jsonl`
- `campaign_outline_*.md`
- `generated_story_outline.txt`
- 完整私有模板库，只保留必要示例模板

## 3. 扫描敏感信息

```bash
rg --hidden -n "API_KEY|sk-|secret|password|token|Bearer|/Users/|身份证|电话|微信|邮箱" .
```

如果发现真实密钥、个人路径、联系方式或未公开作品内容，先删除或改成示例占位符。

## 4. 验证基础可运行

```bash
python -m compileall config.py main.py web_api.py core tools
```

可选启动后端：

```bash
uvicorn web_api:app --reload --port 8000
```

## 5. 建议的首次发布步骤

由于当前目录的上级用户目录是 Git 仓库，请不要直接在用户目录执行 `git add .`。更安全的方式是把干净导出的开源包作为新仓库：

```bash
cd path/to/novel_factory_open_source
git init
git add .
git commit -m "Initial open source release"
```

之后再添加你自己的 GitHub 远程仓库地址并推送。
