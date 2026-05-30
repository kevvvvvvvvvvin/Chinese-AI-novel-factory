#!/usr/bin/env python3
"""
AI小说工厂 v3.0 - 环境检查与安装向导
运行: python setup.py
"""
import os
import sys
import subprocess
import json

def check_python():
    v = sys.version_info
    print(f"  Python: {v.major}.{v.minor}.{v.micro}", end="")
    if v.major >= 3 and v.minor >= 8:
        print(" ✅")
        return True
    print(" ❌ (需要 3.8+)")
    return False

def check_package(name, pip_name=None):
    try:
        __import__(name)
        print(f"  {pip_name or name}: ✅")
        return True
    except ImportError:
        print(f"  {pip_name or name}: ❌ 未安装")
        return False

def install_package(pip_name):
    print(f"  正在安装 {pip_name}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])

def check_data_files():
    base = os.path.dirname(os.path.abspath(__file__))
    files = {
        "世界观": os.path.join(base, "data", "my_world.json"),
        "概念图谱": os.path.join(base, "data", "concept_map.json"),
        "套路索引": os.path.join(base, "data", "trope_index.json"),
        "项目配置": os.path.join(base, "project_config.json"),
    }
    dirs = {
        "模板B": os.path.join(base, "data", "templates_b"),
        "模板C": os.path.join(base, "data", "templates_c"),
        "记忆库": os.path.join(base, "memory_bank"),
        "输出": os.path.join(base, "output"),
    }
    
    all_ok = True
    for name, path in files.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  {name}: ✅ ({size}字节)")
        else:
            print(f"  {name}: ❌ 缺失")
            all_ok = False
    
    for name, path in dirs.items():
        if os.path.exists(path):
            count = len(os.listdir(path))
            print(f"  {name}: ✅ ({count}个文件)")
        else:
            os.makedirs(path, exist_ok=True)
            print(f"  {name}: 📁 已创建")
    
    return all_ok

def setup_api_key():
    print("\n" + "="*50)
    print("  API配置（可选，跳过则使用离线模式）")
    print("="*50)
    print("  支持的API:")
    print("  1. Anthropic Claude (推荐)")
    print("  2. OpenAI GPT-4")
    print("  3. 跳过（离线模式）")
    
    choice = input("\n  请选择: ").strip()
    
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    
    if choice == "1":
        key = input("  请输入 Anthropic API Key: ").strip()
        if key:
            with open(env_file, "w") as f:
                f.write(f"ANTHROPIC_API_KEY={key}\n")
                f.write("LLM_PROVIDER=claude\n")
            print("  ✅ Claude API已配置")
            print(f"  💡 也可设置环境变量: export ANTHROPIC_API_KEY={key[:8]}...")
    elif choice == "2":
        key = input("  请输入 OpenAI API Key: ").strip()
        if key:
            with open(env_file, "w") as f:
                f.write(f"OPENAI_API_KEY={key}\n")
                f.write("LLM_PROVIDER=openai\n")
            print("  ✅ OpenAI API已配置")
    else:
        print("  📄 已选择离线模式（系统将导出Prompt文件供手动使用）")


def main():
    print("""
╔══════════════════════════════════════════════════╗
║   🏭 AI小说工厂 v3.0 - 环境检查与安装向导       ║
╚══════════════════════════════════════════════════╝
""")
    
    # 1. Python版本
    print("[1/4] 检查Python版本")
    if not check_python():
        print("  请升级Python到3.8以上")
        return
    
    # 2. 依赖包
    print("\n[2/4] 检查依赖包")
    
    # 核心依赖（必需）
    core_ok = True
    # Python标准库，无需检查
    print("  json/os/sqlite3: ✅ (标准库)")
    
    # 可选依赖
    print("\n  --- 可选依赖 ---")
    has_st = check_package("sentence_transformers", "sentence-transformers")
    has_sklearn = check_package("sklearn", "scikit-learn")
    has_anthropic = check_package("anthropic")
    has_openai = check_package("openai")
    
    # 询问安装
    missing = []
    if not has_anthropic:
        missing.append("anthropic")
    if not has_st:
        missing.append("sentence-transformers")
    if not has_sklearn:
        missing.append("scikit-learn")
    
    if missing:
        print(f"\n  可选包未安装: {', '.join(missing)}")
        if input("  是否安装? (y/n): ").lower() == 'y':
            for pkg in missing:
                try:
                    install_package(pkg)
                except Exception as e:
                    print(f"  ⚠️ {pkg}安装失败: {e}")
    
    # 3. 数据文件
    print("\n[3/4] 检查数据文件")
    check_data_files()
    
    # 4. API配置
    print("\n[4/4] API配置")
    env_vars = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    }
    
    has_key = any(env_vars.values())
    if has_key:
        for k, v in env_vars.items():
            if v:
                print(f"  {k}: ✅ ({v[:8]}...)")
        print("  API已配置，将使用全自动模式")
    else:
        # 检查.env文件
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            print("  .env文件已存在 ✅")
        else:
            setup_api_key()
    
    # 完成
    print("\n" + "="*50)
    print("  🎉 环境检查完成！")
    print("="*50)
    print("\n  启动命令:")
    print("    python main.py          # 交互式界面")
    print("    python main.py --plan   # 直接规划")
    print("    python main.py --status # 查看状态")
    print()


if __name__ == "__main__":
    main()
