#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端流水线测试: theme_router -> source_retrieval -> method_planner -> analysis -> critic
用法: python scripts/test_pipeline.py "问题"
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout.reconfigure(encoding="utf-8")

from graphs.state import (
    GraphInput, ThemeRouterInput, SourceRetrievalInput,
    MethodPlannerInput, AnalysisInput, CriticInput,
)
from graphs.nodes.theme_router_node import theme_router_node
from graphs.nodes.source_node import source_retrieval_node
from graphs.nodes.method_node import method_planner_node
from graphs.nodes.analysis_node import analysis_node
from graphs.nodes.critic_node import critic_node


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "创业公司面对行业寒冬，应该如何调整战略方向？"
    print(f"Q: {question}\n{'=' * 66}")

    # 1. 主题路由
    r1 = theme_router_node(GraphInput(user_question=question, theme_codes=[], output_mode="analysis"))
    themes = r1.selected_themes
    print(f"[theme_router] 主题: {json.dumps(themes, ensure_ascii=False)[:120]}")

    # 2. 混合检索
    r2 = source_retrieval_node(
        SourceRetrievalInput(user_question=question, selected_themes=themes))
    print(f"[source_retrieval] 结果片段: {r2.retrieval_results[:120].replace(chr(10), ' ')}...")

    # 3. 方法选择
    r3 = method_planner_node(
        MethodPlannerInput(user_question=question, selected_themes=themes,
                           retrieval_results=r2.retrieval_results))
    print(f"[method_planner] 方法: {json.dumps(r3.selected_methods, ensure_ascii=False)[:150]}")

    # 4. 人格化分析
    r4 = analysis_node(
        AnalysisInput(user_question=question, selected_themes=themes,
                      selected_methods=r3.selected_methods,
                      retrieval_results=r2.retrieval_results, output_mode="analysis"))
    print(f"[analysis] 草稿长度: {len(r4.draft_answer)}")

    # 5. 引用校验 + 合规检查
    r5 = critic_node(
        CriticInput(draft_answer=r4.draft_answer, retrieval_results=r2.retrieval_results,
                    selected_methods=r3.selected_methods))
    print(f"[critic] 终稿长度: {len(r5.markdown_answer)}")
    print("=" * 66)
    print(r5.markdown_answer[:1200])


if __name__ == "__main__":
    main()
