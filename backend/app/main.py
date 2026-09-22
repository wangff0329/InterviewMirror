import json
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.graph import build_interview_graph
from app.schemas import (
    AnswerEvaluationResponse,
    CandidateProfile,
    InterviewResponse,
    ModelConfig,
    QuestionBankItem,
)
from app.services.providers import evaluate_answer, get_question_bank

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
interview_graph = build_interview_graph()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/question-bank", response_model=list[QuestionBankItem])
def question_bank(category: str | None = None) -> list[QuestionBankItem]:
    return get_question_bank(category)


@app.post("/api/interviews/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_interview_answer(
    question_json: str = Form(...),
    answer: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
) -> AnswerEvaluationResponse:
    try:
        question = QuestionBankItem.model_validate(json.loads(question_json))
        config = ModelConfig.model_validate(json.loads(model_config_json))
        evaluation = evaluate_answer(question, answer, config)
        return AnswerEvaluationResponse(question=question, answer=answer, evaluation=evaluation)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"回答评价失败：{error}") from error


@app.post("/api/interviews/generate", response_model=InterviewResponse)
async def generate_interview(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
    profile_json: str = Form("{}", alias="profile"),
) -> InterviewResponse:
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="只支持 PDF 简历。")
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="岗位要求不能为空。")
    content = await resume.read()
    max_size = settings.max_resume_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"简历不能超过 {settings.max_resume_size_mb} MB。")
    try:
        config = ModelConfig.model_validate(json.loads(model_config_json))
        profile = CandidateProfile.model_validate(json.loads(profile_json))
        result = interview_graph.invoke(
            {
                "resume_bytes": content,
                "job_description": job_description,
                "model_config": config,
                "profile": profile,
            }
        )
        return InterviewResponse(
            request_id=str(uuid.uuid4()),
            resume_filename=resume.filename or "resume.pdf",
            resume_text_length=len(result["resume_text"]),
            plan=result["plan"],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"面试分析失败：{error}") from error
