import os
import re
import json
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from graphs.state import ThemeRouterInput, ThemeRouterOutput
from graphs.nodes.local_llm import invoke_local_llm

CFG_NAME = "theme_router_llm_cfg.json"


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


async def theme_router_node(state: ThemeRouterInput) -> ThemeRouterOutput:
    """
    title: 主题识别
    desc: 识别用户问题的主题分类(十大主题), 输出主题代码与名称
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
        theme_codes=json.dumps(state.theme_codes, ensure_ascii=False),
        output_mode=state.output_mode
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
    # 兼容包装格式: {"themes": [...]} / {"items": [...]} / 单个对象 {"code": ...}
    if isinstance(parsed, dict):
        if parsed.get("code") and parsed.get("name"):
            parsed = [parsed]                 # 单个主题对象
        else:
            for key in ("selected_themes", "themes", "items", "result", "data", "list"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                parsed = []
    if not isinstance(parsed, list):
        parsed = []

    themes: List[Dict] = []
    for item in parsed:
        if isinstance(item, dict) and item.get("code") and item.get("name"):
            themes.append({"code": item["code"], "name": item["name"]})
    return ThemeRouterOutput(selected_themes=themes[:3])
