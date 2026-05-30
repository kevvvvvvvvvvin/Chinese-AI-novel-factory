"""
AI小说工厂 v3.0 - 自动驾驶模块 (AutoPilot)
实现零人工干预的全自动章节生产。

核心能力：
1. 从战役细纲中自动提取章节节点
2. 根据节点目标自动选择套路组合
3. 章间自动传递角色状态
4. 失败自动重试 + 降级
5. 全程成本追踪
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import cfg
from core.data_manager import WorldData, ProjectDB, save_text, save_json, load_text, load_json
from core.trope_engine import TropeEngine
from core.prompt_builder import PromptBuilder
from core.llm_gateway import LLMGateway
from core.pipeline import Pipeline


class AutoPilot:
    """
    全自动驾驶系统。
    
    用法：
        pilot = AutoPilot(world, db, tropes, llm)
        pilot.produce_range(1, 50, campaign_file="campaign_001_050.md")
    """
    
    def __init__(self, world: WorldData, db: ProjectDB,
                 tropes: TropeEngine, llm: LLMGateway):
        self.world = world
        self.db = db
        self.tropes = tropes
        self.llm = llm
        self.pipeline = Pipeline(world, db, tropes, llm)
        self.pb = PromptBuilder()
        
        # 运行时状态
        self.character_states: Dict = {}
        self.production_log: List[Dict] = []
    
    # ============================================================
    # 核心：从战役细纲中自动提取章节节点
    # ============================================================
    
    def extract_chapter_nodes(self, campaign_text: str) -> List[Dict]:
        """
        从战役细纲的Markdown文本中，自动提取每个章节的节点信息。
        
        支持两种格式：
        1. AI自动提取（在线模式）
        2. 正则解析（离线模式/备选）
        """
        # 优先尝试AI提取（更准确）
        if self.llm.is_online:
            nodes = self._ai_extract_nodes(campaign_text)
            if nodes:
                return nodes
        
        # 降级为正则解析
        return self._regex_extract_nodes(campaign_text)
    
    def _ai_extract_nodes(self, campaign_text: str) -> Optional[List[Dict]]:
        """用AI从细纲中提取结构化的章节节点"""
        system = """你是一个精确的文本解析器。从战役细纲中提取每个章节的结构化信息。

