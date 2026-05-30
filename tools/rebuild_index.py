#!/usr/bin/env python3
"""
套路索引重建工具
扫描 data/templates_b/ 中的所有套路文件，自动重建 trope_index.json。
用于新增套路后的索引更新。

使用: python tools/rebuild_index.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分类关键词映射
CATEGORY_MAP = {
    '打脸': '爽点爆发', '退婚': '爽点爆发', '羞辱': '爽点爆发', '逼王': '爽点爆发',
    '秒杀': '战斗碾压', '碾压': '战斗碾压', '团灭': '战斗碾压', '一人': '战斗碾压',
    '独战': '战斗碾压', '一剑': '战斗碾压', '一掌': '战斗碾压', '肉身': '战斗碾压',
    '硬刚': '战斗碾压', '对决': '战斗碾压', '横扫': '战斗碾压', '镇压': '战斗碾压',
    '吸干': '战斗碾压', '威压': '战斗碾压',
    '收服': '势力扩张', '收编': '势力扩张', '降维': '势力扩张', '挖角': '势力扩张',
    '策反': '势力扩张', '传功': '势力扩张',
    '寻宝': '探索冒险', '禁地': '探索冒险', '古墓': '探索冒险', '拍卖': '探索冒险',
    '救美': '英雄救美', '救场': '英雄救美', '救援': '英雄救美', '驰援': '英雄救美',
    '逆天施救': '英雄救美',
    '救赎': '情感线', '前任': '情感线', '女神': '情感线', '联姻': '情感线',
    '约会': '情感线', '舔狗': '情感线', '血脉': '情感线', '情敌': '情感线',
    '误会': '情感线', '鼎炉': '情感线', '魅体': '情感线',
    '神豪': '身份反转', '直播': '身份反转', '同学聚会': '身份反转',
    '百亿': '身份反转', '后台': '身份反转', '阶级': '身份反转',
    '宴会': '社交场景', '鸿门宴': '社交场景',
    '宗门': '宗门冲突', '邪派': '宗门冲突',
    '反派': '反派体系', '大佬': '反派体系', '杀手': '反派体系',
    '夺舍': '反派体系', '内奸': '反派体系',
    '系统': '金手指', '传承': '金手指', '满级': '金手指',
    '突破': '主角成长', '改造': '主角成长', '魔改': '主角成长',
    '装备': '主角成长', '融合': '主角成长',
    '高手下山': '开局模板', '废柴': '开局模板', '回归': '开局模板',
    '流氓': '角色特色', '谦谦': '角色特色',
    '恶人': '智谋博弈', '将计就计': '智谋博弈', '黑吃黑': '智谋博弈',
    '卧底': '智谋博弈', '偷换': '智谋博弈', '先发制人': '智谋博弈',
}

def classify(name: str) -> str:
    for kw, cat in CATEGORY_MAP.items():
        if kw in name:
            return cat
    return '通用剧情'

def rebuild_index(templates_dir: str, output_file: str):
    """重建套路索引"""
    index = {}
    
    for filename in sorted(os.listdir(templates_dir)):
        if not filename.endswith('.txt'):
            continue
        
        filepath = os.path.join(templates_dir, filename)
        if os.path.getsize(filepath) < 50:
            continue
        
        trope_key = filename.replace('.txt', '')
        
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        
        # 尝试解析为JSON格式
        name, desc, tags = trope_key, '', []
        try:
            data = json.loads(raw)
            name = data.get('套路名称', trope_key)
            skeleton = data.get('逻辑骨架', {})
            desc = skeleton.get('触发时机', '') or skeleton.get('载体形式', '')
            tags = data.get('功能标签', [])
            if not tags:
                tags = [str(p)[:15] for p in data.get('产出', [])[:5]]
        except (json.JSONDecodeError, ValueError):
            # Markdown格式
            for line in raw.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    candidate = line.lstrip('#').strip()
                    if '核心逻辑' in candidate:
                        name = candidate.replace('核心逻辑骨架：', '').replace('核心逻辑骨架:', '')
                    elif not desc:
                        name = candidate
                    break
            for line in raw.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('---') and len(line) > 10:
                    desc = line[:120]
                    break
        
        index[name] = {
            "功能大类": classify(trope_key),
            "功能标签": tags[:5] if isinstance(tags, list) else [],
            "模板B文件名": filename,
            "描述": desc[:150] if desc else f"套路：{name}"
        }
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    # 统计
    cats = {}
    for v in index.values():
        c = v['功能大类']
        cats[c] = cats.get(c, 0) + 1
    
    print(f"\n✅ 索引重建完成: {len(index)} 个套路")
    print(f"   保存到: {output_file}")
    print(f"\n   分类统计:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"     {c}: {n}个")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base, "data", "templates_b")
    output_file = os.path.join(base, "data", "trope_index.json")
    
    if not os.path.exists(templates_dir):
        print(f"❌ 模板目录不存在: {templates_dir}")
        sys.exit(1)
    
    rebuild_index(templates_dir, output_file)
