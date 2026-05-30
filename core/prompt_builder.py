"""
AI小说工厂 v3.0 - Prompt构建器
所有Prompt模板的统一管理中心。
模板与代码分离，支持热更新。
"""
import json
from typing import Dict, List, Optional, Any


def _sanitize(obj: Any) -> Any:
    """递归清理数据结构，确保JSON可序列化"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(e) for e in obj]
    if isinstance(obj, set):
        return [_sanitize(e) for e in obj]
    return obj


class PromptBuilder:
    """Prompt构建工厂"""
    
    # ============================================================
    # 规划阶段 Prompts
    # ============================================================
    
    @staticmethod
    def quest_fusion(world_settings: Dict, raw_quests: List[Dict]) -> tuple:
        """
        阶段1: 任务融合 - 将多条独立任务线融合为有机整体
        返回 (system_prompt, user_prompt)
        """
        system = """你是一位拥有上帝视角的"故事世界架构师"，精通多线程剧情设计。
你的任务是将碎片化的"原始创作意图"转化为一份结构化的"精炼任务日志"。

你必须做到：
1. 为每条任务线设计简洁的任务ID（如 MAIN_01_REVENGE）
2. 将目标具体化，明确起始条件、核心冲突和预期结果
3. 分解为可执行的阶段，每阶段有明确里程碑
4. 标注优先级和依赖关系
5. 【最重要】进行战略关联，确保多线程之间有机呼应——一条线的进展成为另一条线的前置条件

输出格式：严格输出纯JSON，无任何额外文字。"""

        user_data = {
            "世界观背景": world_settings,
            "原始任务意图": raw_quests,
            "输出格式": {
                "quests": [
                    {
                        "任务ID": "MAIN_01_XXX",
                        "任务名称": "名称",
                        "任务类型": "主线/支线/暗线",
                        "核心描述": "描述",
                        "状态": "进行中",
                        "阶段": [
                            {"id": 1, "status": "进行中", "desc": "阶段描述", "milestone": "里程碑"}
                        ],
                        "战略关联": "与其他任务的关联"
                    }
                ]
            }
        }
        
        return system, json.dumps(_sanitize(user_data), indent=2, ensure_ascii=False)
    
    @staticmethod
    def story_outline(world_settings: Dict, quest_log: Dict) -> tuple:
        """
        阶段2: 故事总纲 - 将任务日志转化为电影级故事梗概
        """
        system = """你是一位拥有奥斯卡水准的"电影故事梗概"撰写人。
你的任务是将结构化的任务日志，转化为一篇800-1500字的、充满激情和画面感的故事总纲。

必须包含：
- 开篇钩子：用极具冲突的场景抓住眼球
- 人物弧光：主角从状态A到状态B的蜕变
- 关键转折：幕与幕之间的转折点
- 高潮对决：最富冲击力的场景描绘
- 结尾余韵：清晰有力的结局

输出格式：直接输出Markdown格式的故事总纲。"""

        user = json.dumps(_sanitize({
            "世界观": world_settings,
            "任务日志": quest_log
        }), indent=2, ensure_ascii=False)
        
        return system, user
    
    @staticmethod
    def campaign_outline(story_outline: str, quest_log: Dict, focus: str) -> tuple:
        """
        阶段3: 战役细纲 - 为特定章节范围生成详细规划
        """
        system = """你是一位极其严谨的"首席剧情规划师"。
你必须严格按以下步骤工作：

【任务1：情节解构】将焦点部分解构为5-8个章节节点，规划每个节点的命名和关键步骤。
【任务2：爽点识别】审视所有步骤，为需要"戏剧冲突"的地方提出套路使用建议（描述功能而非具体名称）。
【任务3：整合输出】按指定格式整合输出。

输出格式：
# 战役细纲：【战役焦点】

### 章节 1: 【章节命名】
- **关键情节步骤**: 1. ... 2. ... 3. ...
- **套路建议**: (本章需要的叙事技巧)
- **产出与钩子**: (本章成果 + 为下章留的悬念)

### 章节 2: 【章节命名】
..."""

        user = json.dumps(_sanitize({
            "故事总纲": story_outline,
            "任务日志": quest_log,
            "本次战役焦点": focus
        }), indent=2, ensure_ascii=False)
        
        return system, user
    
    # ============================================================
    # 执行阶段 Prompts
    # ============================================================
    
    @staticmethod
    def chapter_outline(
        world_settings: Dict,
        story_outline: str,
        campaign_outline: str,
        quest_node: str,
        character_states: Dict,
        last_report: Dict,
        selected_tropes: List[Dict],
        trope_templates: Dict
    ) -> tuple:
        """
        章节大纲生成 - 将战役节点转化为分镜式大纲
        """
        system = """你是一位拥有二十年经验的顶级网文主编和剧情架构师。
你的任务是根据【本章核心剧本】，结合所有背景资料，生成一份详细的"分镜式"大纲。

【绝对规则】
1. 你必须100%遵循战役细纲中指定的任务节点
2. 套路模板仅作参考，不得照搬具体情节
3. 确保与上一章报告完美衔接

