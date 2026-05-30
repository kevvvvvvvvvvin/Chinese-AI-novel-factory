"""
AI小说工厂 v3.0 - Web API (多项目版)
启动: pip install fastapi uvicorn && uvicorn web_api:app --reload --port 8000
"""
import os, sys, json
from typing import Dict, List, Optional
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, HTMLResponse
    from pydantic import BaseModel
except ImportError:
    print("需安装: pip install fastapi uvicorn"); sys.exit(1)

from config import cfg
from core.data_manager import WorldData, ProjectDB, load_text, save_text, load_json, save_json
from core.trope_engine import TropeEngine
from core.llm_gateway import LLMGateway
from core.pipeline import Pipeline
from core.autopilot import AutoPilot
from core.project_manager import ProjectManager
from core.mvp_workflows import MVPWorkflowService
from core.quota_manager import QuotaManager

app = FastAPI(title="AI小说工厂", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pm = ProjectManager()
llm = LLMGateway()
_global_world = WorldData()

@app.on_event("startup")
async def startup():
    cfg.ensure_dirs()
    _global_world.load_all()
    llm.initialize()
    projects = pm.list_projects()
    if not projects and _global_world.trope_index:
        try:
            name = _global_world.project_config.get("current_project_name", "默认项目")
            pm.create_project(name, genre="玄幻")
            pm.switch_to(pm.list_projects()[0]["id"])
        except: pass
    elif projects:
        pm.switch_to(projects[0]["id"])

def _world(): return pm.current_world or _global_world
def _db():
    if not pm.current_id:
        ps = pm.list_projects()
        if ps: pm.switch_to(ps[0]["id"])
    return pm.current_db or ProjectDB()
def _engine(): return TropeEngine(_world().trope_index)
def _pipeline(): return Pipeline(_world(), _db(), _engine(), llm)
def _pilot(): return AutoPilot(_world(), _db(), _engine(), llm)
def _mvp(): return MVPWorkflowService(_world(), _db(), _engine(), llm)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    p = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(p) if os.path.exists(p) else HTMLResponse("<h1>API运行中</h1><p>/docs</p>")

# --- 数据模型 ---
class CreateProjectReq(BaseModel):
    name: str; genre: str = ""; description: str = ""
class ProduceReq(BaseModel):
    chapter_num: int; quest_node: str; campaign_content: str = ""
    tropes: List[str] = []; character_states: Dict = {}; style: Dict = {}
class BatchReq(BaseModel):
    start: int; end: int; campaign_file: str = ""; token_budget: int = 0
class ChapterUpdateReq(BaseModel):
    title: str = ""; content: str = ""; outline: str = ""; status: str = ""

# --- 小说日更助手 MVP ---
@app.get("/api/mvp/status")
async def mvp_status(member_id: str = "default_member"):
    quota = QuotaManager().get_usage(member_id)
    return {
        "product_name": "小说日更助手",
        "version": "0.1.0",
        "member_id": member_id,
        "quota": quota,
        "llm": llm.get_stats(),
        "available_workflows": [
            "topic_generator",
            "character_generator",
            "golden_three_outline",
            "daily_chapter_pack",
            "opening_diagnosis",
        ],
    }

@app.post("/api/mvp/topic")
async def mvp_topic(req: Dict):
    return _mvp().generate_topic(req or {})

@app.post("/api/mvp/characters")
async def mvp_characters(req: Dict):
    return _mvp().generate_characters(req or {})

@app.post("/api/mvp/golden-three")
async def mvp_golden_three(req: Dict):
    return _mvp().generate_golden_three(req or {})

@app.post("/api/mvp/daily-chapter")
async def mvp_daily_chapter(req: Dict):
    return _mvp().generate_daily_chapter_pack(req or {})

@app.post("/api/mvp/opening-diagnosis")
async def mvp_opening_diagnosis(req: Dict):
    return _mvp().diagnose_opening(req or {})

# --- 项目 ---
@app.get("/api/projects")
async def list_projects():
    return {"projects": pm.list_projects(), "current": pm.current_id}

@app.post("/api/projects")
async def create_project(req: CreateProjectReq):
    try:
        meta = pm.create_project(req.name, req.genre, req.description)
        pm.switch_to(meta["id"])
        return {"success": True, "project": meta}
    except ValueError as e: raise HTTPException(400, str(e))

@app.post("/api/projects/{pid}/switch")
async def switch_project(pid: str):
    if pm.switch_to(pid): return {"success": True, "current": pid}
    raise HTTPException(404, "项目不存在")

@app.delete("/api/projects/{pid}")
async def delete_project(pid: str):
    if pm.delete_project(pid): return {"success": True}
    raise HTTPException(404)

# --- 状态 ---
@app.get("/api/status")
async def get_status():
    db = _db(); w = _world()
    chs = db.list_chapters() if db else []
    return {
        "project": pm.current_id,
        "llm": llm.get_stats(),
        "tropes": len(w.trope_index) if w else 0,
        "campaigns": len(w.campaign_outlines) if w else 0,
        "chapters": {"total": len(chs), "completed": sum(1 for c in chs if c.get("status")=="completed"), "words": sum(c.get("word_count",0) for c in chs)},
    }

# --- 世界观 ---
@app.get("/api/world")
async def get_world():
    w = _world()
    return {"settings": w.world_settings, "concept_map": w.concept_map,
            "story_outline": (w.story_outline or "")[:5000],
            "campaigns": list(w.campaign_outlines.keys())}

# --- 套路 ---
@app.get("/api/tropes")
async def list_tropes():
    e = _engine()
    return {"total": e.count, "categories": {k: len(v) for k,v in e.get_categories().items()},
            "tropes": [{"name":n, "category":d.get("功能大类",""), "tags":d.get("功能标签",[]), "desc":d.get("描述","")[:80]} for n,d in e.index.items()]}

@app.get("/api/tropes/search")
async def search_tropes(q: str, k: int = 10):
    return [{"name":n,"score":round(s,3)} for n,s in _engine().semantic_search(q, k)]

@app.get("/api/tropes/categories")
async def trope_categories():
    return _engine().get_categories()

# --- 章节 ---
@app.get("/api/chapters")
async def list_chapters():
    db = _db(); chs = db.list_chapters() if db else []
    for c in chs:
        c["content_preview"] = (c.get("content") or "")[:200]
        c["content"] = None
    return chs

@app.get("/api/chapters/{num}")
async def get_chapter(num: int):
    ch = _db().get_chapter(num)
    if not ch: raise HTTPException(404)
    return ch

@app.put("/api/chapters/{num}")
async def update_chapter(num: int, req: ChapterUpdateReq):
    u = {}
    if req.title: u["title"] = req.title
    if req.content: u["content"] = req.content; u["word_count"] = len(req.content)
    if req.outline: u["outline"] = req.outline
    if req.status: u["status"] = req.status
    if u: _db().save_chapter(num, **u)
    return {"success": True}

# --- 生产 ---
@app.post("/api/produce/chapter")
async def produce_chapter(req: ProduceReq):
    campaign = req.campaign_content or (list(_world().campaign_outlines.values()) or [""])[0]
    return _pipeline().produce_chapter(req.chapter_num, req.quest_node, campaign, req.tropes, req.character_states, req.style)

@app.post("/api/produce/batch")
async def produce_batch(req: BatchReq, bg: BackgroundTasks):
    if not llm.is_online: raise HTTPException(400, "需要API Key")
    campaign = None
    w = _world()
    if w.campaign_outlines: campaign = list(w.campaign_outlines.values())[0]
    if not campaign: raise HTTPException(400, "无战役细纲")
    bg.add_task(_pilot().produce_range, req.start, req.end, campaign_text=campaign, token_budget=req.token_budget)
    return {"status": "started"}

@app.post("/api/produce/auto")
async def produce_auto(bg: BackgroundTasks):
    if not llm.is_online: raise HTTPException(400, "需要API Key")
    bg.add_task(_pilot().produce_all)
    return {"status": "started"}

# --- 导出 ---
@app.get("/api/export/full")
async def export_full():
    db = _db(); chs = db.list_chapters() if db else []
    parts = []
    for ch in sorted(chs, key=lambda x: x["chapter_num"]):
        c = ch.get("content","")
        if c:
            parts.append(f"\n第{ch['chapter_num']}章 {ch.get('title','')}\n\n{c}")
    text = "\n".join(parts)
    return {"chapters": len(parts), "words": len(text), "content": text}
