"""
AI小说工厂 v3.0 - 数据层
SQLite持久化 + 统一的文件I/O管理。
"""
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import cfg


# ============================================================
# 文件I/O 工具
# ============================================================
def load_json(filepath: str) -> Optional[Dict]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"  [!] JSON解析错误 {os.path.basename(filepath)}: {e}")
        return None

def save_json(data: Any, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_text(filepath: str) -> Optional[str]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_text(text: str, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)


# ============================================================
# SQLite 数据库 - 项目状态持久化
# ============================================================
class ProjectDB:
    """项目数据库 - 管理章节进度、角色状态、任务追踪"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or cfg.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS project_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS chapters (
                chapter_num INTEGER PRIMARY KEY,
                title TEXT,
                status TEXT DEFAULT 'planned',
                core_goal TEXT,
                tropes_used TEXT,
                outline TEXT,
                content TEXT,
                word_count INTEGER DEFAULT 0,
                report_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS characters (
                name TEXT PRIMARY KEY,
                profile_json TEXT,
                last_state TEXT,
                appearances TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS quest_log (
                quest_id TEXT PRIMARY KEY,
                quest_type TEXT,
                quest_name TEXT,
                act TEXT,
                description TEXT,
                status TEXT DEFAULT '待办',
                phases_json TEXT,
                dependencies TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS generation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_num INTEGER,
                step TEXT,
                prompt_hash TEXT,
                response_preview TEXT,
                tokens_used INTEGER,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    # --- 项目元数据 ---
    def get_meta(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM project_meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    
    def set_meta(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO project_meta (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now())
        )
        self.conn.commit()
    
    # --- 章节管理 ---
    def get_chapter(self, num: int) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM chapters WHERE chapter_num=?", (num,)).fetchone()
        return dict(row) if row else None
    
    def save_chapter(self, num: int, **kwargs):
        existing = self.get_chapter(num)
        if existing:
            sets = ", ".join(f"{k}=?" for k in kwargs)
            vals = list(kwargs.values()) + [datetime.now(), num]
            self.conn.execute(f"UPDATE chapters SET {sets}, updated_at=? WHERE chapter_num=?", vals)
        else:
            kwargs['chapter_num'] = num
            cols = ", ".join(kwargs.keys())
            placeholders = ", ".join("?" * len(kwargs))
            self.conn.execute(f"INSERT INTO chapters ({cols}) VALUES ({placeholders})", list(kwargs.values()))
        self.conn.commit()
    
    def get_latest_chapter_num(self) -> int:
        row = self.conn.execute("SELECT MAX(chapter_num) as n FROM chapters").fetchone()
        return row["n"] or 0
    
    def list_chapters(self, status: str = None) -> List[Dict]:
        if status:
            rows = self.conn.execute("SELECT * FROM chapters WHERE status=? ORDER BY chapter_num", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM chapters ORDER BY chapter_num").fetchall()
        return [dict(r) for r in rows]
    
    # --- 角色管理 ---
    def save_character(self, name: str, profile: Dict, state: str = ""):
        self.conn.execute(
            "INSERT OR REPLACE INTO characters (name, profile_json, last_state, updated_at) VALUES (?,?,?,?)",
            (name, json.dumps(profile, ensure_ascii=False), state, datetime.now())
        )
        self.conn.commit()
    
    def get_character(self, name: str) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM characters WHERE name=?", (name,)).fetchone()
        if row:
            result = dict(row)
            result['profile'] = json.loads(result['profile_json']) if result['profile_json'] else {}
            return result
        return None
    
    def list_characters(self) -> List[Dict]:
        rows = self.conn.execute("SELECT name, last_state FROM characters ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    
    # --- 任务日志 ---
    def save_quest(self, quest_id: str, **kwargs):
        kwargs['quest_id'] = quest_id
        kwargs['updated_at'] = datetime.now()
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        updates = ", ".join(f"{k}=excluded.{k}" for k in kwargs if k != 'quest_id')
        self.conn.execute(
            f"INSERT INTO quest_log ({cols}) VALUES ({placeholders}) ON CONFLICT(quest_id) DO UPDATE SET {updates}",
            list(kwargs.values())
        )
        self.conn.commit()
    
    def list_quests(self, status: str = None) -> List[Dict]:
        if status:
            rows = self.conn.execute("SELECT * FROM quest_log WHERE status=? ORDER BY quest_id", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM quest_log ORDER BY quest_id").fetchall()
        return [dict(r) for r in rows]
    
    # --- 生成日志 ---
    def log_generation(self, chapter_num: int, step: str, prompt_hash: str, 
                       response_preview: str, tokens: int, model: str):
        self.conn.execute(
            "INSERT INTO generation_log (chapter_num, step, prompt_hash, response_preview, tokens_used, model) VALUES (?,?,?,?,?,?)",
            (chapter_num, step, prompt_hash, response_preview[:500], tokens, model)
        )
        self.conn.commit()
    
    def close(self):
        self.conn.close()


# ============================================================
# 世界数据加载器 - 统一加载所有静态数据
# ============================================================
class WorldData:
    """世界数据容器 - 加载并持有所有静态设定"""
    
    def __init__(self):
        self.world_settings: Dict = {}
        self.concept_map: Dict = {}
        self.trope_index: Dict = {}
        self.project_config: Dict = {}
        self.story_outline: str = ""
        self.campaign_outlines: Dict[str, str] = {}
        self._loaded = False
    
    def load_all(self, base_dir: str = None) -> bool:
        """加载所有世界数据"""
        base = base_dir or cfg.BASE_DIR
        print("  [数据层] 正在加载世界数据...")
        
        self.world_settings = load_json(cfg.WORLD_FILE) or {}
        self.concept_map = load_json(cfg.CONCEPT_MAP_FILE) or {}
        self.trope_index = load_json(cfg.TROPE_INDEX_FILE) or {}
        self.project_config = load_json(cfg.PROJECT_CONFIG_FILE) or {}
        
        if not self.world_settings:
            print("  [!] 警告: 世界观文件未加载")
        if not self.trope_index:
            print("  [!] 警告: 套路索引未加载")
        
        # 加载故事总纲
        outline_file = self.project_config.get("story_outline_file", "")
        if outline_file:
            self.story_outline = load_text(os.path.join(base, outline_file)) or ""
        
        # 扫描战役细纲
        for fn in os.listdir(base):
            if fn.startswith("campaign_outline_") and fn.endswith(".md"):
                content = load_text(os.path.join(base, fn))
                if content:
                    self.campaign_outlines[fn] = content
        
        self._loaded = True
        print(f"  [数据层] 加载完成: {len(self.world_settings)}项世界设定, "
              f"{len(self.trope_index)}个套路, {len(self.campaign_outlines)}份战役细纲")
        return True
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
