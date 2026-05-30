"""
小说日更助手 MVP - 本地额度与调用日志

第一版没有真实用户系统，只记录 default_member 的本地内测额度。
"""
import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional

from config import cfg

_QUOTA_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _month() -> str:
    return datetime.now().strftime("%Y-%m")


class QuotaManager:
    def __init__(self, usage_path: Optional[str] = None, generation_log_path: Optional[str] = None):
        self.usage_path = usage_path or os.path.join(cfg.DATA_DIR, "mvp_usage.json")
        self.generation_log_path = generation_log_path or os.path.join(cfg.DATA_DIR, "mvp_generation_log.jsonl")
        self.enforce_quota = os.environ.get("MVP_ENFORCE_QUOTA", "false").lower() == "true"
        self.default_monthly_quota = int(os.environ.get("MVP_DEFAULT_MONTHLY_QUOTA", "30") or 30)
        os.makedirs(os.path.dirname(self.usage_path), exist_ok=True)
        self._ensure_files()

    def get_usage(self, member_id: str = "default_member") -> Dict:
        with _QUOTA_LOCK:
            data = self._load_usage()
            member = self._ensure_member(data, member_id)
            self._reset_if_needed(member)
            self._save_usage(data)
            return self._public_usage(member)

    def consume(
        self,
        member_id: str = "default_member",
        workflow: str = "",
        units: int = 1,
        input_summary: str = "",
    ) -> Dict:
        with _QUOTA_LOCK:
            data = self._load_usage()
            member = self._ensure_member(data, member_id)
            self._reset_if_needed(member)

            remaining_before = max(0, int(member.get("monthly_quota", 0)) - int(member.get("used", 0)))
            allowed = (remaining_before >= units) or not self.enforce_quota

            if allowed:
                member["used"] = int(member.get("used", 0)) + units
                member.setdefault("logs", []).append({
                    "created_at": _now(),
                    "workflow": workflow,
                    "units": units,
                    "input_summary": input_summary[:500],
                    "result_summary": "",
                })
                member["logs"] = member["logs"][-300:]
                self._save_usage(data)

            return {
                "allowed": allowed,
                "enforced": self.enforce_quota,
                "member_id": member_id,
                "workflow": workflow,
                "units": units,
                "quota": self._public_usage(member),
            }

    def reset_member(
        self,
        member_id: str = "default_member",
        monthly_quota: int = 30,
        plan: str = "internal_test",
    ) -> Dict:
        with _QUOTA_LOCK:
            data = self._load_usage()
            data[member_id] = {
                "plan": plan,
                "monthly_quota": monthly_quota,
                "used": 0,
                "reset_month": _month(),
                "logs": [],
            }
            self._save_usage(data)
            return self._public_usage(data[member_id])

    def log_result(
        self,
        member_id: str = "default_member",
        workflow: str = "",
        result_summary: str = "",
    ) -> None:
        with _QUOTA_LOCK:
            data = self._load_usage()
            member = self._ensure_member(data, member_id)
            logs = member.setdefault("logs", [])
            for item in reversed(logs):
                if item.get("workflow") == workflow and not item.get("result_summary"):
                    item["result_summary"] = result_summary[:500]
                    item["completed_at"] = _now()
                    break
            self._save_usage(data)

    def append_generation_log(
        self,
        member_id: str,
        workflow: str,
        input_summary: str,
        success: bool,
        result_summary: str,
        tokens_total: int = 0,
        model: str = "offline",
    ) -> None:
        os.makedirs(os.path.dirname(self.generation_log_path), exist_ok=True)
        row = {
            "created_at": _now(),
            "member_id": member_id,
            "workflow": workflow,
            "input_summary": input_summary[:500],
            "success": bool(success),
            "result_summary": result_summary[:500],
            "tokens_total": int(tokens_total or 0),
            "model": model or "offline",
        }
        with _QUOTA_LOCK:
            with open(self.generation_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _ensure_files(self) -> None:
        if not os.path.exists(self.usage_path):
            self.reset_member(
                "default_member",
                monthly_quota=self.default_monthly_quota,
                plan="internal_test",
            )
        if not os.path.exists(self.generation_log_path):
            open(self.generation_log_path, "a", encoding="utf-8").close()

    def _load_usage(self) -> Dict:
        try:
            with open(self.usage_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_usage(self, data: Dict) -> None:
        os.makedirs(os.path.dirname(self.usage_path), exist_ok=True)
        with open(self.usage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _ensure_member(self, data: Dict, member_id: str) -> Dict:
        if member_id not in data:
            data[member_id] = {
                "plan": "internal_test",
                "monthly_quota": self.default_monthly_quota,
                "used": 0,
                "reset_month": _month(),
                "logs": [],
            }
        return data[member_id]

    def _reset_if_needed(self, member: Dict) -> None:
        current_month = _month()
        if member.get("reset_month") != current_month:
            member["used"] = 0
            member["reset_month"] = current_month
            member.setdefault("logs", []).append({
                "created_at": _now(),
                "workflow": "quota_reset",
                "units": 0,
                "input_summary": f"自动重置到 {current_month}",
                "result_summary": "",
            })

    def _public_usage(self, member: Dict) -> Dict:
        monthly_quota = int(member.get("monthly_quota", self.default_monthly_quota) or 0)
        used = int(member.get("used", 0) or 0)
        return {
            "plan": member.get("plan", "internal_test"),
            "monthly_quota": monthly_quota,
            "used": used,
            "remaining": max(0, monthly_quota - used),
            "reset_month": member.get("reset_month", _month()),
            "enforce_quota": self.enforce_quota,
        }
