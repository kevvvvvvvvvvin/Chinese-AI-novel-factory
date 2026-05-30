"""
AI小说工厂 v3.0 - 套路引擎
语义搜索 + 关键词搜索 + 分类浏览 + AI智能推荐。
"""
import os
from typing import Dict, List, Tuple, Optional
from config import cfg
from core.data_manager import load_text


class TropeEngine:
    """套路搜索与管理引擎"""
    
    def __init__(self, trope_index: Dict):
        self.index = trope_index
        self._semantic_model = None
        self._embeddings = None
        self._trope_names = []
        self._semantic_ready = False
    
    # ============================================================
    # 语义搜索（可选依赖）
    # ============================================================
    def init_semantic_search(self) -> bool:
        """初始化语义搜索模型"""
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            
            print("  [套路引擎] 正在加载语义搜索模型...")
            self._semantic_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
            
            # 构建向量索引
            texts = []
            names = []
            for name, data in self.index.items():
                if not data:
                    continue
                parts = [
                    name,
                    data.get('功能大类', ''),
                    ' '.join(data.get('功能标签', [])),
                    data.get('描述', '')
                ]
                texts.append(' '.join(filter(None, parts)))
                names.append(name)
            
            if texts:
                self._embeddings = self._semantic_model.encode(texts)
                self._trope_names = names
                self._semantic_ready = True
                print(f"  [套路引擎] 语义索引就绪: {len(names)} 个套路")
                return True
            return False
            
        except ImportError:
            print("  [套路引擎] 语义搜索不可用（安装 sentence-transformers 可启用）")
            return False
        except Exception as e:
            print(f"  [套路引擎] 语义模型加载失败: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 8) -> List[Tuple[str, float]]:
        """语义搜索套路"""
        if not self._semantic_ready:
            return self.keyword_search(query, top_k)
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            q_emb = self._semantic_model.encode([query])
            sims = cosine_similarity(q_emb, self._embeddings)[0]
            top_idx = np.argsort(sims)[::-1][:top_k]
            
            return [
                (self._trope_names[i], float(sims[i]))
                for i in top_idx
                if sims[i] > 0.15
            ]
        except Exception:
            return self.keyword_search(query, top_k)
    
    # ============================================================
    # 关键词搜索（零依赖备选）
    # ============================================================
    def keyword_search(self, query: str, top_k: int = 8) -> List[Tuple[str, float]]:
        """基于关键词的简单搜索"""
        results = []
        query_chars = set(query)
        
        for name, data in self.index.items():
            if not data:
                continue
            
            # 计算匹配分数
            score = 0.0
            search_text = name + ' ' + data.get('功能大类', '') + ' ' + \
                         ' '.join(data.get('功能标签', [])) + ' ' + data.get('描述', '')
            
            # 完全包含查询词
            if query in search_text:
                score += 1.0
            
            # 单字匹配
            text_chars = set(search_text)
            common = query_chars & text_chars
            if common:
                score += len(common) / len(query_chars) * 0.5
            
            # 名称直接匹配加分
            if query in name:
                score += 0.5
            
            if score > 0.1:
                results.append((name, score))
        
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    # ============================================================
    # 分类浏览
    # ============================================================
    def get_categories(self) -> Dict[str, List[str]]:
        """按功能大类分组"""
        cats = {}
        for name, data in self.index.items():
            if not data:
                continue
            cat = data.get('功能大类', '未分类')
            cats.setdefault(cat, []).append(name)
        return dict(sorted(cats.items()))
    
    def get_trope_detail(self, name: str) -> Optional[Dict]:
        """获取套路详情"""
        data = self.index.get(name)
        if not data:
            return None
        
        result = dict(data)
        result['name'] = name
        
        # 尝试加载模板B内容
        b_file = data.get('模板B文件名', '')
        if b_file:
            # 搜索多个可能的路径
            for search_dir in [cfg.TEMPLATES_B_DIR, cfg.BASE_DIR, os.path.join(cfg.BASE_DIR, 'data')]:
                path = os.path.join(search_dir, b_file)
                if os.path.exists(path):
                    result['模板B内容'] = load_text(path)
                    break
        
        return result
    
    def get_trope_template_b(self, name: str) -> Optional[str]:
        """获取套路的模板B文本内容"""
        detail = self.get_trope_detail(name)
        if detail:
            return detail.get('模板B内容')
        return None
    
    # ============================================================
    # 批量操作
    # ============================================================
    def get_tropes_for_goal(self, goal: str, count: int = 5) -> List[Dict]:
        """根据章节目标推荐套路（带详情）"""
        results = self.semantic_search(goal, top_k=count)
        detailed = []
        for name, score in results:
            detail = self.get_trope_detail(name)
            if detail:
                detail['match_score'] = score
                detailed.append(detail)
        return detailed
    
    def validate_trope_name(self, name: str) -> Optional[str]:
        """验证套路名称，支持模糊匹配"""
        # 精确匹配
        if name in self.index:
            return name
        
        # 模糊匹配
        candidates = []
        for key in self.index:
            if name in key or key in name:
                candidates.append(key)
        
        if len(candidates) == 1:
            return candidates[0]
        elif candidates:
            return candidates  # 返回列表让调用者选择
        
        return None
    
    @property
    def count(self) -> int:
        return len(self.index)
    
    @property
    def has_semantic(self) -> bool:
        return self._semantic_ready
