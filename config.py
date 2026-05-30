"""
AI小说工厂 v3.0 - 全局配置
所有路径、API密钥、模型设置的唯一来源。
"""
import os
from dataclasses import dataclass, field
from typing import Optional


def _load_env_file():
    """自动加载项目根目录的 .env 文件到环境变量"""
    env_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, value = line.partition('=')
                    key, value = key.strip(), value.strip().strip('"').strip("'")
                    if key and value and key not in os.environ:
                        os.environ[key] = value
            return env_path
    return None

# 在Config实例化之前加载
_loaded_env = _load_env_file()


@dataclass
class FactoryConfig:
    """工厂配置 - 可通过环境变量或配置文件覆盖"""
    
    # === 项目根目录 ===
    BASE_DIR: str = field(default_factory=lambda: os.environ.get(
        "NOVEL_FACTORY_DIR", os.path.dirname(os.path.abspath(__file__))
    ))
    
    # === AI API 配置 ===
    LLM_PROVIDER: str = field(default_factory=lambda: os.environ.get(
        "LLM_PROVIDER", "deepseek" if os.environ.get("DEEPSEEK_API_KEY") else "claude"
    ))
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    OPENAI_API_KEY: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    DEEPSEEK_API_KEY: str = field(default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY", ""))
    DEEPSEEK_BASE_URL: str = field(default_factory=lambda: os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    
    # 模型选择
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_MODEL: str = "gpt-4o"
    DEEPSEEK_MODEL: str = field(default_factory=lambda: os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"))
    
    # 生成参数
    MAX_TOKENS_OUTLINE: int = 4000
    MAX_TOKENS_WRITING: int = 8000
    MAX_TOKENS_REPORT: int = 2000
    TEMPERATURE_OUTLINE: float = 0.7
    TEMPERATURE_WRITING: float = 0.85
    
    # === 数据目录 ===
    @property
    def DATA_DIR(self): return os.path.join(self.BASE_DIR, "data")
    
    @property
    def TEMPLATES_B_DIR(self): return os.path.join(self.BASE_DIR, "data", "templates_b")
    
    @property
    def TEMPLATES_C_DIR(self): return os.path.join(self.BASE_DIR, "data", "templates_c")
    
    @property
    def MEMORY_BANK_DIR(self): return os.path.join(self.BASE_DIR, "memory_bank")
    
    @property
    def OUTPUT_DIR(self): return os.path.join(self.BASE_DIR, "output")
    
    @property
    def DB_PATH(self): return os.path.join(self.BASE_DIR, "data", "factory.db")
    
    # === 核心数据文件 ===
    @property
    def WORLD_FILE(self): return os.path.join(self.DATA_DIR, "my_world.json")
    
    @property
    def CONCEPT_MAP_FILE(self): return os.path.join(self.DATA_DIR, "concept_map.json")
    
    @property
    def TROPE_INDEX_FILE(self): return os.path.join(self.DATA_DIR, "trope_index.json")
    
    @property
    def PROJECT_CONFIG_FILE(self): return os.path.join(self.BASE_DIR, "project_config.json")
    
    # === 质量控制 ===
    MIN_CHAPTER_WORDS: int = 1500
    MAX_CHAPTER_WORDS: int = 5000
    CONSISTENCY_CHECK: bool = True
    
    def ensure_dirs(self):
        """确保所有必需目录存在"""
        for d in [self.DATA_DIR, self.TEMPLATES_B_DIR, self.TEMPLATES_C_DIR,
                  self.MEMORY_BANK_DIR, self.OUTPUT_DIR]:
            os.makedirs(d, exist_ok=True)
    
    @property
    def has_api_key(self) -> bool:
        if self.LLM_PROVIDER == "deepseek":
            return bool(self.DEEPSEEK_API_KEY)
        elif self.LLM_PROVIDER == "claude":
            return bool(self.ANTHROPIC_API_KEY)
        elif self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        return False


# 全局单例
cfg = FactoryConfig()
