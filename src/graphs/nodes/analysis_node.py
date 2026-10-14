import os
import json
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from graphs.state import AnalysisInput, AnalysisOutput
from graphs.nodes.local_llm import invoke_local_llm

CFG_NAME = "analysis_llm_cfg.json"


def _project_root() -> Path:
    workspace_path = os.getenv("COZE_WORKSPACE_PATH")
    if workspace_path:
        return Path(workspace_path)
    return Path(__file__).resolve().parents[3]


def _load_persona() -> str:
    """加载教员人格卡(语气/思维/限制), 注入系统提示"""
    p = _project_root() / "assets" / "persona" / "persona_mao.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


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


async def analysis_node(state: AnalysisInput) -> AnalysisOutput:
    """
    title: 结构化分析
    desc: 综合用户问题、主题、检索结果和分析方法，注入教员人格卡，生成深度分析报告
    """
    # 读取LLM配置
    cfg_path = _project_root() / "config" / CFG_NAME
    with open(cfg_path, "r", encoding="utf-8") as f:
        llm_cfg: Dict = json.load(f)

    model_config: Dict = llm_cfg.get("config", {})
    sp: str = llm_cfg.get("sp", "")
    up_tpl_str: str = llm_cfg.get("up", "")

    # 注入教员人格卡(语气/思维/限制), 位于系统提示尾部
    persona: str = _load_persona()
    if persona:
        sp = sp + "\n\n" + persona

    # 渲染用户提示词
    up_tpl = Template(up_tpl_str)
    user_prompt: str = up_tpl.render(
        user_question=state.user_question,
        selected_themes=json.dumps(state.selected_themes, ensure_ascii=False),
        selected_methods=json.dumps(state.selected_methods, ensure_ascii=False),
        retrieval_results=state.retrieval_results,
        output_mode=state.output_mode
    )

    draft_answer: str = invoke_local_llm(
        system_prompt=sp,
        user_prompt=user_prompt,
        model_config=model_config,
    )

    return AnalysisOutput(draft_answer=_extract_text(draft_answer))