输出格式：
# 章节名称：（吸引人的名字）
# 场景：（地点和环境氛围）
# 核心目标：（一句话概括）
# 核心爽点：（最能调动读者情绪的关键点）
# 关键情节步骤：
1. [开场] ...
2. [冲突] ...
3. [导火索] ...
4. [爆发] ...
5. [高潮] ...
6. [收尾/钩子] ..."""

        user_data = {
            "世界设定": world_settings,
            "故事总纲（宏观参考）": story_outline[:2000] if story_outline else "无",
            "本章核心剧本": {
                "战役蓝图": campaign_outline,
                "本章聚焦节点": quest_node
            },
            "角色状态": character_states,
            "上章交接报告": last_report,
            "套路参考（仅参考精神，不照搬情节）": {
                name: tmpl[:500] for name, tmpl in trope_templates.items()
            } if trope_templates else "无"
        }
        
        return system, json.dumps(_sanitize(user_data), indent=2, ensure_ascii=False)
    
    @staticmethod
    def chapter_writing(
        world_settings: Dict,
        chapter_outline: str,
        character_states: Dict,
        last_report: Dict,
        trope_templates: Dict,
        style_directives: Dict = None
    ) -> tuple:
        """
        章节正文生成 - 将大纲转化为高质量正文
        """
        style_section = ""
        if style_directives:
            if style_directives.get('dominant_emotion'):
                style_section += f"\n本章主导情绪: {style_directives['dominant_emotion']}"
            if style_directives.get('visual_tone'):
                style_section += f"\n视觉基调: {style_directives['visual_tone']}"
            if style_directives.get('example_text'):
                style_section += f"\n参考文风范例:\n{style_directives['example_text'][:500]}"
        
        system = f"""你是一位顶级网络小说家，擅长将分镜式大纲转化为沉浸感极强的正文。

【三维场景扩写法】你必须运用此方法丰满每个场景：
维度一·感官：不只写"他走进酒馆"，要写他看到什么（昏暗烛火）、听到什么（粗野笑骂）、闻到什么（劣质酒味）。
维度二·思想：不只写"他很愤怒"，要写愤怒的层次——内心独白、回忆闪现、外在表现。
维度三·互动：不只写"他与反派对峙"，要写微表情、小动作、环境互动。

【风格指令】{style_section if style_section else "使用网文标准爽文风格。"}

【绝对规则】
1. 严格遵循大纲中的每一个情节步骤
2. 自然扩展到2000-3000字，杜绝注水
3. 每段都有存在价值
4. 结尾留悬念或转折"""

        user_data = {
            "世界设定": world_settings,
            "本章大纲（绝对剧本）": chapter_outline,
            "角色状态": character_states,
            "上章报告": last_report,
            "套路逻辑参考": {
                name: tmpl[:300] for name, tmpl in trope_templates.items()
            } if trope_templates else "无"
        }
        
        return system, json.dumps(_sanitize(user_data), indent=2, ensure_ascii=False)
    
    @staticmethod
    def handoff_report(chapter_num: int, chapter_text: str) -> tuple:
        """
        交接报告生成 - AI自动提取章节关键信息
        """
        system = """你是一位极其严谨的"首席情报分析官"。
你的任务是阅读一份刚完成的小说章节，撰写结构化的交接简报。

【绝对指令】严格按JSON格式输出，不要有任何额外文字：
{
    "source_chapter": 章节号,
    "ending_summary": "一句话结局总结",
    "final_character_states": {
        "角色名": "该角色的最终物理和心理状态"
    },
    "unresolved_hooks": ["悬念1", "悬念2"],
    "items_gained_or_lost": ["获得/失去的物品"],
    "power_level_changes": "实力变化描述"
}"""

        user = f"以下是第{chapter_num}章的完整正文，请分析并生成交接报告：\n\n{chapter_text}"
        
        return system, user
    
    @staticmethod
    def trope_recommendation(
        chapter_goal: str,
        trope_summaries: Dict,
        character_states: Dict
    ) -> tuple:
        """
        AI套路推荐 - 根据章节目标推荐最佳套路组合
        """
        system = """你是一位经验丰富的网文主编。
根据本章目标和可用套路库，推荐2-4个最适合的套路组合。

输出JSON格式：
{
    "reasoning": "推荐理由",
    "recommended": [
        {"name": "套路名", "role": "主导/辅助", "reason": "理由"}
    ]
}"""

        user_data = {
            "本章目标": chapter_goal,
            "角色状态": character_states,
            "可用套路": trope_summaries
        }
        
        return system, json.dumps(_sanitize(user_data), indent=2, ensure_ascii=False)
    
    @staticmethod
    def quality_review(chapter_text: str, world_settings: Dict, character_names: List[str]) -> tuple:
        """
        质量审查 - AI自动检查一致性和质量
        """
        system = """你是一位严苛的网文质量审查员。
请检查以下方面并输出JSON报告：

{
    "overall_score": 1-10分,
    "word_count": 字数,
    "issues": [
        {"type": "一致性/逻辑/节奏/文笔", "severity": "严重/中等/轻微", "description": "描述", "location": "大概位置"}
    ],
    "strengths": ["亮点1", "亮点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}"""

        user_data = {
            "待审查正文": chapter_text,
            "世界观设定（对照用）": world_settings,
            "已知角色名单": character_names
        }
        
        return system, json.dumps(_sanitize(user_data), indent=2, ensure_ascii=False)
