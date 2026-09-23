import json
import uuid

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.graph import build_interview_graph
from app.schemas import (
    ApplicationAdaptationResponse,
    AnswerEvaluationResponse,
    CandidateProfile,
    InterviewResponse,
    AuthResponse,
    LoginRequest,
    ModelConfig,
    QuestionBankItem,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import authenticate_user, create_access_token, create_user, decode_access_token, init_auth_database
from app.services.pdf import extract_pdf_text
from app.services.providers import adapt_application, evaluate_answer, get_question_bank

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
init_auth_database(settings)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest) -> AuthResponse:
    try:
        user = create_user(settings, payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return AuthResponse(access_token=create_access_token(settings, user), user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    user = authenticate_user(settings, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误。")
    return AuthResponse(access_token=create_access_token(settings, user), user=user)


def current_user(authorization: str | None = Header(default=None)) -> UserResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录。")
    try:
        return decode_access_token(settings, authorization[7:].strip())
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user(user: UserResponse = Depends(current_user)) -> UserResponse:
    return user


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


@app.post("/api/applications/adapt", response_model=ApplicationAdaptationResponse)
async def adapt_application_materials(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
    profile_json: str = Form("{}", alias="profile"),
) -> ApplicationAdaptationResponse:
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
        resume_text = extract_pdf_text(content)
        adaptation = adapt_application(job_description, resume_text, config, profile)
        return ApplicationAdaptationResponse(
            request_id=str(uuid.uuid4()),
            resume_filename=resume.filename or "resume.pdf",
            resume_text_length=len(resume_text),
            adaptation=adaptation,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"网申适配失败：{error}") from error
