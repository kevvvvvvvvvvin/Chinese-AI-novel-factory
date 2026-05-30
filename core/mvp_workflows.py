"""
小说日更助手 MVP - 轻量工作流服务

该服务位于原有 Pipeline 外层，保留工厂原核心能力，同时提供可演示、
可记录、可额度化的产品接口。
"""
import os
from datetime import datetime
from typing import Callable, Dict, List, Tuple

from config import cfg
from core.mvp_prompts import MVPPromptBuilder
from core.quota_manager import QuotaManager


class MVPWorkflowService:
    def __init__(self, world, db, trope_engine, llm):
        self.world = world
        self.db = db
        self.trope_engine = trope_engine
        self.llm = llm
        self.quota = QuotaManager()

    def generate_topic(self, req: dict) -> dict:
        hints = self._trope_hints(req.get("keywords") or req.get("genre") or "开局 爽点", 5)
        return self._run(
            "topic_generator",
            req,
            lambda: MVPPromptBuilder.topic_generator(req, hints),
            max_tokens=3500,
            temperature=0.72,
        )

    def generate_characters(self, req: dict) -> dict:
        query = " ".join([
            str(req.get("genre", "")),
            str(req.get("story_seed", "")),
            str(req.get("desired_payoff", "")),
        ]).strip() or "人设 金手指 成长 爽点"
        hints = self._trope_hints(query, 5)
        return self._run(
            "character_generator",
            req,
            lambda: MVPPromptBuilder.character_generator(req, hints),
            max_tokens=3800,
            temperature=0.72,
        )

    def generate_golden_three(self, req: dict) -> dict:
        query = " ".join([
            str(req.get("genre", "")),
            str(req.get("core_hook", "")),
            str(req.get("main_conflict", "")),
        ]).strip() or "黄金三章 开局 冲突 爽点"
        hints = self._trope_hints(query, 5)
        return self._run(
            "golden_three_outline",
            req,
            lambda: MVPPromptBuilder.golden_three_outline(req, hints),
            max_tokens=4200,
            temperature=0.68,
        )

    def generate_daily_chapter_pack(self, req: dict) -> dict:
        query = " ".join([
            str(req.get("chapter_goal", "")),
            str(req.get("must_include", "")),
            str(req.get("style", "")),
        ]).strip() or "日更 章节 冲突 爽点 钩子"
        hints = self._trope_hints(query, 6)
        target_words = int(req.get("target_words", 2500) or 2500)
        generate_full_text = bool(req.get("generate_full_text", True))
        max_tokens = min(9000, max(3500, target_words * 2 + 1800)) if generate_full_text else 3500
        return self._run(
            "daily_chapter_pack",
            req,
            lambda: MVPPromptBuilder.daily_chapter_pack(req, hints),
            max_tokens=max_tokens,
            temperature=0.78,
        )

    def diagnose_opening(self, req: dict) -> dict:
        return self._run(
            "opening_diagnosis",
            req,
            lambda: MVPPromptBuilder.opening_diagnosis(req),
            max_tokens=3600,
            temperature=0.45,
        )

    def _run(
        self,
        workflow: str,
        req: Dict,
        prompt_factory: Callable[[], Tuple[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> Dict:
        member_id = req.get("member_id") or "default_member"
        input_summary = self._input_summary(req)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        quota_result = self.quota.consume(member_id, workflow, units=1, input_summary=input_summary)
        if not quota_result["allowed"]:
            result_summary = "额度不足，已阻止生成"
            self.quota.append_generation_log(
                member_id=member_id,
                workflow=workflow,
                input_summary=input_summary,
                success=False,
                result_summary=result_summary,
                tokens_total=0,
                model=self._llm_mode(),
            )
            return {
                "success": False,
                "workflow": workflow,
                "input_summary": input_summary,
                "result": {},
                "raw_text": "",
                "tokens": 0,
                "created_at": created_at,
                "error": result_summary,
                "quota": quota_result["quota"],
            }

        system_prompt, user_prompt = prompt_factory()
        token_before = getattr(self.llm, "total_tokens", 0)
        raw_text = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            step_name=f"mvp_{workflow}",
            expect_json=True,
        )
        tokens = max(0, int(getattr(self.llm, "total_tokens", 0) or 0) - int(token_before or 0))

        parse_error = False
        offline = raw_text is None
        if offline:
            result = {
                "offline_prompt_exported": True,
                "prompt_file": os.path.join(cfg.OUTPUT_DIR, f"prompt_mvp_{workflow}.txt"),
                "message": "当前 LLM 为离线模式，已导出 Prompt，可手动复制到 DeepSeek 或其他模型执行。",
            }
            raw_text_out = ""
        else:
            parsed = self.llm.parse_json_response(raw_text)
            parse_error = parsed is None
            result = parsed if isinstance(parsed, dict) else {"items": parsed} if parsed is not None else {}
            raw_text_out = raw_text or ""

        result_summary = self._result_summary(result, raw_text_out, offline, parse_error)
        self.quota.log_result(member_id, workflow, result_summary)
        self.quota.append_generation_log(
            member_id=member_id,
            workflow=workflow,
            input_summary=input_summary,
            success=True,
            result_summary=result_summary,
            tokens_total=tokens,
            model=self._llm_mode(),
        )

        return {
            "success": True,
            "workflow": workflow,
            "input_summary": input_summary,
            "result": result,
            "raw_text": raw_text_out,
            "tokens": tokens,
            "created_at": created_at,
            "offline": offline,
            "parse_error": parse_error,
            "quota": self.quota.get_usage(member_id),
        }

    def _trope_hints(self, query: str, count: int = 5) -> List[Dict]:
        if not self.trope_engine:
            return []
        try:
            results = self.trope_engine.semantic_search(query, top_k=count)
            hints = []
            for name, score in results:
                detail = self.trope_engine.get_trope_detail(name) or {}
                hints.append({
                    "name": name,
                    "category": detail.get("功能大类", ""),
                    "tags": detail.get("功能标签", [])[:5],
                    "desc": detail.get("描述", "")[:160],
                    "score": round(float(score), 3),
                })
            return hints
        except Exception:
            return []

    def _input_summary(self, req: Dict) -> str:
        parts = []
        for key, value in req.items():
            if key == "member_id":
                continue
            text = str(value).replace("\n", " ").strip()
            if not text:
                continue
            if key == "opening_text":
                text = text[:160]
            else:
                text = text[:80]
            parts.append(f"{key}={text}")
        return "；".join(parts)[:500] or "空输入"

    def _result_summary(self, result: Dict, raw_text: str, offline: bool, parse_error: bool) -> str:
        if offline:
            return "离线模式，已导出 Prompt"
        if parse_error:
            return (raw_text or "JSON 解析失败，空响应")[:300]
        if isinstance(result, dict):
            keys = list(result.keys())[:8]
            preview = "，".join(str(k) for k in keys)
            return f"JSON 字段：{preview}" if preview else "生成完成"
        return "生成完成"

    def _llm_mode(self) -> str:
        return getattr(self.llm, "mode", "offline") or "offline"
