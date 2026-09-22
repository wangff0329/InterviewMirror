# Interview Mirror

Interview Mirror 是一个开源的 AI 模拟面试工作台：用户上传简历 PDF，输入目标岗位要求，并使用自己配置的 OpenAI-compatible 模型生成个性化面试题。

## 技术栈

- Frontend: Vue 3, Vite, JavaScript
- Backend: FastAPI, Python 3.11+
- AI orchestration: LangGraph
- Model adapter: `langchain-openai`，支持 OpenAI、Azure OpenAI、DeepSeek、通义千问、Ollama 等兼容接口
- Resume parsing: `pypdf`

## Project layout

```text
InterviewMirror/
├── frontend/       # Vue 3 + Vite
├── backend/        # FastAPI + LangGraph
└── docker-compose.yml
```

## Quick start

### 1. Start the API

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The frontend sends the model configuration per request, so users can bring their own API key. The key is not persisted by the backend. For local development, the app also supports Demo mode without an API key.

## Model configuration

The API accepts an OpenAI-compatible configuration:

```json
{
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "api_key": "your-key",
  "model": "gpt-4o-mini"
}
```

`base_url` should be the provider root, not the full `/chat/completions` path.

## API

- `GET /api/health`
- `POST /api/interviews/generate`
  - multipart field: `resume`
  - form field: `job_description`
  - form field: `model_config` (JSON string)

## Tests

```bash
cd backend
pytest
```

## Roadmap

- Streaming interview sessions with LangGraph checkpoints
- Follow-up questions based on the candidate's answer
- Rubric-based answer evaluation
- PostgreSQL persistence and authentication
- Provider presets and encrypted client-side configuration
