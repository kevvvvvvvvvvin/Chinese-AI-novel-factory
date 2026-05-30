"""
AI小说工厂 v3.0 - 流水线编排器
自动化整个创作流程：规划 → 大纲 → 正文 → 审查 → 归档
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

from config import cfg
from core.data_manager import WorldData, ProjectDB, save_text, load_text, save_json, load_json
from core.trope_engine import TropeEngine
from core.prompt_builder import PromptBuilder
from core.llm_gateway import LLMGateway


class Pipeline:
    """
    小说生产流水线。
    
    支持两种运行模式：
    - 全自动：有API Key时，一键完成整个章节
    - 半自动：无API Key时，逐步导出Prompt并等待用户手动回填
    """
    
    def __init__(self, world: WorldData, db: ProjectDB, 
                 trope_engine: TropeEngine, llm: LLMGateway):
        self.world = world
        self.db = db
        self.tropes = trope_engine
        self.llm = llm
        self.pb = PromptBuilder()
    
    # ============================================================
    # 规划阶段流水线
    # ============================================================
    
    def run_planning(self, raw_quests: List[Dict]) -> Dict:
        """
        运行完整的规划流水线。
        raw_quests: 原始任务意图列表
        
        流程: 任务融合 → 故事总纲 → 战役细纲
        """
        results = {"steps_completed": []}
        
        # Step 1: 任务融合
        print("\n📋 [规划 1/3] 任务融合...")
        sys_prompt, user_prompt = self.pb.quest_fusion(
            self.world.world_settings, raw_quests
        )
        
        response = self.llm.generate(
            sys_prompt, user_prompt,
            max_tokens=cfg.MAX_TOKENS_OUTLINE,
            temperature=0.7,
            step_name="1_quest_fusion"
        )
        
        if response:
            quest_log = self.llm.parse_json_response(response)
            if quest_log:
                save_json(quest_log, os.path.join(cfg.OUTPUT_DIR, "quest_log.json"))
                results["quest_log"] = quest_log
                results["steps_completed"].append("quest_fusion")
                
                # 存入数据库
                for quest in quest_log.get("quests", []):
                    self.db.save_quest(
                        quest.get("任务ID", "UNKNOWN"),
                        quest_type=quest.get("任务类型", ""),
                        quest_name=quest.get("任务名称", ""),
                        description=quest.get("核心描述", ""),
                        status=quest.get("状态", "待办"),
                        phases_json=json.dumps(quest.get("阶段", []), ensure_ascii=False)
                    )
                print("  ✅ 任务日志已生成并存入数据库")
            else:
                save_text(response, os.path.join(cfg.OUTPUT_DIR, "quest_log_raw.txt"))
                print("  ⚠️ JSON解析失败，原始响应已保存")
        else:
            print("  📄 离线Prompt已导出，请手动执行")
        
        # Step 2: 故事总纲
        quest_log_data = results.get("quest_log") or \
                         load_json(os.path.join(cfg.OUTPUT_DIR, "quest_log.json"))
        
        if quest_log_data:
            print("\n📋 [规划 2/3] 故事总纲...")
            sys_prompt, user_prompt = self.pb.story_outline(
                self.world.world_settings, quest_log_data
            )
            
            response = self.llm.generate(
                sys_prompt, user_prompt,
                max_tokens=cfg.MAX_TOKENS_OUTLINE,
                temperature=0.8,
                step_name="2_story_outline"
            )
            
            if response:
                save_text(response, os.path.join(cfg.OUTPUT_DIR, "story_outline.md"))
                results["story_outline"] = response
                results["steps_completed"].append("story_outline")
                self.db.set_meta("story_outline", response[:5000])
                print("  ✅ 故事总纲已生成")
        
        return results
    
    def generate_campaign(self, focus: str) -> Optional[str]:
        """生成战役细纲"""
        quest_log = load_json(os.path.join(cfg.OUTPUT_DIR, "quest_log.json")) or {}
        outline = self.world.story_outline or self.db.get_meta("story_outline")
        
        if not outline:
            outline_path = os.path.join(cfg.OUTPUT_DIR, "story_outline.md")
            outline = load_text(outline_path) or ""
        
        print(f"\n📋 生成战役细纲: {focus}")
        sys_prompt, user_prompt = self.pb.campaign_outline(outline, quest_log, focus)
        
        response = self.llm.generate(
            sys_prompt, user_prompt,
            max_tokens=cfg.MAX_TOKENS_OUTLINE,
            temperature=0.7,
            step_name=f"3_campaign_{focus[:10]}"
        )
        
        if response:
            safe_name = ''.join(c for c in focus if c.isalnum() or c in '_-')[:30]
            filepath = os.path.join(cfg.OUTPUT_DIR, f"campaign_{safe_name}.md")
            save_text(response, filepath)
            print(f"  ✅ 战役细纲已保存: {os.path.basename(filepath)}")
            return response
        
        return None
    
    # ============================================================
    # 章节生产流水线
    # ============================================================
    
    def produce_chapter(
        self,
        chapter_num: int,
        quest_node: str,
        campaign_content: str,
        selected_tropes: List[str] = None,
        character_states: Dict = None,
        style: Dict = None,
        auto_review: bool = True
    ) -> Dict:
        """
        一键生产一章完整内容。
        
        流程: 选套路 → 生成大纲 → 生成正文 → 质量审查 → 生成交接报告 → 归档
        """
        results = {
            "chapter_num": chapter_num,
            "steps": [],
            "success": False
        }
        
        # 准备数据
        char_states = character_states or {}
        last_report = self._get_last_report(chapter_num)
        trope_templates = {}
        
        if selected_tropes:
            for name in selected_tropes:
                tmpl = self.tropes.get_trope_template_b(name)
                if tmpl:
                    trope_templates[name] = tmpl
        
        # --- Step 1: 生成大纲 ---
        print(f"\n✍️  [第{chapter_num}章 1/4] 生成章节大纲...")
        sys_prompt, user_prompt = self.pb.chapter_outline(
            world_settings=self.world.world_settings,
            story_outline=self.world.story_outline,
            campaign_outline=campaign_content,
            quest_node=quest_node,
            character_states=char_states,
            last_report=last_report,
            selected_tropes=[{"name": n} for n in (selected_tropes or [])],
            trope_templates=trope_templates
        )
        
        outline = self.llm.generate(
            sys_prompt, user_prompt,
            max_tokens=cfg.MAX_TOKENS_OUTLINE,
            temperature=cfg.TEMPERATURE_OUTLINE,
            step_name=f"ch{chapter_num:03d}_outline"
        )
        
        if outline:
            outline_path = os.path.join(cfg.OUTPUT_DIR, f"chapter_{chapter_num:03d}_outline.txt")
            save_text(outline, outline_path)
            self.db.save_chapter(chapter_num, outline=outline, status='outline_done',
                               core_goal=quest_node,
                               tropes_used=json.dumps(selected_tropes or [], ensure_ascii=False))
            results["outline"] = outline
            results["steps"].append("outline")
            print("  ✅ 大纲已生成")
        else:
            print("  📄 大纲Prompt已导出")
            results["steps"].append("outline_exported")
            return results
        
        # --- Step 2: 生成正文 ---
        print(f"\n✍️  [第{chapter_num}章 2/4] 生成正文...")
        sys_prompt, user_prompt = self.pb.chapter_writing(
            world_settings=self.world.world_settings,
            chapter_outline=outline,
            character_states=char_states,
            last_report=last_report,
            trope_templates=trope_templates,
            style_directives=style
        )
        
        content = self.llm.generate(
            sys_prompt, user_prompt,
            max_tokens=cfg.MAX_TOKENS_WRITING,
            temperature=cfg.TEMPERATURE_WRITING,
            step_name=f"ch{chapter_num:03d}_writing",
            min_length=cfg.MIN_CHAPTER_WORDS  # 低于最小字数自动重试
        )
        
        if content:
            content_path = os.path.join(cfg.OUTPUT_DIR, f"chapter_{chapter_num:03d}.txt")
            save_text(content, content_path)
            word_count = len(content)
            self.db.save_chapter(chapter_num, content=content, word_count=word_count, 
                               status='written')
            results["content"] = content
            results["word_count"] = word_count
            results["steps"].append("writing")
            print(f"  ✅ 正文已生成 ({word_count}字)")
        else:
            print("  📄 正文Prompt已导出")
            results["steps"].append("writing_exported")
            return results
        
        # --- Step 3: 质量审查 + 自动重写 ---
        if auto_review and content:
            print(f"\n🔍 [第{chapter_num}章 3/4] 质量审查...")
            char_names = [c.get("name", "") for c in self.db.list_characters()] or ["主角"]
            
            rewrite_attempts = 0
            max_rewrites = 2  # 最多重写2次
            
            while rewrite_attempts <= max_rewrites:
                sys_prompt, user_prompt = self.pb.quality_review(
                    content, self.world.world_settings, char_names
                )
                
                review = self.llm.generate(
                    sys_prompt, user_prompt,
                    max_tokens=cfg.MAX_TOKENS_REPORT,
                    temperature=0.3,
                    step_name=f"ch{chapter_num:03d}_review",
                    expect_json=True
                )
                
                if not review:
                    break
                    
                review_data = self.llm.parse_json_response(review)
                if not review_data:
                    break
                
                score = review_data.get("overall_score", 10)
                issues = review_data.get("issues", [])
                severe = [i for i in issues if i.get("severity") == "严重"]
                
                save_json(review_data, os.path.join(
                    cfg.OUTPUT_DIR, f"chapter_{chapter_num:03d}_review.json"))
                print(f"  审查评分: {score}/10, 问题: {len(issues)}个 (严重: {len(severe)})")
                
                # 评分>=6且无严重问题则通过
                if (isinstance(score, (int, float)) and score >= 6) or not severe:
                    results["review"] = review_data
                    results["steps"].append("review")
                    print(f"  ✅ 质量通过")
                    break
                
                # 评分不足，自动重写
                rewrite_attempts += 1
                if rewrite_attempts > max_rewrites:
                    print(f"  ⚠️ 达到最大重写次数，保留当前版本")
                    results["review"] = review_data
                    results["steps"].append("review")
                    break
                
                print(f"  🔄 评分偏低，启动自动重写 (第{rewrite_attempts}次)...")
                
                # 构建重写Prompt（附带问题反馈）
                rewrite_system = """你是一位网文精修编辑。请根据审查反馈修改正文。
