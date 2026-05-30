"""
AI小说工厂 v3.0 - 多项目管理器
每个项目拥有独立的世界观、套路库、角色、进度和数据库。
"""
import os
import json
import shutil
from typing import Dict, List, Optional
from datetime import datetime

from config import cfg
from core.data_manager import WorldData, ProjectDB, save_json, load_json, save_text, load_text


class ProjectManager:
    """
    多项目管理器。
    
    目录结构:
    projects/
      ├── my_novel_1/
      │   ├── project.json        # 项目元数据
      │   ├── data/
      │   │   ├── factory.db      # 独立数据库
      │   │   ├── my_world.json
      │   │   ├── concept_map.json
      │   │   ├── trope_index.json
      │   │   ├── templates_b/
      │   │   └── templates_c/
      │   ├── memory_bank/
      │   └── output/
      └── my_novel_2/
          └── ...
    """
    
    def __init__(self, projects_root: str = None):
        self.root = projects_root or os.path.join(cfg.BASE_DIR, "projects")
        os.makedirs(self.root, exist_ok=True)
        self._current_id: Optional[str] = None
        self._current_db: Optional[ProjectDB] = None
        self._current_world: Optional[WorldData] = None
    
    # ============================================================
    # 项目 CRUD
    # ============================================================
    
    def create_project(self, name: str, genre: str = "", description: str = "",
                       copy_from: str = None) -> Dict:
        """
        创建新项目。
        copy_from: 可选，从已有项目复制世界观和套路库。
        """
        project_id = self._name_to_id(name)
        project_dir = os.path.join(self.root, project_id)
        
        if os.path.exists(project_dir):
            raise ValueError(f"项目已存在: {project_id}")
        
        # 创建目录结构
        for sub in ["data/templates_b", "data/templates_c", "memory_bank", "output"]:
            os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
        
        # 项目元数据
        meta = {
            "id": project_id,
            "name": name,
            "genre": genre,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "chapter_count": 0,
            "total_words": 0
        }
        save_json(meta, os.path.join(project_dir, "project.json"))
        
        if copy_from:
            self._copy_assets(copy_from, project_id)
        else:
            # 创建空的默认文件
            save_json({
                "世界观名称": name,
                "核心力量体系": {"名称": "", "概念": "", "境界等级": []},
                "专有名词": {},
            }, os.path.join(project_dir, "data", "my_world.json"))
            
            save_json({}, os.path.join(project_dir, "data", "concept_map.json"))
            save_json({}, os.path.join(project_dir, "data", "trope_index.json"))
        
        # 从全局套路库复制（如果项目自己没有）
        global_trope = os.path.join(cfg.DATA_DIR, "trope_index.json")
        project_trope = os.path.join(project_dir, "data", "trope_index.json")
        if os.path.exists(global_trope) and os.path.getsize(project_trope) < 10:
            shutil.copy2(global_trope, project_trope)
        
        # 复制全局模板B
        global_b = os.path.join(cfg.DATA_DIR, "templates_b")
        project_b = os.path.join(project_dir, "data", "templates_b")
        if os.path.exists(global_b) and not os.listdir(project_b):
            for f in os.listdir(global_b):
                src = os.path.join(global_b, f)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(project_b, f))
        
        return meta
    
    def list_projects(self) -> List[Dict]:
        """列出所有项目"""
        projects = []
        if not os.path.exists(self.root):
            return projects
        
        for dirname in sorted(os.listdir(self.root)):
            meta_path = os.path.join(self.root, dirname, "project.json")
            if os.path.exists(meta_path):
                meta = load_json(meta_path) or {}
                meta["id"] = dirname
                
                # 实时统计
                db_path = os.path.join(self.root, dirname, "data", "factory.db")
                if os.path.exists(db_path):
                    try:
                        db = ProjectDB(db_path)
                        chapters = db.list_chapters()
                        meta["chapter_count"] = len(chapters)
                        meta["total_words"] = sum(c.get("word_count", 0) for c in chapters)
                        meta["completed_chapters"] = sum(1 for c in chapters if c["status"] == "completed")
                        db.close()
                    except:
                        pass
                
                projects.append(meta)
        
        return projects
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目详情"""
        meta_path = os.path.join(self.root, project_id, "project.json")
        if not os.path.exists(meta_path):
            return None
        return load_json(meta_path)
    
    def update_project(self, project_id: str, **kwargs) -> bool:
        """更新项目元数据"""
        meta_path = os.path.join(self.root, project_id, "project.json")
        meta = load_json(meta_path)
        if not meta:
            return False
        meta.update(kwargs)
        meta["updated_at"] = datetime.now().isoformat()
        save_json(meta, meta_path)
        return True
    
    def delete_project(self, project_id: str) -> bool:
        """删除项目（危险操作）"""
        project_dir = os.path.join(self.root, project_id)
        if not os.path.exists(project_dir):
            return False
        shutil.rmtree(project_dir)
        if self._current_id == project_id:
            self._current_id = None
            self._current_db = None
            self._current_world = None
        return True
    
    # ============================================================
    # 项目切换
    # ============================================================
    
    def switch_to(self, project_id: str) -> bool:
        """切换到指定项目，加载其数据"""
        project_dir = os.path.join(self.root, project_id)
        if not os.path.exists(os.path.join(project_dir, "project.json")):
            return False
        
        # 关闭旧连接
        if self._current_db:
            self._current_db.close()
        
        self._current_id = project_id
        
        # 加载项目数据库
        db_path = os.path.join(project_dir, "data", "factory.db")
        self._current_db = ProjectDB(db_path)
        
        # 加载世界数据
        self._current_world = WorldData()
        
        # 临时修改cfg路径指向项目目录
        data_dir = os.path.join(project_dir, "data")
        self._current_world.world_settings = load_json(os.path.join(data_dir, "my_world.json")) or {}
        self._current_world.concept_map = load_json(os.path.join(data_dir, "concept_map.json")) or {}
        self._current_world.trope_index = load_json(os.path.join(data_dir, "trope_index.json")) or {}
        
        # 加载故事总纲
        for fn in os.listdir(project_dir):
            if fn.endswith(('.txt', '.md')) and 'outline' in fn.lower():
                content = load_text(os.path.join(project_dir, fn))
                if content:
                    self._current_world.story_outline = content
                    break
        
        # 加载战役细纲
        for search_dir in [os.path.join(project_dir, "output"), project_dir]:
            if os.path.exists(search_dir):
                for fn in os.listdir(search_dir):
                    if 'campaign' in fn.lower() and fn.endswith(('.md', '.txt')):
                        content = load_text(os.path.join(search_dir, fn))
                        if content:
                            self._current_world.campaign_outlines[fn] = content
        
        self._current_world._loaded = True
        return True
    
    @property
    def current_id(self) -> Optional[str]:
        return self._current_id
    
    @property
    def current_db(self) -> Optional[ProjectDB]:
        return self._current_db
    
    @property
    def current_world(self) -> Optional[WorldData]:
        return self._current_world
    
    def get_project_dir(self, project_id: str = None) -> str:
        pid = project_id or self._current_id
        return os.path.join(self.root, pid) if pid else self.root
    
    def get_output_dir(self, project_id: str = None) -> str:
        return os.path.join(self.get_project_dir(project_id), "output")
    
    def get_memory_dir(self, project_id: str = None) -> str:
        return os.path.join(self.get_project_dir(project_id), "memory_bank")
    
    # ============================================================
    # 内部方法
    # ============================================================
    
    def _name_to_id(self, name: str) -> str:
        """将项目名转为安全的目录名"""
        import re
        safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', name).strip('_')
        return safe[:50] or f"project_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _copy_assets(self, source_id: str, target_id: str):
        """从源项目复制资产到目标项目"""
        src_dir = os.path.join(self.root, source_id, "data")
        dst_dir = os.path.join(self.root, target_id, "data")
        
        if not os.path.exists(src_dir):
            return
        
        for fn in ["my_world.json", "concept_map.json", "trope_index.json"]:
            src = os.path.join(src_dir, fn)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst_dir, fn))
        
        # 复制模板
        for subdir in ["templates_b", "templates_c"]:
            src_sub = os.path.join(src_dir, subdir)
            dst_sub = os.path.join(dst_dir, subdir)
            if os.path.exists(src_sub):
                for f in os.listdir(src_sub):
                    shutil.copy2(os.path.join(src_sub, f), os.path.join(dst_sub, f))
    
    def close(self):
        if self._current_db:
            self._current_db.close()
