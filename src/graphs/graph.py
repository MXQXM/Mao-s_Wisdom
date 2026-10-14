from langgraph.graph import StateGraph, END
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
)
from graphs.nodes.theme_router_node import theme_router_node
from graphs.nodes.source_node import source_retrieval_node
from graphs.nodes.method_node import method_planner_node
from graphs.nodes.analysis_node import analysis_node
from graphs.nodes.critic_node import critic_node

# 工作流: 主题识别 -> 混合检索 -> 方法选择 -> 人格化分析 -> 引用校验
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

builder.add_node("theme_router", theme_router_node)
builder.add_node("source_retrieval", source_retrieval_node)
builder.add_node("method_planner", method_planner_node)
builder.add_node("analysis", analysis_node)
builder.add_node("critic", critic_node)

builder.set_entry_point("theme_router")
builder.add_edge("theme_router", "source_retrieval")
builder.add_edge("source_retrieval", "method_planner")
builder.add_edge("method_planner", "analysis")
builder.add_edge("analysis", "critic")
builder.add_edge("critic", END)

main_graph = builder.compile()
