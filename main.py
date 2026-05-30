#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   🏭 AI小说工厂 v3.0 - 商业化重构版              ║
║   一站式网文自动化生产系统                        ║
╚══════════════════════════════════════════════════╝

使用方式:
  python main.py                    # 交互式CLI
  python main.py --auto 1-10        # 自动生产第1-10章
  python main.py --plan             # 进入规划模式
  python main.py --status           # 查看项目状态
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import cfg, FactoryConfig
from core.data_manager import WorldData, ProjectDB, save_text, load_text, save_json, load_json
from core.trope_engine import TropeEngine
from core.prompt_builder import PromptBuilder
from core.llm_gateway import LLMGateway
from core.pipeline import Pipeline
from core.autopilot import AutoPilot


# ============================================================
# 美化输出工具
# ============================================================
def banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🏭  AI 小 说 工 厂  v3.0                                  ║
║   ─────────────────────────────                              ║
║   套路驱动 · AI赋能 · 工业化生产                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝""")

def header(title: str):
    w = 60
    print(f"\n{'─'*w}")
    print(f"  {title}")
    print(f"{'─'*w}")

def menu(title: str, options: Dict[str, str]):
    header(title)
    for key, desc in options.items():
        print(f"  [{key}] {desc}")


# ============================================================
# 工厂主控制器
# ============================================================
class NovelFactory:
    """AI小说工厂主控制器"""
    
    def __init__(self):
        self.world = WorldData()
        self.db: Optional[ProjectDB] = None
        self.tropes: Optional[TropeEngine] = None
        self.llm = LLMGateway()
        self.pipeline: Optional[Pipeline] = None
        self.autopilot: Optional[AutoPilot] = None
        
        # 运行时状态
        self.current_chapter = 1
        self.selected_tropes: List[str] = []
        self.character_states: Dict = {}
    
    def initialize(self) -> bool:
        """初始化整个系统"""
        header("系统初始化")
        cfg.ensure_dirs()
        
        # 加载世界数据
        if not self.world.load_all():
            print("\n  ⚠️ 部分数据未加载，功能可能受限")
        
        # 初始化数据库
        self.db = ProjectDB()
        last_ch = self.db.get_latest_chapter_num()
        if last_ch > 0:
            self.current_chapter = last_ch + 1
            print(f"  [DB] 检测到已有进度，当前从第{self.current_chapter}章开始")
        
        # 初始化套路引擎
        self.tropes = TropeEngine(self.world.trope_index)
        self.tropes.init_semantic_search()  # 可选
        
        # 初始化LLM网关
        self.llm.initialize()
        
        # 构建流水线
        self.pipeline = Pipeline(self.world, self.db, self.tropes, self.llm)
        self.autopilot = AutoPilot(self.world, self.db, self.tropes, self.llm)
        
        print(f"\n  ✅ 初始化完成")
        print(f"     套路库: {self.tropes.count} 个")
        print(f"     LLM模式: {self.llm.mode}")
        print(f"     当前章节: 第{self.current_chapter}章")
        
        return True
    
    # ============================================================
    # 主菜单
    # ============================================================
    def run(self):
        """主循环"""
        banner()
        
        if not self.initialize():
            print("\n❌ 初始化失败")
            return
        
        while True:
            menu("🏭 主控制台", {
                "P": "📋 规划模式 - 生成任务日志、总纲、战役细纲",
                "E": "✍️  执行模式 - 章节大纲、正文、交接报告",
                "A": "🚀 全自动模式 - AutoPilot零干预批量生产",
                "T": "🔍 套路工坊 - 搜索、浏览、管理套路",
                "S": "📊 项目状态 - 查看进度和统计",
                "I": "📥 导入结果 - 手动导入AI响应（离线模式用）",
                "Q": "🚪 退出"
            })
            
            choice = input("\n  请选择 > ").strip().upper()
            
            if choice == 'P':
                self.planning_mode()
            elif choice == 'E':
                self.execution_mode()
            elif choice == 'A':
                self.autopilot_mode()
            elif choice == 'T':
                self.trope_workshop()
            elif choice == 'S':
                self.show_status()
            elif choice == 'I':
                self.import_results()
            elif choice == 'Q':
                self._shutdown()
                break
            else:
                print("  无效输入")
    
    # ============================================================
    # 规划模式
    # ============================================================
    def planning_mode(self):
        """规划模式 - 生成战略级资产"""
        while True:
            menu("📋 规划模式", {
                "1": "一键规划 - 任务融合 → 总纲 → 细纲（全自动）",
                "2": "仅生成任务日志",
                "3": "仅生成故事总纲",
                "4": "生成战役细纲",
                "0": "返回主菜单"
            })
            
            choice = input("\n  请选择 > ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._full_planning()
            elif choice == '2':
                self._plan_quest_log()
            elif choice == '3':
                self._plan_story_outline()
            elif choice == '4':
                self._plan_campaign()
    
    def _full_planning(self):
        """一键完整规划"""
        header("一键规划流程")
        raw_quests = self._collect_raw_quests()
        if not raw_quests:
            return
        
        results = self.pipeline.run_planning(raw_quests)
        
        if "story_outline" in results.get("steps_completed", []):
            if input("\n  是否继续生成战役细纲? (y/n): ").lower() == 'y':
                focus = input("  请输入战役焦点 (如: 第一幕/前50章): ").strip()
                if focus:
                    self.pipeline.generate_campaign(focus)
    
    def _collect_raw_quests(self) -> List[Dict]:
        """收集原始任务意图"""
        # 扫描模板C文件
        c_dir = cfg.TEMPLATES_C_DIR
        templates = []
        
        for search_dir in [c_dir, cfg.BASE_DIR, os.path.join(cfg.BASE_DIR, 'data')]:
            if os.path.exists(search_dir):
                for f in os.listdir(search_dir):
                    if f.endswith('.json') and not f.startswith(('project_', 'trope_', 'concept_')):
                        data = load_json(os.path.join(search_dir, f))
                        if data and ('任务链' in data or '阶段' in str(data)):
                            templates.append((f, data))
        
        if not templates:
            print("  ⚠️ 未找到任务线模板（templates_c/*.json）")
            # 允许手动输入
            quests = []
            print("  请手动输入任务线（输入空行结束）:")
            while True:
                quest_type = input("    任务类型 (主线/支线/暗线，空行结束): ").strip()
                if not quest_type:
                    break
                goal = input("    核心目标: ").strip()
                if goal:
                    quests.append({"quest_type_hint": quest_type, "core_goal": goal})
            return quests
        
        print(f"\n  检测到 {len(templates)} 个任务线模板:")
        for i, (fn, _) in enumerate(templates):
            name = fn.replace('.json', '')
            print(f"    [{i+1}] {name}")
        print(f"    [0] 完成选择")
        
        selected = []
        while True:
            choice = input(f"\n    添加任务线 (已选{len(selected)}个, 0结束): ").strip()
            if choice == '0':
                break
            if choice.isdigit() and 0 < int(choice) <= len(templates):
                idx = int(choice) - 1
                fn, data = templates[idx]
                
                type_map = {"1": "主线", "2": "支线", "3": "暗线"}
                t = input("      类型 (1:主线 2:支线 3:暗线): ").strip()
                quest_type = type_map.get(t, "其他")
                goal = input("      核心目标: ").strip()
                
                selected.append({
                    "quest_type_hint": quest_type,
                    "core_goal": goal,
                    "template_c_content": data
                })
                print(f"      ✅ 已添加: {fn.replace('.json','')}")
        
        return selected
    
    def _plan_quest_log(self):
        """单独生成任务日志"""
        raw_quests = self._collect_raw_quests()
        if raw_quests:
            sys_p, user_p = PromptBuilder.quest_fusion(self.world.world_settings, raw_quests)
            resp = self.llm.generate(sys_p, user_p, step_name="quest_fusion")
            if resp:
                save_text(resp, os.path.join(cfg.OUTPUT_DIR, "quest_log.json"))
                print("  ✅ 任务日志已生成")
    
    def _plan_story_outline(self):
        """单独生成故事总纲"""
        quest_log = load_json(os.path.join(cfg.OUTPUT_DIR, "quest_log.json"))
        if not quest_log:
            print("  ⚠️ 请先生成任务日志")
            return
        sys_p, user_p = PromptBuilder.story_outline(self.world.world_settings, quest_log)
        resp = self.llm.generate(sys_p, user_p, step_name="story_outline")
        if resp:
            save_text(resp, os.path.join(cfg.OUTPUT_DIR, "story_outline.md"))
            print("  ✅ 故事总纲已生成")
    
    def _plan_campaign(self):
        """生成战役细纲"""
        focus = input("  请输入战役焦点: ").strip()
        if focus:
            self.pipeline.generate_campaign(focus)
    
    # ============================================================
    # AutoPilot 全自动模式
    # ============================================================
    def autopilot_mode(self):
        """全自动模式 - 零干预批量生产"""
        header("🚀 AutoPilot 全自动模式")
        
        if not self.llm.is_online:
            print("  ⚠️ AutoPilot需要API Key才能运行")
            print("  请设置环境变量 ANTHROPIC_API_KEY 或在 .env 文件中配置")
            input("\n  按回车返回...")
            return
        
        menu("AutoPilot 操作", {
            "1": "🚀 全自动生产（自动发现细纲 → 全量生产）",
            "2": "📍 从中断处恢复生产",
            "3": "🎯 指定范围生产",
            "4": "💰 设置Token预算",
            "0": "返回"
        })
        
        choice = input("\n  请选择 > ").strip()
        
        if choice == '1':
            print("\n  即将启动全自动生产模式...")
            print("  系统将自动: 解析细纲 → 提取节点 → 选择套路 → 生成内容 → 质量审查 → 归档")
            confirm = input("\n  确认启动? (yes/no): ").strip().lower()
            if confirm == 'yes':
                budget = input("  Token预算 (直接回车=不限): ").strip()
                budget = int(budget) if budget.isdigit() else 0
                self.autopilot.produce_all(token_budget=budget)
            else:
                print("  已取消")
        
        elif choice == '2':
            print(f"\n  当前进度: 已完成到第{self.db.get_latest_chapter_num()}章")
            self.autopilot.resume()
        
        elif choice == '3':
            start = int(input("  起始章节: ").strip() or "1")
            end = int(input("  结束章节: ").strip() or "10")
            budget = input("  Token预算 (直接回车=不限): ").strip()
            budget = int(budget) if budget.isdigit() else 0
            
            self.autopilot.produce_range(
                start, end, token_budget=budget
            )
        
        elif choice == '4':
            budget = int(input("  设置Token预算上限: ").strip() or "500000")
            self.llm.set_budget(budget)
            print(f"  ✅ Token预算已设为: {budget:,}")

    # ============================================================
    # 执行模式
    # ============================================================
    def execution_mode(self):
        """执行模式 - 日常章节生产"""
        while True:
            # 显示当前状态
            print(f"\n  📌 当前: 第{self.current_chapter}章 | "
                  f"已选套路: {self.selected_tropes or '无'}")
            
            menu("✍️  执行模式", {
                "1": f"⚡ 一键生产第{self.current_chapter}章（全自动）",
                "2": "🎯 配置本章参数",
                "3": "🔍 选择套路",
                "4": "📝 单独生成大纲",
                "5": "📖 单独生成正文",
                "6": "📋 生成交接报告",
                "7": "🔄 批量生产多章",
                "8": "🔄 恢复中断的章节",
                "9": "📦 导出小说合集",
                "0": "返回主菜单"
            })
            
            choice = input("\n  请选择 > ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._one_click_produce()
            elif choice == '2':
                self._configure_chapter()
            elif choice == '3':
                self._select_tropes()
            elif choice == '4':
                self._generate_outline_only()
            elif choice == '5':
                self._generate_writing_only()
            elif choice == '6':
                self._generate_report_only()
            elif choice == '7':
                self._batch_produce()
            elif choice == '8':
                self._resume_chapter()
            elif choice == '9':
                self._export_novel()
    
    def _one_click_produce(self):
        """一键生产当前章节"""
        # 选择战役细纲
        campaign = self._pick_campaign_content()
        if not campaign:
            return
        
        quest_node = input("  请输入本章聚焦的任务节点: ").strip()
        if not quest_node:
            print("  ⚠️ 必须指定任务节点")
            return
        
        # 收集风格（可选）
        style = {}
        emotion = input("  本章主导情绪 (可选, 直接回车跳过): ").strip()
        if emotion:
            style['dominant_emotion'] = emotion
        
        result = self.pipeline.produce_chapter(
            chapter_num=self.current_chapter,
            quest_node=quest_node,
            campaign_content=campaign,
            selected_tropes=self.selected_tropes,
            character_states=self.character_states,
            style=style if style else None
        )
        
        if result.get("success"):
            self.current_chapter += 1
            self.selected_tropes = []  # 重置
            
            # 更新角色状态
            if result.get("report"):
                states = result["report"].get("final_character_states", {})
                self.character_states.update(states)
    
    def _configure_chapter(self):
        """配置章节参数"""
        header("配置本章参数")
        
        num = input(f"  章节号 (默认{self.current_chapter}): ").strip()
        if num.isdigit():
            self.current_chapter = int(num)
        
        name = input("  主角姓名: ").strip()
        level = input("  当前境界: ").strip()
        
        if name:
            self.character_states = {
                "主角": {"姓名": name, "境界": level}
            }
        
        print(f"  ✅ 已配置: 第{self.current_chapter}章")
    
    def _select_tropes(self):
        """选择套路"""
        header("套路选择")
        print("  输入搜索词查找套路，输入 'done' 完成选择")
        
        while True:
            query = input(f"\n  搜索 (已选{len(self.selected_tropes)}个, 'done'结束): ").strip()
            if query.lower() == 'done':
                break
            if not query:
                continue
            
            results = self.tropes.semantic_search(query, top_k=6)
            if not results:
                print("  未找到相关套路")
                continue
            
            for i, (name, score) in enumerate(results):
                marker = " ✓" if name in self.selected_tropes else ""
                print(f"    [{i+1}] {name} ({score:.2f}){marker}")
            
            sel = input("  选择编号添加 (空格分隔多选): ").strip().split()
            for s in sel:
                if s.isdigit() and 0 < int(s) <= len(results):
                    name = results[int(s)-1][0]
                    if name not in self.selected_tropes:
                        self.selected_tropes.append(name)
                        print(f"    ✅ 已添加: {name}")
        
        print(f"\n  当前套路组合: {self.selected_tropes}")
    
    def _pick_campaign_content(self) -> Optional[str]:
        """选择战役细纲内容"""
        # 先搜索output目录
        campaigns = {}
        for d in [cfg.OUTPUT_DIR, cfg.BASE_DIR]:
            if os.path.exists(d):
                for fn in os.listdir(d):
                    if ('campaign' in fn.lower() or '战役' in fn) and fn.endswith(('.md', '.txt')):
                        content = load_text(os.path.join(d, fn))
                        if content:
                            campaigns[fn] = content
        
        # 也检查world data中已加载的
        campaigns.update(self.world.campaign_outlines)
        
        if not campaigns:
            print("  ⚠️ 未找到战役细纲，请先在规划模式中生成")
            # 允许手动输入
            manual = input("  或手动输入本章剧情要求: ").strip()
            return manual if manual else None
        
        if len(campaigns) == 1:
            fn, content = list(campaigns.items())[0]
            print(f"  自动选择: {fn}")
            return content
        
        print("  可用的战役细纲:")
        items = list(campaigns.items())
        for i, (fn, _) in enumerate(items):
            print(f"    [{i+1}] {fn}")
        
        choice = input("  请选择: ").strip()
        if choice.isdigit() and 0 < int(choice) <= len(items):
            return items[int(choice)-1][1]
        
        return None
    
    def _generate_outline_only(self):
        """单独生成大纲"""
        campaign = self._pick_campaign_content()
        if not campaign:
            return
        node = input("  任务节点: ").strip()
        if not node:
            return
        
        last_report = self.pipeline._get_last_report(self.current_chapter)
        trope_templates = {}
        for name in self.selected_tropes:
            tmpl = self.tropes.get_trope_template_b(name)
            if tmpl:
                trope_templates[name] = tmpl
        
        sys_p, user_p = PromptBuilder.chapter_outline(
            self.world.world_settings, self.world.story_outline,
            campaign, node, self.character_states, last_report,
            [{"name": n} for n in self.selected_tropes], trope_templates
        )
        
        resp = self.llm.generate(sys_p, user_p, 
                                max_tokens=cfg.MAX_TOKENS_OUTLINE,
                                step_name=f"ch{self.current_chapter:03d}_outline")
        if resp:
            save_text(resp, os.path.join(cfg.OUTPUT_DIR, f"chapter_{self.current_chapter:03d}_outline.txt"))
            self.db.save_chapter(self.current_chapter, outline=resp, status='outline_done')
            print("  ✅ 大纲已生成")
    
    def _generate_writing_only(self):
        """单独生成正文"""
        ch_data = self.db.get_chapter(self.current_chapter)
        if not ch_data or not ch_data.get("outline"):
            outline_path = os.path.join(cfg.OUTPUT_DIR, f"chapter_{self.current_chapter:03d}_outline.txt")
            outline = load_text(outline_path)
            if not outline:
                print("  ⚠️ 请先生成本章大纲")
                return
        else:
            outline = ch_data["outline"]
        
        last_report = self.pipeline._get_last_report(self.current_chapter)
        trope_templates = {}
        for name in self.selected_tropes:
            tmpl = self.tropes.get_trope_template_b(name)
            if tmpl:
                trope_templates[name] = tmpl
        
        sys_p, user_p = PromptBuilder.chapter_writing(
            self.world.world_settings, outline, self.character_states,
            last_report, trope_templates
        )
        
        resp = self.llm.generate(sys_p, user_p,
                                max_tokens=cfg.MAX_TOKENS_WRITING,
                                temperature=cfg.TEMPERATURE_WRITING,
                                step_name=f"ch{self.current_chapter:03d}_writing")
        if resp:
            save_text(resp, os.path.join(cfg.OUTPUT_DIR, f"chapter_{self.current_chapter:03d}.txt"))
            self.db.save_chapter(self.current_chapter, content=resp, 
                               word_count=len(resp), status='written')
            print(f"  ✅ 正文已生成 ({len(resp)}字)")
    
    def _generate_report_only(self):
        """单独生成交接报告"""
        ch_data = self.db.get_chapter(self.current_chapter)
        content = None
        if ch_data and ch_data.get("content"):
            content = ch_data["content"]
        else:
            content_path = os.path.join(cfg.OUTPUT_DIR, f"chapter_{self.current_chapter:03d}.txt")
            content = load_text(content_path)
        
        if not content:
            print("  ⚠️ 请先生成本章正文")
            return
        
        sys_p, user_p = PromptBuilder.handoff_report(self.current_chapter, content)
        resp = self.llm.generate(sys_p, user_p,
                                max_tokens=cfg.MAX_TOKENS_REPORT,
                                step_name=f"ch{self.current_chapter:03d}_report")
        if resp:
            report = self.llm.parse_json_response(resp)
            if report:
                save_json(report, os.path.join(cfg.MEMORY_BANK_DIR, 
                         f"chapter_{self.current_chapter:03d}_report.json"))
                self.db.save_chapter(self.current_chapter, 
                                    report_json=json.dumps(report, ensure_ascii=False),
                                    status='completed')
                print("  ✅ 交接报告已生成")
            else:
                save_text(resp, os.path.join(cfg.OUTPUT_DIR, 
                         f"chapter_{self.current_chapter:03d}_report_raw.txt"))
                print("  ⚠️ JSON解析失败，原始文本已保存")
    
    def _batch_produce(self):
        """批量生产"""
        header("批量生产")
        start = int(input("  起始章节: ").strip() or self.current_chapter)
        end = int(input("  结束章节: ").strip() or start + 4)
        
        campaign = self._pick_campaign_content()
        if not campaign:
            return
        
        print(f"  请为第{start}-{end}章逐一输入任务节点 (每行一个):")
        nodes = []
        for i in range(start, end + 1):
            node = input(f"    第{i}章节点: ").strip()
            if node:
                nodes.append(node)
            else:
                break
        
        if nodes:
            self.pipeline.batch_produce(
                start, start + len(nodes) - 1,
                campaign, nodes,
                character_states=self.character_states
            )
            self.current_chapter = start + len(nodes)
    
    def _resume_chapter(self):
        """恢复中断的章节"""
        header("恢复中断的章节")
        ch_num = int(input(f"  要恢复的章节号 (默认{self.current_chapter}): ").strip() 
                      or self.current_chapter)
        
        campaign = self._pick_campaign_content()
        node = input("  任务节点: ").strip() if campaign else ""
        
        self.pipeline.resume_chapter(
            ch_num,
            quest_node=node or "恢复",
            campaign_content=campaign or "",
            selected_tropes=self.selected_tropes,
            character_states=self.character_states
        )
    
    def _export_novel(self):
        """导出小说合集"""
        header("📦 导出小说合集")
        chapters = self.db.list_chapters()
        completed = [c for c in chapters if c.get('content')]
        
        if not completed:
            print("  ⚠️ 暂无已完成的章节")
            return
        
        print(f"  已完成章节: {len(completed)}章")
        fmt = input("  导出格式 (1:txt 2:md, 默认1): ").strip()
        fmt = "md" if fmt == "2" else "txt"
        
        filepath = self.pipeline.export_novel(format=fmt)
        if filepath:
            print(f"  📁 文件位置: {filepath}")
    
    # ============================================================
    # 套路工坊
    # ============================================================
    def trope_workshop(self):
        """套路浏览和搜索"""
        while True:
            menu("🔍 套路工坊", {
                "1": f"语义搜索 {'(向量)' if self.tropes.has_semantic else '(关键词)'}",
                "2": "分类浏览",
                "3": "查看详情",
                "4": "AI推荐套路",
                "0": "返回"
            })
            
            choice = input("\n  请选择 > ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                query = input("  描述你想要的效果: ").strip()
                if query:
                    results = self.tropes.semantic_search(query)
                    for i, (name, score) in enumerate(results):
                        print(f"    [{i+1}] {name} ({score:.2f})")
            elif choice == '2':
                cats = self.tropes.get_categories()
                for i, (cat, items) in enumerate(cats.items()):
                    print(f"    [{i+1}] {cat} ({len(items)}个)")
                
                c = input("  选择分类: ").strip()
                if c.isdigit() and 0 < int(c) <= len(cats):
                    cat_name = list(cats.keys())[int(c)-1]
                    for j, name in enumerate(cats[cat_name]):
                        print(f"      [{j+1}] {name}")
            elif choice == '3':
                name = input("  套路名称: ").strip()
                detail = self.tropes.get_trope_detail(name)
                if detail:
                    for k, v in detail.items():
                        if k != '模板B内容':
                            print(f"    {k}: {v}")
                else:
                    print("  未找到")
            elif choice == '4':
                if not self.character_states:
                    print("  ⚠️ 请先在执行模式中配置角色")
                    continue
                goal = input("  本章目标: ").strip()
                if goal:
                    # 构建摘要供AI参考
                    summaries = {}
                    for name, data in list(self.world.trope_index.items())[:50]:
                        summaries[name] = data.get('功能大类', '') + ': ' + data.get('描述', '')[:50]
                    
                    sys_p, user_p = PromptBuilder.trope_recommendation(
                        goal, summaries, self.character_states
                    )
                    resp = self.llm.generate(sys_p, user_p, max_tokens=1500,
                                           step_name="trope_recommend")
                    if resp:
                        print(f"\n  AI推荐:\n  {resp[:1000]}")
    
    # ============================================================
    # 状态与导入
    # ============================================================
    def show_status(self):
        """显示项目状态"""
        header("📊 项目状态")
        
        project_name = self.world.project_config.get("current_project_name", "未命名")
        print(f"  项目: {project_name}")
        print(f"  LLM: {self.llm.mode} | 累计Token: {self.llm.total_tokens}")
        print(f"  套路库: {self.tropes.count}个 | 语义搜索: {'✅' if self.tropes.has_semantic else '❌'}")
        print(f"  战役细纲: {len(self.world.campaign_outlines)}份")
        
        chapters = self.db.list_chapters()
        if chapters:
            completed = sum(1 for c in chapters if c['status'] == 'completed')
            total_words = sum(c.get('word_count', 0) for c in chapters)
            print(f"\n  章节进度: {completed}/{len(chapters)} 完成")
            print(f"  总字数: {total_words}")
            
            print(f"\n  最近章节:")
            for ch in chapters[-5:]:
                status_icon = {'planned': '📋', 'outline_done': '📝', 
                              'written': '✍️', 'completed': '✅'}.get(ch['status'], '❓')
                print(f"    第{ch['chapter_num']}章 {status_icon} {ch['status']} "
                      f"({ch.get('word_count', 0)}字)")
        else:
            print(f"\n  尚未开始创作")
        
        quests = self.db.list_quests()
        if quests:
            print(f"\n  任务线: {len(quests)}条")
            for q in quests[:5]:
                print(f"    {q['quest_id']}: {q.get('quest_name', '')} [{q.get('status', '')}]")
        
        input("\n  按回车继续...")
    
    def import_results(self):
        """导入手动执行的结果"""
        header("📥 导入AI响应")
        print("  用于离线模式: 将AI返回的结果导入系统\n")
        
        ch_num = int(input("  章节号: ").strip() or self.current_chapter)
        
        step_map = {"1": "outline", "2": "content", "3": "report"}
        print("  导入类型: [1]大纲 [2]正文 [3]交接报告")
        step_choice = input("  选择: ").strip()
        step = step_map.get(step_choice)
        
        if not step:
            return
        
        filepath = input("  文件路径: ").strip()
        if filepath and os.path.exists(filepath):
            self.pipeline.import_manual_result(ch_num, step, filepath)
        else:
            print("  文件不存在")
    
    def _shutdown(self):
        """关闭清理"""
        if self.db:
            self.db.close()
        print("\n  👋 感谢使用AI小说工厂！")


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='AI小说工厂 v3.0')
    parser.add_argument('--plan', action='store_true', help='直接进入规划模式')
    parser.add_argument('--status', action='store_true', help='显示项目状态')
    parser.add_argument('--auto', type=str, help='自动生产章节范围 (如: 1-10)')
    parser.add_argument('--dir', type=str, help='指定项目目录')
    
    args = parser.parse_args()
    
    if args.dir:
        cfg.BASE_DIR = args.dir
    
    try:
        factory = NovelFactory()
        
        if args.status:
            factory.initialize()
            factory.show_status()
        elif args.plan:
            factory.initialize()
            factory.planning_mode()
        elif args.auto:
            factory.initialize()
            if not factory.llm.is_online:
                print("❌ 自动模式需要API Key")
                print("   设置: export ANTHROPIC_API_KEY=<your_anthropic_api_key>")
                return
            
            # 解析章节范围
            parts = args.auto.replace('~', '-').replace('—', '-').split('-')
            start = int(parts[0].strip())
            end = int(parts[1].strip()) if len(parts) > 1 else start
            
            print(f"\n🚀 AutoPilot: 自动生产第{start}-{end}章")
            factory.autopilot.produce_range(start, end)
        else:
            factory.run()
            
    except KeyboardInterrupt:
        print("\n\n  👋 再见！")
    except Exception as e:
        print(f"\n❌ 运行异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
