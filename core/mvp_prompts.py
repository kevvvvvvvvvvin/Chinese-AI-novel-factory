"""
小说日更助手 MVP - Prompt 构建器

这组 Prompt 是产品层工作流，不替代原有 PromptBuilder / Pipeline。
目标是帮助作者做创作决策、拆纲和诊断，而不是承诺爆款或自动代写。
"""
import json
from typing import Any, Dict, List, Tuple


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _common_system(extra: str = "") -> str:
    return f"""你是一位中文网文商业编辑，熟悉番茄、七猫、起点、短剧爽文的读者偏好。
你的任务不是替作者承诺爆款，而是帮助作者提高开局吸引力、日更稳定性和长篇连续性。

工作原则：
1. 你是创作助手，不是保证签约、保证爆款、保证赚钱的营销话术机器。
2. 不抄袭具体作品，不直接复刻知名小说设定、角色、桥段或书名。
3. 不输出违法、过度低俗、仇恨、诈骗、侵权或鼓励现实伤害的内容。
4. 所有建议都要服务于作者可执行的创作决策。
5. 除明确要求正文草稿外，严格输出 JSON，不要输出 Markdown，不要输出解释。
{extra}""".strip()


class MVPPromptBuilder:
    """小说日更助手 MVP 的 5 个轻量工作流 Prompt。"""

    @staticmethod
    def topic_generator(req: Dict, trope_hints: List[Dict] = None) -> Tuple[str, str]:
        system = _common_system("请像网文选题编辑一样，给出可执行的开局方案和风险提醒。")
        user = {
            "任务": "生成选题/开局方案",
            "输入": {
                "genre": req.get("genre", ""),
                "audience": req.get("audience", ""),
                "keywords": req.get("keywords", ""),
                "tone": req.get("tone", ""),
                "protagonist_direction": req.get("protagonist_direction", ""),
                "platform": req.get("platform", ""),
            },
            "可参考套路方向": trope_hints or [],
            "输出要求": {
                "titles": ["给出 5-8 个可改写书名方向，避免碰瓷具体作品"],
                "core_hook": "一句话开局钩子",
                "market_positioning": "读者预期与平台适配说明",
                "protagonist_starting_problem": "主角开局困境，必须具体、有压迫感",
                "golden_finger": "金手指机制，说明触发、限制、成长空间",
                "first_three_chapters": [
                    "第1章：300字内出现钩子和强冲突",
                    "第2章：金手指/反转强化",
                    "第3章：第一次爽点兑现并留下追读钩子",
                ],
                "reader_promise": "对目标读者的稳定爽点承诺",
                "risk_notes": ["同质化风险", "尺度风险", "长篇续航风险"],
            },
            "严格 JSON Schema": {
                "titles": [],
                "core_hook": "",
                "market_positioning": "",
                "protagonist_starting_problem": "",
                "golden_finger": "",
                "first_three_chapters": [],
                "reader_promise": "",
                "risk_notes": [],
            },
        }
        return system, _json(user)

    @staticmethod
    def character_generator(req: Dict, trope_hints: List[Dict] = None) -> Tuple[str, str]:
        system = _common_system("请像人设编辑一样，优先保证人设冲突、爽点兑现和长篇续航。")
        user = {
            "任务": "生成人设与金手指方案",
            "输入": {
                "genre": req.get("genre", ""),
                "audience": req.get("audience", ""),
                "story_seed": req.get("story_seed", ""),
                "protagonist_identity": req.get("protagonist_identity", ""),
                "desired_payoff": req.get("desired_payoff", ""),
            },
            "可参考套路方向": trope_hints or [],
            "设计重点": [
                "主角要有清晰初始短板和可持续目标",
                "反派不只当工具人，要能制造层级压力",
                "金手指必须有触发条件、限制、升级节奏和反噬/代价",
                "情绪发动机要能支撑日更推进",
            ],
            "严格 JSON Schema": {
                "protagonist": {},
                "antagonists": [],
                "heroine_or_key_supporting_roles": [],
                "golden_finger": {},
                "growth_curve": [],
                "emotional_engine": "",
                "sustainable_conflict_sources": [],
            },
        }
        return system, _json(user)

    @staticmethod
    def golden_three_outline(req: Dict, trope_hints: List[Dict] = None) -> Tuple[str, str]:
        system = _common_system("请像负责留存的网文主编一样，细拆黄金三章。")
        user = {
            "任务": "生成黄金三章细纲",
            "输入": {
                "title_direction": req.get("title_direction", ""),
                "genre": req.get("genre", ""),
                "core_hook": req.get("core_hook", ""),
                "protagonist": req.get("protagonist", ""),
                "golden_finger": req.get("golden_finger", ""),
                "main_conflict": req.get("main_conflict", ""),
            },
            "硬性要求": [
                "第一章 300 字内必须给钩子",
                "第一章必须出现强冲突，不要慢热铺设",
                "第二章强化金手指或完成关键反转",
                "第三章完成第一次爽点兑现",
                "每章结尾必须有明确追读钩子",
                "不要承诺签约、爆款或赚钱",
            ],
            "可参考套路方向": trope_hints or [],
            "严格 JSON Schema": {
                "chapter_1": {
                    "title": "",
                    "opening_hook": "",
                    "main_conflict": "",
                    "payoff": "",
                    "ending_hook": "",
                    "reader_expectation": "",
                },
                "chapter_2": {
                    "title": "",
                    "opening_hook": "",
                    "main_conflict": "",
                    "payoff": "",
                    "ending_hook": "",
                    "reader_expectation": "",
                },
                "chapter_3": {
                    "title": "",
                    "opening_hook": "",
                    "main_conflict": "",
                    "payoff": "",
                    "ending_hook": "",
                    "reader_expectation": "",
                },
                "overall_notes": [],
            },
        }
        return system, _json(user)

    @staticmethod
    def daily_chapter_pack(req: Dict, trope_hints: List[Dict] = None) -> Tuple[str, str]:
        generate_full_text = bool(req.get("generate_full_text", True))
        system = _common_system(
            "请像日更陪跑编辑一样，把当天这一章拆成作者能直接执行的目标、细纲、钩子和记忆更新。"
        )
        user = {
            "任务": "生成单章日更包",
            "输入": {
                "chapter_num": req.get("chapter_num", ""),
                "story_context": req.get("story_context", ""),
                "chapter_goal": req.get("chapter_goal", ""),
                "characters_state": req.get("characters_state", ""),
                "must_include": req.get("must_include", ""),
                "style": req.get("style", ""),
                "target_words": req.get("target_words", 2500),
                "generate_full_text": generate_full_text,
            },
            "生成规则": [
                "先明确本章目标合同：本章必须完成什么、不能偏离什么、读者要得到什么",
                "细纲要按场景推进，包含冲突、升级、兑现、收尾",
                "结尾必须留下下一章追读钩子",
                "记忆更新要记录角色状态、伏笔、物品、关系变化",
                "正文草稿是辅助作者修改的初稿，不要声称成稿必然可直接发布",
            ],
            "可参考套路方向": trope_hints or [],
            "严格 JSON Schema": {
                "chapter_goal_contract": {},
                "chapter_outline": "",
                "chapter_draft": "如果 generate_full_text=false，这里输出空字符串；如果为 true，输出完整正文草稿",
                "ending_hook": "",
                "next_chapter_preview": "",
                "memory_updates": [],
            },
        }
        return system, _json(user)

    @staticmethod
    def opening_diagnosis(req: Dict) -> Tuple[str, str]:
        system = _common_system(
            "请像网文编辑诊断作品开头，不要像作文老师。重点判断读者会不会继续翻下一页。"
        )
        user = {
            "任务": "诊断作品开头",
            "输入": {
                "genre": req.get("genre", ""),
                "platform": req.get("platform", ""),
                "target_reader": req.get("target_reader", ""),
                "opening_text": req.get("opening_text", ""),
            },
            "诊断重点": [
                "开头钩子是否强",
                "主角目标是否清楚",
                "矛盾是否足够尖锐",
                "爽点来得是否太晚",
                "信息量是否过载",
                "是否有继续追读理由",
                "前 300 字是否抓人",
            ],
            "评分说明": "所有分数为 0-10，越高越适合目标读者继续阅读。",
            "严格 JSON Schema": {
                "overall_score": 0,
                "scores": {
                    "opening_hook": 0,
                    "protagonist_goal": 0,
                    "conflict_intensity": 0,
                    "payoff_speed": 0,
                    "readability": 0,
                    "reader_retention": 0,
                },
                "main_problems": [],
                "line_level_suggestions": [],
                "rewrite_strategy": "",
                "improved_opening_sample": "",
            },
        }
        return system, _json(user)
