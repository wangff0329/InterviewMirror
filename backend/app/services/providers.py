import json
from typing import Any

from langchain_openai import ChatOpenAI

from app.schemas import (
    AnswerEvaluation,
    CandidateProfile,
    InterviewPlan,
    ModelConfig,
    QuestionBankItem,
)


QUESTION_BANK = [
    QuestionBankItem(
        id="behavior-001",
        category="自我介绍",
        question="请做一个和这个岗位相关的自我介绍。",
        intent="判断候选人能否围绕岗位组织信息，并快速建立可信度。",
        difficulty="easy",
        tips=["控制在 90 秒内", "优先讲与岗位最相关的经历", "用结果而不是职责收尾"],
    ),
    QuestionBankItem(
        id="behavior-002",
        category="项目深挖",
        question="请讲一个你主导并最终产生明确结果的项目。",
        intent="验证 ownership、决策过程和结果意识。",
        difficulty="medium",
        tips=["使用 STAR 结构", "明确你本人做了什么", "补充可量化结果"],
    ),
    QuestionBankItem(
        id="behavior-003",
        category="失败复盘",
        question="讲一个结果不如预期的项目，你从中学到了什么？",
        intent="评估反思能力、责任感和成长性。",
        difficulty="medium",
        tips=["不要把失败归因给别人", "说明你采取过的补救行动", "讲清楚之后的行为改变"],
    ),
    QuestionBankItem(
        id="behavior-004",
        category="协作沟通",
        question="遇到合作方目标不一致时，你通常如何推进？",
        intent="评估跨团队影响力、沟通方式和冲突处理能力。",
        difficulty="medium",
        tips=["先说明分歧是什么", "讲具体沟通动作", "用结果证明推进有效"],
    ),
    QuestionBankItem(
        id="technical-001",
        category="技术能力",
        question="你最熟悉的一项技术或方法是什么？请结合实际项目说明。",
        intent="区分真实使用经验与只停留在概念层面的了解。",
        difficulty="medium",
        tips=["说明使用场景", "讲一个关键取舍", "准备性能、稳定性或成本结果"],
    ),
    QuestionBankItem(
        id="technical-002",
        category="问题解决",
        question="如果线上核心指标突然下降，你会如何定位问题？",
        intent="观察排查路径、优先级判断和止损意识。",
        difficulty="hard",
        tips=["先确认指标口径和影响范围", "从时间、版本、流量分层", "说明止损与长期修复"],
    ),
    QuestionBankItem(
        id="motivation-001",
        category="求职动机",
        question="为什么想申请这个岗位？你希望在下一份工作中获得什么？",
        intent="判断动机是否真实，以及候选人与岗位的长期匹配度。",
        difficulty="easy",
        tips=["不要只复述公司介绍", "连接自己的经历与岗位机会", "表达具体的成长目标"],
    ),
    QuestionBankItem(
        id="leadership-001",
        category="领导力",
        question="请讲一个你没有正式职权，但推动别人完成目标的例子。",
        intent="评估影响力、共识建立和推动复杂事项的能力。",
        difficulty="hard",
        tips=["说明阻力来自哪里", "讲清楚你如何建立共识", "补充最终的业务结果"],
    ),
]


DEMO_PLAN = InterviewPlan(
    match_score=82,
    match_summary="你的经历和岗位方向有较强交集，重点需要把项目结果、个人贡献和协作方式讲得更具体。",
    candidate_summary="候选人的经历与目标岗位存在可进一步验证的匹配点，建议围绕项目结果、数据判断和跨团队协作展开面试。",
    matching_points=["具备可被追问的项目经历", "岗位要求与候选人实践经验有交集", "可以通过量化结果验证实际影响力"],
    risk_points=["需要准备一个失败复盘案例", "需要说清楚个人贡献而不是只描述团队成果"],
    questions=[
        {"category": "项目深挖", "question": "请挑选一个最能代表你的项目，说明背景、你的具体职责、关键决策和最终结果。", "intent": "验证项目 ownership 与结果意识", "difficulty": "medium"},
        {"category": "岗位匹配", "question": "如果入职后负责这个岗位的核心目标，你会如何拆解前 30 天的工作计划？", "intent": "观察结构化思考和岗位理解", "difficulty": "hard"},
        {"category": "数据能力", "question": "请分享一次你通过数据发现问题、提出假设并验证结果的经历。", "intent": "验证数据驱动的工作方式", "difficulty": "medium"},
        {"category": "协作能力", "question": "遇到合作方目标不一致或项目被卡住时，你是如何推动事情继续前进的？", "intent": "评估跨团队沟通与影响力", "difficulty": "medium"},
        {"category": "失败复盘", "question": "讲一个结果不如预期的项目。现在回头看，你会在哪个节点做不同的决策？", "intent": "评估反思能力与成长性", "difficulty": "easy"},
        {"category": "情景题", "question": "如果核心指标连续两周下降，你会先看哪些数据，如何快速定位原因？", "intent": "观察问题定位和优先级判断", "difficulty": "hard"},
    ],
)


