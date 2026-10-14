#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毛选 DeepAgent 服务 (LangGraph 原生版)
接口:
  GET  /health            健康检查
  GET  /graph_parameter   工作流输入/输出格式说明
  POST /run               完整分析(JSON)
  POST /stream_run        SSE 流式运行
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Optional, List, Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from graphs.graph import main_graph

app = FastAPI(title="毛选 DeepAgent", description="教员人格 + RAG 知识检索 + DeepAgent 工作流")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEOUT_SECONDS = 300

# 静态文件托管: 手机/局域网可通过 http://<ip>:5000/static/chat.html 访问前端
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
app.mount("/static", StaticFiles(directory=str(_PROJECT_ROOT), html=False), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(_PROJECT_ROOT / "chat.html")


class RunRequest(BaseModel):
    user_question: str = Field(description="用户提出的现实问题")
    theme_codes: List[str] = Field(default_factory=list, description="预选主题编码, 空则自动判断")
    output_mode: str = Field(default="analysis", description="输出模式")


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Service is running"}


@app.get("/graph_parameter")
async def graph_parameter():
    """返回工作流输入输出 schema (前端动态渲染用)"""
    return {
        "input_schema": {
            "properties": {
                "user_question": {"type": "string", "description": "用户提出的现实问题"},
                "theme_codes": {"type": "array", "items": {"type": "string"}, "description": "预选主题编码"},
                "output_mode": {"type": "string", "description": "输出模式"},
            },
            "required": ["user_question"],
        },
        "output_schema": {
            "properties": {
                "markdown_answer": {"type": "string", "description": "最终回答(Markdown)"},
                "citations": {"type": "array", "description": "引用来源"},
                "methods": {"type": "array", "description": "选用的分析方法"},
                "selected_themes": {"type": "array", "description": "识别出的主题"},
            }
        },
        "nodes": [
            {"name": "theme_router", "desc": "主题识别"},
            {"name": "source_retrieval", "desc": "混合知识库检索"},
            {"name": "method_planner", "desc": "方法选择"},
            {"name": "analysis", "desc": "人格化分析"},
            {"name": "critic", "desc": "引用校验与合规检查"},
        ],
    }


@app.post("/run")
async def run(req: RunRequest):
    """完整分析: 主题 -> 检索 -> 方法 -> 分析 -> 校验, 返回最终回答
    节点均为 async 函数 -> LangGraph 在事件循环直接执行(不进线程池),
    Windows 上 asyncio 线程池内 SSL 连接失败(实测) -> async 节点绕开该坑
    """
    payload = req.model_dump()
    try:
        result = await asyncio.wait_for(main_graph.ainvoke(payload), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"error": f"处理超时({TIMEOUT_SECONDS}s)"})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"处理失败: {e}"})
    return {
        "markdown_answer": result.get("markdown_answer", ""),
        "citations": result.get("citations", []),
        "methods": result.get("methods", []),
        "action_checklist": result.get("action_checklist", []),
        "selected_themes": result.get("selected_themes", []),
    }


@app.post("/stream_run")
async def stream_run(req: RunRequest):
    """SSE 流式运行: 逐节点推送进度, 最后推送完整结果"""
    payload = req.model_dump()

    async def gen():
        yield _sse({"type": "start", "message": "工作流启动"})
        state_acc: dict = {}
        try:
            async for update in main_graph.astream(payload, stream_mode="updates"):
                for node_name, node_state in update.items():
                    state_acc.update(node_state)
                    brief = _node_brief(node_name, node_state)
                    yield _sse({"type": "node", "node": node_name, "brief": brief})
            result = {
                "markdown_answer": state_acc.get("markdown_answer", ""),
                "citations": state_acc.get("citations", []),
                "methods": state_acc.get("methods", []),
                "action_checklist": state_acc.get("action_checklist", []),
                "selected_themes": state_acc.get("selected_themes", []),
            }
            yield _sse({"type": "result", "data": result})
        except Exception as e:
            traceback.print_exc()
            yield _sse({"type": "error", "error": str(e)})
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _node_brief(node_name: str, state: dict) -> str:
    """每个节点完成后的简短说明"""
    if node_name == "theme_router":
        themes = state.get("selected_themes", [])
        names = [t.get("name", "") for t in themes if isinstance(t, dict)]
        return f"主题识别: {', '.join(names) if names else '无'}"
    if node_name == "source_retrieval":
        text = state.get("retrieval_results", "")
        return f"知识库检索: {len(text)} 字符"
    if node_name == "method_planner":
        methods = state.get("selected_methods", [])
        names = [m.get("name", "") for m in methods if isinstance(m, dict)]
        return f"方法选择: {', '.join(names) if names else '无'}"
    if node_name == "analysis":
        return f"人格化分析: 草稿 {len(state.get('draft_answer', ''))} 字符"
    if node_name == "critic":
        return f"引用校验: 终稿 {len(state.get('markdown_answer', ''))} 字符"
    return ""


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000)