保留原文的情节和结构，只修复指出的问题。输出完整修改后的正文。"""
                
                rewrite_user = json.dumps({
                    "原始正文": content,
                    "审查反馈": {
                        "评分": score,
                        "严重问题": [{"类型": i.get("type"), "描述": i.get("description")} 
                                   for i in severe],
                        "改进建议": review_data.get("suggestions", [])
                    },
                    "指令": "请修复严重问题并改进，输出完整修改后的正文"
                }, indent=2, ensure_ascii=False)
                
                rewritten = self.llm.generate(
                    rewrite_system, rewrite_user,
                    max_tokens=cfg.MAX_TOKENS_WRITING,
                    temperature=0.75,
                    step_name=f"ch{chapter_num:03d}_rewrite_{rewrite_attempts}",
                    min_length=cfg.MIN_CHAPTER_WORDS
                )
                
                if rewritten and len(rewritten) >= len(content) * 0.7:
                    content = rewritten
                    word_count = len(content)
                    save_text(content, os.path.join(cfg.OUTPUT_DIR, f"chapter_{chapter_num:03d}.txt"))
                    self.db.save_chapter(chapter_num, content=content, word_count=word_count)
                    results["content"] = content
                    results["word_count"] = word_count
                    print(f"  重写完成 ({word_count}字)，重新审查...")
                else:
                    print(f"  重写失败，保留原始版本")
                    break
        
        # --- Step 4: 交接报告 ---
        if content:
            print(f"\n📝 [第{chapter_num}章 4/4] 生成交接报告...")
            sys_prompt, user_prompt = self.pb.handoff_report(chapter_num, content)
            
            report_response = self.llm.generate(
                sys_prompt, user_prompt,
                max_tokens=cfg.MAX_TOKENS_REPORT,
                temperature=0.3,
                step_name=f"ch{chapter_num:03d}_report",
                expect_json=True  # JSON格式验证，解析失败自动重试
            )
            
            if report_response:
                report = self.llm.parse_json_response(report_response)
                if report:
                    report_path = os.path.join(cfg.MEMORY_BANK_DIR, f"chapter_{chapter_num:03d}_report.json")
                    save_json(report, report_path)
                    self.db.save_chapter(chapter_num, report_json=json.dumps(report, ensure_ascii=False),
                                        status='completed')
                    results["report"] = report
                    results["steps"].append("report")
                    print("  ✅ 交接报告已生成并归档")
                    
                    # 【自动更新角色状态到数据库】
                    char_states_new = report.get("final_character_states", {})
                    for char_name, state_desc in char_states_new.items():
                        self.db.save_character(char_name, {}, str(state_desc))
                    if char_states_new:
                        print(f"  ✅ 已自动更新{len(char_states_new)}个角色状态")
        
        results["success"] = "writing" in results["steps"]
        
        # 汇总
        if results["success"]:
            print(f"\n{'='*60}")
            print(f"🎉 第{chapter_num}章生产完成！")
            print(f"   大纲: ✅  正文: ✅ ({results.get('word_count',0)}字)  "
                  f"审查: {'✅' if 'review' in results['steps'] else '⏭️'}  "
                  f"报告: {'✅' if 'report' in results['steps'] else '⏭️'}")
            print(f"   LLM累计Token: {self.llm.total_tokens}")
            print(f"{'='*60}")
        
        return results
    
    # ============================================================
    # 批量生产
    # ============================================================
    
    def batch_produce(
        self,
        start_chapter: int,
        end_chapter: int,
        campaign_content: str,
        quest_nodes: List[str],
        tropes_per_chapter: Dict[int, List[str]] = None,
        character_states: Dict = None,
        style: Dict = None
    ) -> List[Dict]:
        """
        批量生产多个章节。
        """
        results = []
        tropes_map = tropes_per_chapter or {}
        
        for i, ch_num in enumerate(range(start_chapter, end_chapter + 1)):
            if i >= len(quest_nodes):
                print(f"  ⚠️ 任务节点不足，跳过第{ch_num}章")
                break
            
            print(f"\n{'='*60}")
            print(f"📖 开始生产第 {ch_num} 章 ({i+1}/{end_chapter-start_chapter+1})")
            print(f"{'='*60}")
            
            chapter_result = self.produce_chapter(
                chapter_num=ch_num,
                quest_node=quest_nodes[i],
                campaign_content=campaign_content,
                selected_tropes=tropes_map.get(ch_num, []),
                character_states=character_states,
                style=style
            )
            
            results.append(chapter_result)
            
            # 如果上一章失败，询问是否继续
            if not chapter_result.get("success") and self.llm.is_online:
                if input("\n上一章生产未完成，是否继续？(y/n): ").lower() != 'y':
                    break
            
            # 更新角色状态（如果有交接报告）
            if chapter_result.get("report"):
                char_states = chapter_result["report"].get("final_character_states", {})
                if char_states:
                    character_states = character_states or {}
                    character_states.update(char_states)
        
        # 汇总报告
        completed = sum(1 for r in results if r.get("success"))
        total_words = sum(r.get("word_count", 0) for r in results)
        print(f"\n{'='*60}")
        print(f"📊 批量生产完成: {completed}/{len(results)} 章成功")
        print(f"   总字数: {total_words}")
        print(f"   总Token: {self.llm.total_tokens}")
        print(f"{'='*60}")
        
        return results
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _get_last_report(self, chapter_num: int) -> Dict:
        """获取上一章的交接报告"""
        if chapter_num <= 1:
            return {"comment": "第一章，无上章报告"}
        
        # 先从数据库查
        prev = self.db.get_chapter(chapter_num - 1)
        if prev and prev.get("report_json"):
            try:
                return json.loads(prev["report_json"])
            except:
                pass
        
        # 从文件查
        report_path = os.path.join(cfg.MEMORY_BANK_DIR, f"chapter_{chapter_num-1:03d}_report.json")
        return load_json(report_path) or {"comment": f"第{chapter_num-1}章报告未找到"}
    
    def import_manual_result(self, chapter_num: int, step: str, filepath: str) -> bool:
        """
        导入手动执行的结果（用于离线模式）。
        step: "outline" | "content" | "report"
        """
        content = load_text(filepath)
        if not content:
            print(f"  [!] 无法读取文件: {filepath}")
            return False
        
        if step == "outline":
            self.db.save_chapter(chapter_num, outline=content, status='outline_done')
            print(f"  ✅ 第{chapter_num}章大纲已导入")
        elif step == "content":
            self.db.save_chapter(chapter_num, content=content, 
                               word_count=len(content), status='written')
            print(f"  ✅ 第{chapter_num}章正文已导入 ({len(content)}字)")
        elif step == "report":
            report = load_json(filepath)
            if report:
                self.db.save_chapter(chapter_num, 
                                    report_json=json.dumps(report, ensure_ascii=False),
                                    status='completed')
                # 自动更新角色状态
                for name, state in report.get("final_character_states", {}).items():
                    self.db.save_character(name, {}, str(state))
                print(f"  ✅ 第{chapter_num}章报告已导入")
            else:
                self.db.save_chapter(chapter_num, report_json=content, status='completed')
        
        return True
    
    # ============================================================
    # 导出合集
    # ============================================================
    
    def export_novel(self, start: int = 1, end: int = None, 
                     format: str = "txt") -> Optional[str]:
        """
        将已完成的章节导出为完整小说文件。
        支持格式: txt, md
        """
        chapters = self.db.list_chapters()
        completed = [c for c in chapters if c.get("content") and c["chapter_num"] >= start]
        if end:
            completed = [c for c in completed if c["chapter_num"] <= end]
        
        if not completed:
            print("  ⚠️ 没有已完成的章节可导出")
            return None
        
        completed.sort(key=lambda c: c["chapter_num"])
        
        # 构建合集
        parts = []
        total_words = 0
        
        project_name = self.world.project_config.get("current_project_name", "我的小说")
        
        if format == "md":
            parts.append(f"# {project_name}\n\n---\n")
        else:
            parts.append(f"{project_name}\n{'='*40}\n\n")
        
        for ch in completed:
            num = ch["chapter_num"]
            title = ch.get("title", f"第{num}章")
            content = ch["content"]
            wc = len(content)
            total_words += wc
            
            if format == "md":
                parts.append(f"\n## 第{num}章 {title}\n\n{content}\n\n---\n")
            else:
                parts.append(f"\n第{num}章 {title}\n{'-'*30}\n\n{content}\n\n")
        
        # 添加统计
        stats = f"\n[全书统计: {len(completed)}章, {total_words}字]\n"
        parts.append(stats)
        
        full_text = "\n".join(parts)
        
        ext = "md" if format == "md" else "txt"
        filename = f"{project_name}_第{completed[0]['chapter_num']}-{completed[-1]['chapter_num']}章.{ext}"
        filepath = os.path.join(cfg.OUTPUT_DIR, filename)
        save_text(full_text, filepath)
        
        print(f"  ✅ 导出完成: {filename}")
        print(f"     共{len(completed)}章, {total_words}字")
        return filepath
    
    # ============================================================
    # 崩溃恢复
    # ============================================================
    
    def resume_chapter(self, chapter_num: int, **kwargs) -> Dict:
        """
        从上次中断的位置恢复章节生产。
        自动检测已完成的步骤，从下一步继续。
        """
        ch = self.db.get_chapter(chapter_num)
        if not ch:
            print(f"  数据库中无第{chapter_num}章记录，从头开始")
            return self.produce_chapter(chapter_num, **kwargs)
        
        status = ch.get("status", "")
        print(f"  第{chapter_num}章当前状态: {status}")
        
        if status == "completed":
            print(f"  ✅ 已完成，无需恢复")
            return {"chapter_num": chapter_num, "success": True, "steps": ["already_completed"]}
        
        # 根据状态决定从哪步恢复
        if status == "written" and ch.get("content"):
            # 正文已有，只缺报告
            print(f"  🔄 从交接报告步骤恢复...")
            content = ch["content"]
            
            sys_prompt, user_prompt = self.pb.handoff_report(chapter_num, content)
            report_response = self.llm.generate(
                sys_prompt, user_prompt,
                max_tokens=cfg.MAX_TOKENS_REPORT,
                temperature=0.3,
                step_name=f"ch{chapter_num:03d}_report",
                expect_json=True
            )
            if report_response:
                report = self.llm.parse_json_response(report_response)
                if report:
                    save_json(report, os.path.join(cfg.MEMORY_BANK_DIR, f"chapter_{chapter_num:03d}_report.json"))
                    self.db.save_chapter(chapter_num, report_json=json.dumps(report, ensure_ascii=False), status='completed')
                    for name, state in report.get("final_character_states", {}).items():
                        self.db.save_character(name, {}, str(state))
                    print(f"  ✅ 恢复完成")
                    return {"chapter_num": chapter_num, "success": True, "steps": ["report_recovered"]}
        
        elif status == "outline_done" and ch.get("outline"):
            # 大纲已有，从正文开始
            print(f"  🔄 从正文生成步骤恢复...")
            # 需要调用者提供完整参数
            return self.produce_chapter(chapter_num, **kwargs)
        
        # 其他情况从头开始
        print(f"  🔄 状态不明，从头开始...")
        return self.produce_chapter(chapter_num, **kwargs)
