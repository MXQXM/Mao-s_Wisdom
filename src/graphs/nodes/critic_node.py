import os
import re
import json
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from graphs.state import CriticInput, CriticOutput
from graphs.nodes.local_llm import invoke_local_llm

CFG_NAME = "critic_llm_cfg.json"


def _project_root() -> Path:
    workspace_path = os.getenv("COZE_WORKSPACE_PATH")
    if workspace_path:
        return Path(workspace_path)
    return Path(__file__).resolve().parents[3]


def _load_persona() -> str:
    """加载教员人格卡(含限制层), 用于合规检查"""
    p = _project_root() / "assets" / "persona" / "persona_mao.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


_COMPLIANCE_CHECK = """
## 合规检查(硬性, 优先级最高)
在输出最终回答前, 必须逐条检查:
1. 是否冒充毛泽东本人身份? 若有(如"我是毛泽东""本主席"), 必须改写为思想应用式表述。
2. 是否有虚构引用? 声称"毛泽东说过/指出"的内容必须在检索结果中有原文依据, 否则删除或标注为推断。
3. 引用是否标注了篇名出处? 未标注的补充标注。
4. 是否有敏感历史评价或越界内容? 若有, 改为客观表述或删除。
5. 检索结果为空时, 回答是否如实声明了知识边界?
检查结果: 违规内容直接修正后输出, 不输出检查过程。
"""


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


def _build_citations(retrieval_results: str) -> List[Dict]:
    """从检索结果中提取引用来源"""
    citations: List[Dict] = []
    if not retrieval_results or retrieval_results == "未在知识库中找到相关检索结果。":
        return citations

    sections: List[str] = re.split(r"--- 检索结果 \d+ \(相关度: [\d.]+\) ---", retrieval_results)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines: List[str] = section.split("\n")
        content_lines: List[str] = []
        for line in lines:
            if line.startswith("[文档ID:"):
                continue
            content_lines.append(line)
        content_text: str = "\n".join(content_lines).strip()
        if content_text:
            excerpt: str = content_text[:100] + "..." if len(content_text) > 100 else content_text
            citations.append({
                "title": "毛选原文",
                "source": "知识库检索",
                "excerpt": excerpt,
                "score": 0.0
            })
    return citations[:10]


async def critic_node(state: CriticInput) -> CriticOutput:
    """
    title: 引用校验
    desc: 校验分析草稿中的引用真实性和判断准确性, 合规检查, 输出最终回答
    """
    # 读取LLM配置
    cfg_path = _project_root() / "config" / CFG_NAME
    with open(cfg_path, "r", encoding="utf-8") as f:
        llm_cfg: Dict = json.load(f)

    model_config: Dict = llm_cfg.get("config", {})
    sp: str = llm_cfg.get("sp", "")
    up_tpl_str: str = llm_cfg.get("up", "")

    # 注入人格卡限制层 + 合规检查清单
    persona: str = _load_persona()
    if persona:
        sp = sp + "\n\n" + persona
    sp = sp + _COMPLIANCE_CHECK

    # 渲染用户提示词
    up_tpl = Template(up_tpl_str)
    user_prompt: str = up_tpl.render(
        draft_answer=state.draft_answer,
        retrieval_results=state.retrieval_results
    )
    # 输出格式硬约束(置顶, 权重最高): 禁止输出审稿过程, 直接给最终回答
    user_prompt = (
        "【最高优先级指令】你是引用校验引擎, 但你的输出只能是校验完成后的最终回答正文(Markdown)。"
        "绝对禁止输出任何思考过程、审稿说明、'检索结果对照'、校验步骤、分析计划或任何元信息。"
        "直接在回复中输出最终可交付给用户的完整回答, 不要有任何前言后语。\n\n"
        + user_prompt
    )

    verified_answer: str = invoke_local_llm(
        system_prompt=sp,
        user_prompt=user_prompt,
        model_config=model_config,
    )

    # 构建引用来源
    citations: List[Dict] = _build_citations(state.retrieval_results)
    methods: List[Dict] = state.selected_methods if state.selected_methods else []
    action_checklist: List[Dict] = []

    return CriticOutput(
        markdown_answer=_extract_text(verified_answer),
        citations=citations,
        methods=methods,
        action_checklist=action_checklist
    )
