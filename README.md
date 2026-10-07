# Interview Mirror

Interview Mirror 是一个开源的 AI 模拟面试与求职准备工作台。你可以上传简历、填写目标岗位要求，再使用兼容 OpenAI API 的模型生成个性化的面试题、岗位分析和网申材料。

## 功能概览

- **岗位分析**：根据简历和岗位描述，提取匹配点、风险点以及可能被追问的内容。
- **题库练习**：浏览题库并进行针对性练习。
- **AI 模拟面试**：生成个性化问题，支持文字回答、语音录制和回答评价。
- **我的资料**：上传 PDF 或 DOCX 简历，自动整理教育经历、项目、工作经历和技能，并保存资料版本。
- **网申适配**：根据目标岗位调整个人简介、经历要点、求职动机和常见申请问题的回答。
- **练习记录**：保存和查看过往练习结果。
- **Demo 模式**：本地开发时无需配置 API Key，也可以体验基础流程。

## 技术栈

### 前端

- Vue 3
- Vite
- JavaScript

### 后端

- FastAPI
- Python 3.11+
- LangGraph
- `langchain-openai`
- `pypdf`
- `python-docx`

项目支持 OpenAI、Azure OpenAI、DeepSeek、通义千问、Ollama 等兼容 OpenAI API 的模型服务。

## 项目结构

```text
InterviewMirror/
├── frontend/              # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue        # 主要页面与交互逻辑
│   │   ├── styles.css     # 全局样式
│   │   └── upload.css     # 上传组件样式
│   └── package.json
├── backend/               # FastAPI 后端
│   ├── app/
│   ├── tests/
│   └── pyproject.toml
└── docker-compose.yml
```

## 本地运行

### 环境要求

- Python 3.11 或更高版本
- Node.js 18 或更高版本
- npm

### 1. 启动后端 API

在项目根目录执行：

```bash
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows 命令提示符：

```bat
.venv\Scripts\activate.bat
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

后端启动后，可以访问：

- API 地址：`http://localhost:8000`
- 健康检查：`http://localhost:8000/api/health`

### 2. 启动前端

打开新的终端窗口，在项目根目录执行：

```bash
cd frontend
npm install
npm run dev
```

然后打开 Vite 输出的地址，通常是：

```text
http://localhost:5173
```

前端开发服务器会将 API 请求转发到后端服务。请确保后端和前端同时运行。

## 模型配置

应用支持两种模式：

1. **Demo 模式**：默认模式，不需要 API Key，适合本地体验界面和基础流程。
2. **在线模型模式**：填写兼容 OpenAI API 的服务地址、API Key 和模型名称。

配置示例：

```json
{
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "api_key": "your-api-key",
  "model": "gpt-4o-mini",
  "temperature": 0.4
}
```

注意：

- `base_url` 应填写服务根地址，例如 `https://api.openai.com/v1`。
- 不要把 `/chat/completions` 拼接到 `base_url` 后面。
- API Key 由前端按请求发送，后端不会将其持久化保存。
- 使用第三方模型服务时，请确认服务商的接口格式与 OpenAI Chat Completions API 兼容。

## 主要 API

### 基础接口

- `GET /api/health`：检查服务是否正常。
- `GET /api/question-bank`：获取题库。

### 面试接口

- `POST /api/interviews/generate`
  - `resume`：简历文件。
  - `job_description`：岗位描述。
  - `model_config`：JSON 格式的模型配置。
- `POST /api/interviews/evaluate`
  - `question_json`：当前面试题 JSON。
  - `answer`：用户回答。
  - `model_config`：JSON 格式的模型配置。

### 资料与网申接口

- `POST /api/profile/drafts`
  - `resume`：PDF 或 DOCX 简历文件。
  - `model_config`：JSON 格式的模型配置。
- `POST /api/profile/versions`
  - `document_id`：资料文档 ID。
  - `profile`：确认后的资料内容。
- `GET /api/profile/versions`：获取已保存的资料版本。
- `POST /api/applications/adapt`
  - `resume`：简历文件。
  - `job_description`：目标岗位要求。
  - `model_config`：JSON 格式的模型配置。
  - `profile`：候选人资料。

`/api/applications/adapt` 会返回岗位适配结果，包括个人定位、个人简介、改写后的经历要点、求职动机、常见申请问题、关键词以及事实核验提醒。

## 运行测试

后端测试：

```bash
cd backend
pytest
```

前端生产构建：

```bash
cd frontend
npm run build
```

## 使用建议

为了获得更有针对性的结果，建议：

1. 上传内容完整、格式清晰的 PDF 或 DOCX 简历。
2. 在岗位描述中尽量保留职位职责、任职要求和技术关键词。
3. 在“我的资料”中确认 AI 提取的内容，再保存为资料版本。
4. 对 AI 生成的经历描述和求职材料进行事实核验，不要直接提交未经确认的内容。

## 数据与隐私

- 模型配置按请求发送，后端不会持久化保存 API Key。
- 简历和求职信息可能包含个人隐私，请仅在可信的本地或服务器环境中运行。
- 使用第三方模型服务时，请同时遵守对应服务商的隐私政策和数据使用条款。

## 后续计划

- 使用 LangGraph 检查点实现流式面试会话。
- 基于候选人回答生成连续追问。
- 增加更细致的评分量表和回答对比。
- 支持 PostgreSQL 持久化和更完整的用户认证。
- 增加模型服务商预设与更安全的客户端配置管理。
