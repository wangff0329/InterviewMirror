from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ModelConfig(BaseModel):
    provider: Literal["demo", "openai-compatible"] = "demo"
    base_url: str | None = None
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    transcription_model: str = "whisper-1"
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
    job_requirement: str | None = None
    follow_up_points: list[str] = Field(default_factory=list)


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


class InterviewSessionTurn(BaseModel):
    question: str
    answer: str
    evaluation: AnswerEvaluation


class InterviewSessionAnalysis(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str]
    priorities: list[str]
    recurring_follow_ups: list[str]
    next_practice_plan: list[str]


class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: float | None = None


class ApplicationAdaptation(BaseModel):
    target_role: str
    positioning: str
    profile_summary: str
    tailored_bullets: list[str]
    motivation_answer: str
    application_questions: list[dict[str, str]]
    keywords: list[str]
    cautions: list[str]


class ApplicationAdaptationResponse(BaseModel):
    request_id: str
    resume_filename: str
    resume_text_length: int
    adaptation: ApplicationAdaptation
