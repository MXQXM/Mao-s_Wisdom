from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class GlobalState(BaseModel):
    """全局状态 - 工作流运行过程中的共享数据"""
    user_question: str = Field(default="", description="用户提出的现实问题")
    theme_codes: List[str] = Field(default=[], description="用户预选的主题编码列表")
    output_mode: str = Field(default="analysis_table", description="输出模式：normal=纯文本；analysis_table=完整结构化输出")
    selected_themes: List[Dict] = Field(default=[], description="识别出的主题列表")
    retrieval_results: str = Field(default="", description="知识库检索结果文本")
    selected_methods: List[Dict] = Field(default=[], description="选中的分析方法列表")
    draft_answer: str = Field(default="", description="AnalysisAgent生成的分析草稿")
    markdown_answer: str = Field(default="", description="最终Markdown格式的回答全文")
    citations: List[Dict] = Field(default=[], description="引用来源列表")
    methods: List[Dict] = Field(default=[], description="本次分析使用的方法模型")
    action_checklist: List[Dict] = Field(default=[], description="7天行动清单")


class GraphInput(BaseModel):
    """工作流输入"""
    user_question: str = Field(..., description="用户提出的现实问题，支持自然语言描述")
    theme_codes: List[str] = Field(default=[], description="用户预选的主题编码列表，为空时自动判断")
    output_mode: str = Field(default="analysis_table", description="输出模式：normal=纯文本；analysis_table=完整结构化输出")


class GraphOutput(BaseModel):
    """工作流输出"""
    markdown_answer: str = Field(default="", description="最终Markdown格式的回答全文")
    citations: List[Dict] = Field(default=[], description="引用来源列表")
    methods: List[Dict] = Field(default=[], description="本次分析使用的方法模型")
    action_checklist: List[Dict] = Field(default=[], description="7天行动清单")
    selected_themes: List[Dict] = Field(default=[], description="识别出的主题列表")


# ========== 节点2: ThemeRouterAgent ==========
class ThemeRouterInput(BaseModel):
    """主题识别节点输入"""
    user_question: str = Field(..., description="用户提出的现实问题")
    theme_codes: List[str] = Field(default=[], description="用户预选的主题编码列表")
    output_mode: str = Field(default="analysis_table", description="输出模式")


class ThemeRouterOutput(BaseModel):
    """主题识别节点输出"""
    selected_themes: List[Dict] = Field(..., description="识别出的主题列表，每个元素包含code/name/reason")


# ========== 节点3: SourceRetrievalAgent ==========
class SourceRetrievalInput(BaseModel):
    """知识库检索节点输入"""
    user_question: str = Field(..., description="用户提出的现实问题")
    selected_themes: List[Dict] = Field(default=[], description="识别出的主题列表")


class SourceRetrievalOutput(BaseModel):
    """知识库检索节点输出"""
    retrieval_results: str = Field(..., description="知识库检索结果文本")


# ========== 节点4: MethodPlannerAgent ==========
class MethodPlannerInput(BaseModel):
    """方法选择节点输入"""
    user_question: str = Field(..., description="用户提出的现实问题")
    selected_themes: List[Dict] = Field(..., description="识别出的主题列表")
    retrieval_results: str = Field(..., description="知识库检索结果")


class MethodPlannerOutput(BaseModel):
    """方法选择节点输出"""
    selected_methods: List[Dict] = Field(..., description="选中的分析方法列表，每个元素包含code/name/reason/risk_note")


# ========== 节点5: AnalysisAgent ==========
class AnalysisInput(BaseModel):
    """结构化分析节点输入"""
    user_question: str = Field(..., description="用户提出的现实问题")
    selected_themes: List[Dict] = Field(..., description="识别出的主题列表")
    retrieval_results: str = Field(..., description="知识库检索结果")
    selected_methods: List[Dict] = Field(..., description="选中的分析方法列表")
    output_mode: str = Field(default="analysis_table", description="输出模式")


class AnalysisOutput(BaseModel):
    """结构化分析节点输出"""
    draft_answer: str = Field(..., description="结构化分析草稿")


# ========== 节点6: CriticAgent ==========
class CriticInput(BaseModel):
    """引用校验节点输入"""
    draft_answer: str = Field(..., description="分析草稿")
    retrieval_results: str = Field(..., description="知识库检索结果")
    selected_methods: List[Dict] = Field(default=[], description="选中的分析方法列表")


class CriticOutput(BaseModel):
    """引用校验节点输出"""
    markdown_answer: str = Field(..., description="校验后的最终Markdown回答")
    citations: List[Dict] = Field(default=[], description="引用来源列表")
    methods: List[Dict] = Field(default=[], description="本次分析使用的方法模型")
    action_checklist: List[Dict] = Field(default=[], description="7天行动清单")
