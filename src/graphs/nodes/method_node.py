import os
import re
import json
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from graphs.state import MethodPlannerInput, MethodPlannerOutput
from graphs.nodes.local_llm import invoke_local_llm

CFG_NAME = "method_planner_llm_cfg.json"


def _project_root() -> Path:
    workspace_path = os.getenv("COZE_WORKSPACE_PATH")
    if workspace_path:
        return Path(workspace_path)
    return Path(__file__).resolve().parents[3]


def _extract_text(content) -> str:
    """安全提取LLM返回的文本内容"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return " ".join(parts)
    return str(content)


async def method_planner_node(state: MethodPlannerInput) -> MethodPlannerOutput:
    """
    title: 方法选择
    desc: 根据用户问题和主题，从五种分析方法中选择最合适的1-3个
    """
    # 读取LLM配置
    cfg_path = _project_root() / "config" / CFG_NAME
    with open(cfg_path, "r", encoding="utf-8") as f:
        llm_cfg: Dict = json.load(f)

    model_config: Dict = llm_cfg.get("config", {})
    sp: str = llm_cfg.get("sp", "")
    up_tpl_str: str = llm_cfg.get("up", "")

    # 渲染用户提示词
    up_tpl = Template(up_tpl_str)
    user_prompt: str = up_tpl.render(
        user_question=state.user_question,
        selected_themes=json.dumps(state.selected_themes, ensure_ascii=False),
        retrieval_results=state.retrieval_results
    )

    response_text: str = invoke_local_llm(
        system_prompt=sp,
        user_prompt=user_prompt,
        model_config=model_config,
    )

    # 解析JSON: 兼容 ```json 围栏与裸 JSON
    text = _extract_text(response_text).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.S)
        parsed = json.loads(m.group(0)) if m else []
    # 兼容包装格式: {"methods": [...]} / 单个对象 {"code": ...}
    if isinstance(parsed, dict):
        if parsed.get("code") and parsed.get("name"):
            parsed = [parsed]                 # 单个方法对象
        else:
            for key in ("selected_methods", "methods", "items", "result", "data", "list"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                parsed = []
    if not isinstance(parsed, list):
        parsed = []

    methods: List[Dict] = []
    for item in parsed:
        if isinstance(item, dict) and item.get("code") and item.get("name"):
            methods.append({
                "code": item["code"],
                "name": item["name"],
                "reason": item.get("reason", ""),
                "risk_note": item.get("risk_note", ""),
            })
    return MethodPlannerOutput(selected_methods=methods[:3])
