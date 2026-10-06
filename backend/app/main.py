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
    TranscriptionResponse,
    InterviewSessionAnalysis,
    InterviewSessionTurn,
    UserResponse,
)
from app.services.auth import authenticate_user, create_access_token, create_user, decode_access_token, init_auth_database
from app.services.pdf import extract_pdf_text
from app.services.profile import (
    create_profile_draft,
    extract_document_text,
    extract_profile,
    extract_profile_with_ai,
    get_latest_profile_context,
    init_profile_database,
    list_profile_versions,
    save_profile_version,
)
from app.services.providers import adapt_application, analyze_interview_session, evaluate_answer, get_question_bank
from app.services.transcription import transcribe_audio

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
init_profile_database(settings)


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


@app.post("/api/profile/drafts")
async def create_profile_draft_endpoint(
    resume: UploadFile = File(...),
    model_config_json: str = Form("{}", alias="model_config"),
    user: UserResponse = Depends(current_user),
) -> dict:
    content = await resume.read()
    if len(content) > settings.max_resume_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"资料不能超过 {settings.max_resume_size_mb} MB。")
    try:
        draft = create_profile_draft(
            settings,
            user.id,
            resume.filename or "profile",
            resume.content_type or "application/octet-stream",
            content,
        )
        config = ModelConfig.model_validate(json.loads(model_config_json))
        if config.provider != "demo":
            draft["profile"] = extract_profile_with_ai(
                extract_document_text(content, resume.filename or "profile", resume.content_type or ""),
                config,
                draft["profile"],
            )
        return draft
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/profile/versions")
def create_profile_version(
    payload: dict,
    user: UserResponse = Depends(current_user),
) -> dict:
    try:
        return save_profile_version(
            settings,
            user.id,
            int(payload["document_id"]),
            payload["profile"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/profile/versions")
def get_profile_versions(user: UserResponse = Depends(current_user)) -> list[dict]:
    return list_profile_versions(settings, user.id)


@app.post("/api/interviews/transcribe", response_model=TranscriptionResponse)
async def transcribe_interview_audio(
    audio: UploadFile = File(...),
    model_config_json: str = Form(..., alias="model_config"),
) -> TranscriptionResponse:
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="只支持音频文件。")
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=422, detail="音频文件为空。")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="音频不能超过 25 MB。")
    try:
        config = ModelConfig.model_validate(json.loads(model_config_json))
        text = await transcribe_audio(content, audio.filename or "answer.webm", audio.content_type, config)
        return TranscriptionResponse(text=text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"语音转写失败：{error}") from error


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


@app.post("/api/interviews/session-analysis", response_model=InterviewSessionAnalysis)
async def analyze_interview_session_endpoint(
    turns_json: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
    user: UserResponse = Depends(current_user),
) -> InterviewSessionAnalysis:
    try:
        turns = [InterviewSessionTurn.model_validate(item) for item in json.loads(turns_json)]
        config = ModelConfig.model_validate(json.loads(model_config_json))
        return analyze_interview_session(turns, config)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"整场面试分析失败：{error}") from error


@app.post("/api/interviews/generate", response_model=InterviewResponse)
async def generate_interview(
    resume: UploadFile | None = File(None),
    job_description: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
    profile_json: str = Form("{}", alias="profile"),
    user: UserResponse = Depends(current_user),
) -> InterviewResponse:
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="岗位要求不能为空。")
    try:
        config = ModelConfig.model_validate(json.loads(model_config_json))
        profile = json.loads(profile_json)
        saved_context = get_latest_profile_context(settings, user.id)
        if saved_context:
            profile = {**saved_context["profile"], **profile}
        if resume:
            if resume.content_type != "application/pdf":
                raise HTTPException(status_code=415, detail="岗位分析目前只支持 PDF 简历。")
            content = await resume.read()
            max_size = settings.max_resume_size_mb * 1024 * 1024
            if len(content) > max_size:
                raise HTTPException(status_code=413, detail=f"简历不能超过 {settings.max_resume_size_mb} MB。")
            resume_text = extract_pdf_text(content)
            resume_filename = resume.filename or "resume.pdf"
        elif saved_context:
            resume_text = saved_context["resume_text"]
            resume_filename = saved_context["filename"]
        else:
            raise HTTPException(status_code=422, detail="请先上传简历，或在“我的资料”中保存一个资料版本。")
        result = interview_graph.invoke(
            {
                "resume_text": resume_text,
                "job_description": job_description,
                "model_config": config,
                "profile": profile,
            }
        )
        return InterviewResponse(
            request_id=str(uuid.uuid4()),
            resume_filename=resume_filename,
            resume_text_length=len(resume_text),
            plan=result["plan"],
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"面试分析失败：{error}") from error


@app.post("/api/applications/adapt", response_model=ApplicationAdaptationResponse)
async def adapt_application_materials(
    resume: UploadFile | None = File(None),
    job_description: str = Form(...),
    model_config_json: str = Form(..., alias="model_config"),
    profile_json: str = Form("{}", alias="profile"),
    user: UserResponse = Depends(current_user),
) -> ApplicationAdaptationResponse:
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="岗位要求不能为空。")
    try:
        config = ModelConfig.model_validate(json.loads(model_config_json))
        profile_data = json.loads(profile_json)
        saved_context = get_latest_profile_context(settings, user.id)
        if resume:
            if resume.content_type != "application/pdf":
                raise HTTPException(status_code=415, detail="网申适配目前只支持 PDF 简历。")
            content = await resume.read()
            max_size = settings.max_resume_size_mb * 1024 * 1024
            if len(content) > max_size:
                raise HTTPException(status_code=413, detail=f"简历不能超过 {settings.max_resume_size_mb} MB。")
            resume_text = extract_pdf_text(content)
            resume_filename = resume.filename or "resume.pdf"
        elif saved_context:
            resume_text = saved_context["resume_text"]
            resume_filename = saved_context["filename"]
        else:
            raise HTTPException(status_code=422, detail="请先上传简历，或在“我的资料”中保存一个资料版本。")
        if saved_context:
            profile_data = {**saved_context["profile"], **profile_data}
        profile = CandidateProfile.model_validate(profile_data)
        adaptation = adapt_application(job_description, resume_text, config, profile)
        return ApplicationAdaptationResponse(
            request_id=str(uuid.uuid4()),
            resume_filename=resume_filename,
            resume_text_length=len(resume_text),
            adaptation=adaptation,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"网申适配失败：{error}") from error