def get_question_bank(category: str | None = None) -> list[QuestionBankItem]:
    if not category or category == "全部":
        return QUESTION_BANK
    return [item for item in QUESTION_BANK if item.category == category]


def evaluate_answer(question: QuestionBankItem, answer: str, config: ModelConfig) -> AnswerEvaluation:
    if config.provider == "demo":
        word_count = len(answer.strip())
        structure_score = 82 if any(marker in answer for marker in ["背景", "目标", "行动", "结果", "STAR"]) else 62
        evidence_score = 78 if word_count >= 80 else 55
        communication_score = 84 if 40 <= word_count <= 420 else 68
        overall = round((structure_score + evidence_score + communication_score) / 3)
        return AnswerEvaluation(
            overall_score=overall,
            dimensions={"结构": structure_score, "证据": evidence_score, "表达": communication_score},
            strengths=["回答已经有明确的经历主线", "能够看出你本人参与了实际行动"],
            improvements=["补充一个更具体的量化结果", "把个人贡献和团队整体成果分开说明"],
            suggested_answer="建议按照背景、目标、行动、结果四步重组：先交代问题，再说明你的判断和动作，最后用数据或事实收束。",
            follow_up_questions=["当时有哪些替代方案？", "如果再做一次，你会改变哪个决定？"],
        )
    if not config.api_key or not config.base_url:
        raise ValueError("在线模型需要同时配置 API Key 和 Base URL。")
    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url.rstrip("/"),
        model=config.model,
        temperature=config.temperature,
    )
    prompt = f"""
你是一名严格但建设性的面试教练。请评价候选人对下面问题的回答。
只返回 JSON，不要 Markdown：
{{
  "overall_score": 0,
  "dimensions": {{"结构": 0, "证据": 0, "表达": 0}},
  "strengths": ["string"],
  "improvements": ["string"],
  "suggested_answer": "string",
  "follow_up_questions": ["string"]
}}
评分范围 0-100。评价必须具体，不能只说“不错”。
问题：{question.question}
回答：{answer}
"""
    result = llm.invoke(prompt)
    return AnswerEvaluation.model_validate(_extract_json(result.content))


def _extract_json(content: str) -> dict[str, Any]:
    cleaned = content.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def generate_plan(
    job_description: str,
    resume_text: str,
    config: ModelConfig,
    profile: CandidateProfile | None = None,
) -> InterviewPlan:
    if config.provider == "demo":
        return DEMO_PLAN
    if not config.api_key or not config.base_url:
        raise ValueError("在线模型需要同时配置 API Key 和 Base URL。")

    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url.rstrip("/"),
        model=config.model,
        temperature=config.temperature,
    )
    prompt = f"""
你是一名资深技术面试官。请根据岗位要求、候选人简历和候选人自定义画像，生成一份中文面试准备计划。
必须只返回 JSON，不要 Markdown，不要额外解释。
JSON schema:
{{
  "candidate_summary": "string",
  "match_score": 0,
  "match_summary": "string",
  "matching_points": ["string"],
  "risk_points": ["string"],
  "questions": [
    {{
      "category": "string",
      "question": "string",
      "intent": "string",
      "difficulty": "easy|medium|hard",
      "resume_evidence": "string"
    }}
  ]
}}
至少生成 6 道问题，问题必须结合简历中的真实经历，避免泛泛而谈。

岗位要求：
{job_description[:12000]}

候选人简历：
{resume_text[:50000]}

候选人自定义画像：
{profile.model_dump_json() if profile else "{}"}
"""
    result = llm.invoke(prompt)
    return InterviewPlan.model_validate(_extract_json(result.content))
