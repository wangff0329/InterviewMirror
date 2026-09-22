from typing import Literal

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: Literal["demo", "openai-compatible"] = "demo"
    base_url: str | None = None
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.4, ge=0, le=2)


class CandidateProfile(BaseModel):
    target_role: str = ""
    target_company: str = ""
    strengths: list[str] = Field(default_factory=list)
    signature_experience: str = ""
    preferred_style: Literal["structured", "concise", "storytelling"] = "structured"
    custom_notes: str = ""


class InterviewQuestion(BaseModel):
    category: str
    question: str
    intent: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    resume_evidence: str | None = None


class InterviewPlan(BaseModel):
    match_score: int = Field(default=0, ge=0, le=100)
    match_summary: str
    candidate_summary: str
    matching_points: list[str]
    risk_points: list[str]
    questions: list[InterviewQuestion]


class QuestionBankItem(BaseModel):
    id: str
    category: str
    question: str
    intent: str
    difficulty: Literal["easy", "medium", "hard"]
    tips: list[str] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    dimensions: dict[str, int]
    strengths: list[str]
    improvements: list[str]
    suggested_answer: str
    follow_up_questions: list[str]


class InterviewResponse(BaseModel):
    request_id: str
    resume_filename: str
    resume_text_length: int
    plan: InterviewPlan


class AnswerEvaluationResponse(BaseModel):
    question: QuestionBankItem
    answer: str
    evaluation: AnswerEvaluation