输出严格JSON格式，不要任何额外文字：
[
    {
        "chapter_title": "章节标题",
        "core_goal": "本章核心目标（一句话）",
        "key_events": ["关键事件1", "关键事件2"],
        "trope_hints": ["需要的叙事技巧关键词"],
        "hook": "本章结尾悬念"
    }
]"""
        
        response = self.llm.generate(
            system, f"请解析以下战役细纲：\n\n{campaign_text}",
            max_tokens=3000, temperature=0.2,
            step_name="auto_extract_nodes",
            expect_json=True
        )
        
        if response:
            data = self.llm.parse_json_response(response)
            if isinstance(data, list) and len(data) > 0:
                print(f"  [AutoPilot] AI提取到 {len(data)} 个章节节点")
                return data
        
        return None
    
    def _regex_extract_nodes(self, campaign_text: str) -> List[Dict]:
        """用正则从细纲Markdown中提取章节节点（零依赖备选）"""
        nodes = []
        
        # 匹配 ### 章节 N: 标题 或 ### **章节 N: 标题**
        pattern = r'###\s*\*{0,2}章节\s*\d+[：:]\s*(.+?)\*{0,2}\s*$'
        sections = re.split(pattern, campaign_text, flags=re.MULTILINE)
        
        # 如果标准格式没有匹配到，尝试更宽泛的模式
        if len(sections) <= 1:
            pattern = r'###\s*(.+?)$'
            sections = re.split(pattern, campaign_text, flags=re.MULTILINE)
        
        # sections[0] 是开头, 之后 [1]=标题1, [2]=内容1, [3]=标题2, [4]=内容2...
        for i in range(1, len(sections) - 1, 2):
            title = sections[i].strip().strip('*').strip()
            content = sections[i + 1] if i + 1 < len(sections) else ""
            
            # 从内容中提取关键信息
            events = []
            trope_hints = []
            hook = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '-')):
                    clean = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
                    if clean:
                        events.append(clean[:80])
                
                if '套路' in line or '建议' in line:
                    trope_hints.append(re.sub(r'^.*?[：:]', '', line).strip()[:60])
                
                if '钩子' in line or '悬念' in line or '产出' in line:
                    hook = re.sub(r'^.*?[：:]', '', line).strip()[:100]
            
            # 核心目标 = 第一个关键事件或标题本身
            core_goal = events[0] if events else title
            
            nodes.append({
                "chapter_title": title,
                "core_goal": core_goal,
                "key_events": events[:5],
                "trope_hints": trope_hints,
                "hook": hook
            })
        
        print(f"  [AutoPilot] 正则提取到 {len(nodes)} 个章节节点")
        return nodes
    
    # ============================================================
    # 核心：根据章节目标自动选择套路
    # ============================================================
    
    def auto_select_tropes(self, node: Dict, max_tropes: int = 3) -> List[str]:
        """
        根据章节节点信息，自动选择最匹配的套路组合。
        
        策略：
        1. 用章节目标做语义搜索
        2. 用套路提示做二次搜索
        3. 去重合并，取Top N
        """
        candidates = {}  # name -> best_score
        
        # 搜索1：基于核心目标
        goal = node.get("core_goal", "")
        if goal:
            results = self.tropes.semantic_search(goal, top_k=5)
            for name, score in results:
                candidates[name] = max(candidates.get(name, 0), score)
        
        # 搜索2：基于关键事件
        for event in node.get("key_events", [])[:3]:
            results = self.tropes.semantic_search(event, top_k=3)
            for name, score in results:
                candidates[name] = max(candidates.get(name, 0), score * 0.8)
        
        # 搜索3：基于套路提示词
        for hint in node.get("trope_hints", []):
            results = self.tropes.semantic_search(hint, top_k=3)
            for name, score in results:
                candidates[name] = max(candidates.get(name, 0), score * 0.9)
        
        # 按分数排序取Top N
        sorted_tropes = sorted(candidates.items(), key=lambda x: -x[1])
        selected = [name for name, _ in sorted_tropes[:max_tropes]]
        
        if selected:
            print(f"  [AutoPilot] 自动选择套路: {selected}")
        
        return selected
    
    # ============================================================
    # 核心：全自动批量生产
    # ============================================================
    
    def produce_range(
        self,
        start_chapter: int,
        end_chapter: int,
        campaign_file: str = None,
        campaign_text: str = None,
        initial_characters: Dict = None,
        style: Dict = None,
        token_budget: int = 0,
        stop_on_fail: bool = False
    ) -> Dict:
        """
        全自动生产指定范围的章节。零人工干预。
        
        Args:
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            campaign_file: 战役细纲文件名（在output/或根目录中搜索）
            campaign_text: 或直接传入细纲文本
            initial_characters: 初始角色状态
            style: 全局风格设定
            token_budget: Token预算上限（0=不限）
            stop_on_fail: 是否遇到失败就停止
        
        Returns:
            生产报告 Dict
        """
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"  🚀 AutoPilot 启动 — 第{start_chapter}~{end_chapter}章")
        print(f"{'='*60}")
        
        # 设置Token预算
        if token_budget > 0:
            self.llm.set_budget(token_budget)
            print(f"  Token预算: {token_budget:,}")
        
        # 加载战役细纲
        campaign = campaign_text
        if not campaign and campaign_file:
            for search_dir in [cfg.OUTPUT_DIR, cfg.BASE_DIR]:
                path = os.path.join(search_dir, campaign_file)
                if os.path.exists(path):
                    campaign = load_text(path)
                    break
        
        if not campaign:
            # 尝试自动发现
            for d in [cfg.OUTPUT_DIR, cfg.BASE_DIR]:
                for fn in os.listdir(d):
                    if 'campaign' in fn.lower() and fn.endswith(('.md', '.txt')):
                        campaign = load_text(os.path.join(d, fn))
                        if campaign:
                            print(f"  自动发现战役细纲: {fn}")
                            break
                if campaign:
                    break
        
        if not campaign:
            print("  ❌ 未找到战役细纲，无法启动")
            return {"success": False, "error": "no_campaign"}
        
        # 提取章节节点
        print("\n  📋 解析战役细纲...")
        nodes = self.extract_chapter_nodes(campaign)
        
        if not nodes:
            print("  ❌ 无法从细纲中提取章节节点")
            return {"success": False, "error": "no_nodes"}
        
        total_chapters = end_chapter - start_chapter + 1
        available_nodes = len(nodes)
        print(f"  提取到 {available_nodes} 个节点，需生产 {total_chapters} 章")
        
        if available_nodes < total_chapters:
            print(f"  ⚠️ 节点不足，将只生产 {available_nodes} 章")
            end_chapter = start_chapter + available_nodes - 1
        
        # 初始化角色状态
        self.character_states = initial_characters or {}
        self.production_log = []
        
        # ========== 主生产循环 ==========
        success_count = 0
        fail_count = 0
        total_words = 0
        
        for i, ch_num in enumerate(range(start_chapter, end_chapter + 1)):
            node = nodes[i]
            
            print(f"\n{'─'*60}")
            print(f"  📖 第{ch_num}章 [{i+1}/{end_chapter-start_chapter+1}]")
            print(f"     目标: {node.get('core_goal', '未知')}")
            print(f"{'─'*60}")
            
            # 检查Token预算
            if self.llm.budget_exhausted:
                print(f"  ⚠️ Token预算耗尽，停止生产")
                break
            
            # 自动选择套路
            selected_tropes = self.auto_select_tropes(node)
            
            # 构建本章的quest_node描述
            quest_node = self._build_quest_description(node)
            
            # 调用流水线生产
            try:
                result = self.pipeline.produce_chapter(
                    chapter_num=ch_num,
                    quest_node=quest_node,
                    campaign_content=campaign,
                    selected_tropes=selected_tropes,
                    character_states=self.character_states,
                    style=style,
                    auto_review=True
                )
                
                if result.get("success"):
                    success_count += 1
                    words = result.get("word_count", 0)
                    total_words += words
                    
                    # 自动更新角色状态
                    if result.get("report"):
                        states = result["report"].get("final_character_states", {})
                        if states:
                            self.character_states.update(states)
                    
                    self.production_log.append({
                        "chapter": ch_num,
                        "status": "success",
                        "words": words,
                        "tropes": selected_tropes,
                        "node": node.get("chapter_title", "")
                    })
                else:
                    fail_count += 1
                    self.production_log.append({
                        "chapter": ch_num,
                        "status": "partial",
                        "steps": result.get("steps", []),
                        "node": node.get("chapter_title", "")
                    })
                    
                    if stop_on_fail:
                        print(f"  ⛔ stop_on_fail=True，停止生产")
                        break
                        
            except Exception as e:
                fail_count += 1
                print(f"  ❌ 第{ch_num}章异常: {e}")
                self.production_log.append({
                    "chapter": ch_num, "status": "error", "error": str(e)
                })
                if stop_on_fail:
                    break
        
        # ========== 生产报告 ==========
        elapsed = (datetime.now() - start_time).total_seconds()
        stats = self.llm.get_stats()
        
        report = {
            "success": True,
            "range": f"{start_chapter}-{end_chapter}",
            "chapters_completed": success_count,
            "chapters_failed": fail_count,
            "total_words": total_words,
            "elapsed_seconds": round(elapsed, 1),
            "words_per_minute": round(total_words / max(1, elapsed / 60)),
            "llm_stats": stats,
            "production_log": self.production_log
        }
        
        # 保存报告
        report_path = os.path.join(cfg.OUTPUT_DIR, 
                                    f"production_report_{start_chapter}-{end_chapter}.json")
        save_json(report, report_path)
        
        # 打印汇总
        print(f"\n{'='*60}")
        print(f"  🏁 AutoPilot 生产完成")
        print(f"{'='*60}")
        print(f"  成功: {success_count}章 | 失败: {fail_count}章")
        print(f"  总字数: {total_words:,}")
        print(f"  耗时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)")
        print(f"  速度: {report['words_per_minute']:,}字/分钟")
        print(f"  API调用: {stats['calls']}次 | Token: {stats['total_tokens']:,}")
        print(f"  费用: ${stats['cost_usd']:.4f}")
        print(f"  报告: {os.path.basename(report_path)}")
        print(f"{'='*60}")
        
        return report
    
    def _build_quest_description(self, node: Dict) -> str:
        """将节点信息组装为quest_node描述文本"""
        parts = [f"【{node.get('chapter_title', '')}】"]
        
        goal = node.get('core_goal', '')
        if goal:
            parts.append(f"核心目标: {goal}")
        
        events = node.get('key_events', [])
        if events:
            parts.append("关键事件: " + "; ".join(events[:4]))
        
        hook = node.get('hook', '')
        if hook:
            parts.append(f"结尾悬念: {hook}")
        
        return "\n".join(parts)
    
    # ============================================================
    # 便捷方法
    # ============================================================
    
    def produce_all(self, **kwargs) -> Dict:
        """
        自动发现战役细纲并生产所有章节。
        最简调用方式。
        """
        # 自动发现campaign文件
        for d in [cfg.OUTPUT_DIR, cfg.BASE_DIR]:
            if not os.path.exists(d):
                continue
            for fn in sorted(os.listdir(d)):
                if 'campaign' in fn.lower() and fn.endswith(('.md', '.txt')):
                    campaign = load_text(os.path.join(d, fn))
                    if campaign:
                        nodes = self.extract_chapter_nodes(campaign)
                        if nodes:
                            print(f"  发现 {fn} ({len(nodes)}章)")
                            return self.produce_range(
                                1, len(nodes),
                                campaign_text=campaign,
                                **kwargs
                            )
        
        print("  ❌ 未找到任何战役细纲")
        return {"success": False}
    
    def resume(self, **kwargs) -> Dict:
        """
        从上次中断的位置继续生产。
        """
        last_ch = self.db.get_latest_chapter_num()
        start = last_ch + 1 if last_ch > 0 else 1
        
        # 读取上一章的角色状态
        if last_ch > 0:
            ch_data = self.db.get_chapter(last_ch)
            if ch_data and ch_data.get("report_json"):
                try:
                    report = json.loads(ch_data["report_json"])
                    self.character_states = report.get("final_character_states", {})
                except:
                    pass
        
        print(f"  📍 从第{start}章恢复生产")
        return self.produce_all(start_chapter=start, **kwargs)
