<script setup>
import { computed, onMounted, ref, watch } from "vue";

const navItems = [
  { id: "dashboard", label: "总览", icon: "⌂" },
  { id: "profile", label: "我的资料", icon: "◌" },
  { id: "question-bank", label: "题库练习", icon: "▤" },
  { id: "job-analysis", label: "岗位分析", icon: "⌁" },
  { id: "resume-builder", label: "简历生成", icon: "▧" },
  { id: "application", label: "网申适配", icon: "□" },
  { id: "records", label: "练习记录", icon: "◷" },
];

const activeView = ref("dashboard");
const file = ref(null);
const jobDescription = ref("");
const applicationRequirements = ref("");
const resumeBuildFile = ref(null);
const resumeBuildLoading = ref(false);
const loading = ref(false);
const bankLoading = ref(false);
const error = ref("");
const result = ref(null);
const applicationResult = ref(null);
const evaluation = ref(null);
const answer = ref("");
const selectedQuestion = ref(null);
const recording = ref(false);
const voiceLoading = ref(false);
const recordingUrl = ref("");
const recordingElapsed = ref(0);
const recordingRemaining = ref(180);
const interviewMode = ref(false);
const interviewQuestions = ref([]);
const interviewIndex = ref(0);
const interviewTurns = ref([]);
const sessionAnalysis = ref(null);
const sessionAnalysisLoading = ref(false);
let mediaRecorder = null;
let recordingChunks = [];
let recordingTimer = null;
const questionBank = ref([]);
const bankCategory = ref("全部");
const configOpen = ref(false);
const sidebarCollapsed = ref(false);
const authMode = ref("login");
const authLoading = ref(false);
const authError = ref("");
const authUser = ref(null);
const authForm = ref({ email: "", password: "" });
const profileSaved = ref(false);
const profileFile = ref(null);
const profileDraft = ref(null);
const profileDocumentId = ref(null);
const profileVersions = ref([]);
const profileLoading = ref(false);
const records = ref([]);
const strengthInput = ref("");
const modelConfig = ref({
  provider: "demo",
  base_url: "",
  api_key: "",
  model: "gpt-4o-mini",
  transcription_model: "whisper-1",
  temperature: 0.4,
});
const profile = ref({
  name: "",
  target_role: "",
  target_company: "",
  strengths: [],
  signature_experience: "",
  preferred_style: "structured",
  custom_notes: "",
});

const isReady = computed(() =>
  Boolean((file.value || profileVersions.value.length) && jobDescription.value.trim()),
);
const apiConfigured = computed(
  () =>
    modelConfig.value.provider === "demo" ||
    Boolean(modelConfig.value.base_url && modelConfig.value.api_key),
);
const currentNav = computed(() =>
  navItems.find((item) => item.id === activeView.value),
);
const categories = computed(() => [
  "全部",
  ...new Set(questionBank.value.map((item) => item.category)),
]);
const profileCompletion = computed(() => {
  const fields = [
    profile.value.target_role,
    profile.value.target_company,
    profile.value.strengths.length,
    profile.value.signature_experience,
    profile.value.custom_notes,
  ];
  return Math.round((fields.filter(Boolean).length / fields.length) * 100);
});
const isAuthenticated = computed(() => Boolean(authUser.value));

function loadLocalState() {
  try {
    const savedProfile = JSON.parse(
      localStorage.getItem("interviewMirrorProfile") || "null",
    );
    const savedConfig = JSON.parse(
      localStorage.getItem("interviewMirrorModel") || "null",
    );
    const savedRecords = JSON.parse(
      localStorage.getItem("interviewMirrorRecords") || "[]",
    );
    if (savedProfile) profile.value = savedProfile;
    if (savedConfig) modelConfig.value = savedConfig;
    records.value = savedRecords;
  } catch {
    error.value = "本地配置读取失败，请重新填写。";
  }
}

async function submitAuth() {
  authLoading.value = true;
  authError.value = "";
  localStorage.setItem(
    "interviewMirrorModel",
    JSON.stringify(modelConfig.value),
  );
  try {
    const response = await fetch(`/api/auth/${authMode.value}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(authForm.value),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "认证失败，请稍后重试。");
    localStorage.setItem("interviewMirrorToken", data.access_token);
    authUser.value = data.user;
    authForm.value.password = "";
    loadQuestionBank();
  } catch (cause) {
    authError.value = cause.message;
  } finally {
    authLoading.value = false;
  }
}

async function restoreAuth() {
  const token = localStorage.getItem("interviewMirrorToken");
  if (!token) return;
  try {
    const response = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("登录状态已失效。");
    authUser.value = await response.json();
  } catch {
    localStorage.removeItem("interviewMirrorToken");
  }
}

function logout() {
  localStorage.removeItem("interviewMirrorToken");
  authUser.value = null;
  activeView.value = "dashboard";
}

function saveProfile() {
  localStorage.setItem("interviewMirrorProfile", JSON.stringify(profile.value));
  profileSaved.value = true;
  setTimeout(() => (profileSaved.value = false), 2200);
}

function authHeaders() {
  const token = localStorage.getItem("interviewMirrorToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function uploadProfileDocument(event) {
  const selected = event.target.files?.[0];
  if (!selected) return;
  const allowed = [".pdf", ".docx"];
  if (!allowed.some((suffix) => selected.name.toLowerCase().endsWith(suffix))) {
    return (error.value = "个人资料只支持 PDF 或 DOCX 文件。");
  }
  if (selected.size > 10 * 1024 * 1024)
    return (error.value = "个人资料不能超过 10 MB。");
  profileLoading.value = true;
  error.value = "";
  const formData = new FormData();
  formData.append("resume", selected);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  try {
    const response = await fetch("/api/profile/drafts", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "资料解析失败。");
    profileFile.value = selected;
    profileDraft.value = data.profile;
    if (!profileDraft.value.education?.length)
      profileDraft.value.education = [{ school: "", degree: "", major: "", period: "" }];
    profileDocumentId.value = data.document_id;
    if (data.profile.basic_info?.name) profile.value.name = data.profile.basic_info.name;
    if (data.profile.target_role) profile.value.target_role = data.profile.target_role;
    if (data.profile.skills?.length) profile.value.strengths = data.profile.skills;
  } catch (cause) {
    error.value = cause.message;
  } finally {
    profileLoading.value = false;
    event.target.value = "";
  }
}

async function saveProfileVersion() {
  if (!profileDraft.value || !profileDocumentId.value)
    return (error.value = "请先上传并解析 PDF 或 DOCX。");
  const merged = {
    ...profileDraft.value,
    target_role: profile.value.target_role,
    basic_info: {
      ...profileDraft.value.basic_info,
      name: profile.value.name || profileDraft.value.basic_info?.name || "",
      age: profileDraft.value.basic_info?.age || null,
    },
  };
  profileLoading.value = true;
  error.value = "";
  try {
    const response = await fetch("/api/profile/versions", {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: profileDocumentId.value,
        profile: merged,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "资料保存失败。");
    profileDraft.value = data.profile;
    profileVersions.value = [data, ...profileVersions.value];
    profileSaved.value = true;
    setTimeout(() => (profileSaved.value = false), 2200);
  } catch (cause) {
    error.value = cause.message;
  } finally {
    profileLoading.value = false;
  }
}

async function loadProfileVersions() {
  try {
    const response = await fetch("/api/profile/versions", {
      headers: authHeaders(),
    });
    if (response.ok) {
      profileVersions.value = await response.json();
      const latest = profileVersions.value[0];
      if (latest?.profile) profileDraft.value = latest.profile;
    }
  } catch {
    error.value = "历史资料加载失败。";
  }
}

function saveModelConfig() {
  localStorage.setItem(
    "interviewMirrorModel",
    JSON.stringify(modelConfig.value),
  );
  configOpen.value = false;
}

function addStrength() {
  const value = strengthInput.value.trim();
  if (value && !profile.value.strengths.includes(value))
    profile.value.strengths.push(value);
  strengthInput.value = "";
}

function removeStrength(strength) {
  profile.value.strengths = profile.value.strengths.filter(
    (item) => item !== strength,
  );
}

function validateFile(selected) {
  error.value = "";
  if (selected.type !== "application/pdf")
    return (error.value = "请上传 PDF 格式的简历。");
  if (selected.size > 10 * 1024 * 1024)
    return (error.value = "简历不能超过 10 MB。");
  file.value = selected;
}

function selectFile(event) {
  const selected = event.target.files?.[0];
  if (selected) validateFile(selected);
}

function onDrop(event) {
  const dropped = event.dataTransfer.files?.[0];
  if (dropped) validateFile(dropped);
}

function formatSize(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function copyText(text) {
  navigator.clipboard?.writeText(text);
}

function openView(view) {
  activeView.value = view;
  error.value = "";
  if (view === "question-bank" && !questionBank.value.length)
    loadQuestionBank();
}

async function loadQuestionBank() {
  bankLoading.value = true;
  try {
    const response = await fetch("/api/question-bank");
    questionBank.value = await response.json();
  } catch {
    error.value = "题库加载失败，请确认后端服务正在运行。";
  } finally {
    bankLoading.value = false;
  }
}

async function generate() {
  if (!isReady.value) return (error.value = "请先上传简历并填写岗位要求。");
  if (!apiConfigured.value) {
    error.value = "在线模型需要填写 Base URL 和 API Key。";
    configOpen.value = true;
    return;
  }
  loading.value = true;
  error.value = "";
  const formData = new FormData();
  if (file.value) formData.append("resume", file.value);
  formData.append("job_description", jobDescription.value);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  formData.append("profile", JSON.stringify(profile.value));
  try {
    const response = await fetch("/api/interviews/generate", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "生成失败，请稍后重试。");
    result.value = data;
    saveRecord(data);
    activeView.value = "job-analysis";
  } catch (cause) {
    error.value = cause.message;
  } finally {
    loading.value = false;
  }
}

async function adaptApplication() {
  if (!isReady.value) return (error.value = "请先上传简历并填写岗位要求。");
  if (!apiConfigured.value) {
    error.value = "在线模型需要填写 Base URL 和 API Key。";
    configOpen.value = true;
    return;
  }

  function selectResumeBuildFile(event) {
    const selected = event.target.files?.[0];
    event.target.value = "";
    if (!selected) return;
    const allowed = [".pdf", ".docx"];
    if (!allowed.some((suffix) => selected.name.toLowerCase().endsWith(suffix))) {
      return (error.value = "简历生成只支持 PDF 或 DOCX 文件。");
    }
    if (selected.size > 10 * 1024 * 1024)
      return (error.value = "简历不能超过 10 MB。");
    error.value = "";
    resumeBuildFile.value = selected;
  }

  async function generateResumeDocument() {
    if (!resumeBuildFile.value && !profileVersions.value.length)
      return (error.value = "请上传原始简历，或先在“我的资料”中保存一个资料版本。");
    if (!jobDescription.value.trim())
      return (error.value = "请先填写目标岗位要求。");
    if (!apiConfigured.value) {
      error.value = "在线模型需要填写 Base URL 和 API Key。";
      configOpen.value = true;
      return;
    }
    resumeBuildLoading.value = true;
    error.value = "";
    const formData = new FormData();
    if (resumeBuildFile.value) formData.append("resume", resumeBuildFile.value);
    formData.append("job_description", jobDescription.value);
    formData.append("model_config", JSON.stringify(modelConfig.value));
    formData.append("profile", JSON.stringify(profile.value));
    try {
      const response = await fetch("/api/resumes/generate", {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "简历生成失败，请稍后重试。");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "岗位定制简历.docx";
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      error.value = cause.message;
    } finally {
      resumeBuildLoading.value = false;
    }
  }
  loading.value = true;
  error.value = "";
  const formData = new FormData();
  if (file.value) formData.append("resume", file.value);
  formData.append("job_description", jobDescription.value);
  formData.append("application_requirements", applicationRequirements.value);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  formData.append("profile", JSON.stringify(profile.value));
  try {
    const response = await fetch("/api/applications/adapt", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.detail || "网申适配失败，请稍后重试。");
    applicationResult.value = data;
  } catch (cause) {
    error.value = cause.message;
  } finally {
    loading.value = false;
  }
}

function saveRecord(data) {
  const record = {
    id: data.request_id,
    filename: data.resume_filename,
    score: data.plan.match_score,
    summary: data.plan.match_summary,
    createdAt: new Date().toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
  records.value = [
    record,
    ...records.value.filter((item) => item.id !== record.id),
  ].slice(0, 8);
  localStorage.setItem("interviewMirrorRecords", JSON.stringify(records.value));
}

function startQuestion(question) {
  selectedQuestion.value = question;
  answer.value = "";
  evaluation.value = null;
  recordingUrl.value = "";
  activeView.value = "question-bank";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function speakQuestion(question = selectedQuestion.value?.question) {
  if (!question || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(question);
  utterance.lang = "zh-CN";
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}

function startPersonalizedInterview() {
  if (!result.value?.plan?.questions?.length)
    return (error.value = "请先完成一次岗位分析，生成你的专属面试题。");
  interviewMode.value = true;
  interviewQuestions.value = result.value.plan.questions;
  interviewIndex.value = 0;
  interviewTurns.value = [];
  sessionAnalysis.value = null;
  startQuestion({ ...interviewQuestions.value[0], id: "personalized-0", tips: [] });
  setTimeout(() => speakQuestion(), 350);
}

async function startRecording() {
  if (
    !navigator.mediaDevices?.getUserMedia ||
    typeof MediaRecorder === "undefined"
  )
    return (error.value =
      "当前浏览器不支持录音，请使用最新版 Chrome 或 Edge。");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordingChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) =>
      event.data.size && recordingChunks.push(event.data);
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(recordingChunks, {
        type: mediaRecorder.mimeType || "audio/webm",
      });
      recordingUrl.value = URL.createObjectURL(blob);
      transcribeRecording(blob);
    };
    mediaRecorder.start();
    recording.value = true;
    recordingElapsed.value = 0;
    recordingRemaining.value = 180;
    recordingTimer = window.setInterval(() => {
      recordingElapsed.value += 1;
      recordingRemaining.value = 180 - recordingElapsed.value;
      if (recordingRemaining.value <= 0) stopRecording();
    }, 1000);
    error.value = "";
  } catch {
    error.value = "无法访问麦克风，请检查浏览器权限。";
  }
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;
  recording.value = false;
  window.clearInterval(recordingTimer);
  recordingTimer = null;
  mediaRecorder.stop();
}

function formatDuration(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const remainder = (seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainder}`;
}

async function transcribeRecording(blob) {
  voiceLoading.value = true;
  error.value = "";
  const formData = new FormData();
  formData.append("audio", blob, "interview-answer.webm");
  formData.append("model_config", JSON.stringify(modelConfig.value));
  try {
    const response = await fetch("/api/interviews/transcribe", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "语音转写失败。");
    answer.value = data.text;
  } catch (cause) {
    error.value = cause.message;
  } finally {
    voiceLoading.value = false;
  }
}

function continueInterview() {
  const followUp = evaluation.value?.follow_up_questions?.[0];
  if (!followUp) return;
  startQuestion({
    id: `follow-up-${Date.now()}`,
    category: "AI 追问",
    question: followUp,
    intent: "根据上一轮回答继续验证经历细节。",
    difficulty: "medium",
    tips: [],
  });
}

function advanceInterview() {
  const nextIndex = interviewIndex.value + 1;
  if (!interviewMode.value || nextIndex >= interviewQuestions.value.length) return finishInterview();
  interviewIndex.value = nextIndex;
  startQuestion({ ...interviewQuestions.value[nextIndex], id: `personalized-${nextIndex}`, tips: [] });
  setTimeout(() => speakQuestion(), 350);
}

async function finishInterview() {
  if (!interviewTurns.value.length) return (error.value = "请至少完成一轮回答后再结束面试。");
  sessionAnalysisLoading.value = true;
  error.value = "";
  const formData = new FormData();
  formData.append("turns_json", JSON.stringify(interviewTurns.value));
  formData.append("model_config", JSON.stringify(modelConfig.value));
  try {
    const response = await fetch("/api/interviews/session-analysis", { method: "POST", headers: authHeaders(), body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "整场面试分析失败。");
    sessionAnalysis.value = data;
    localStorage.setItem("interviewMirrorSession", JSON.stringify({ turns: interviewTurns.value, analysis: data, createdAt: new Date().toISOString() }));
  } catch (cause) {
    error.value = cause.message;
  } finally {
    sessionAnalysisLoading.value = false;
  }
}

async function evaluateCurrentAnswer() {
  if (!selectedQuestion.value || !answer.value.trim())
    return (error.value = "先写下你的回答，再进行评价。");
  loading.value = true;
  error.value = "";
  const formData = new FormData();
  formData.append("question_json", JSON.stringify(selectedQuestion.value));
  formData.append("answer", answer.value);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  try {
    const response = await fetch("/api/interviews/evaluate", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "评价失败。");
    evaluation.value = data.evaluation;
    if (interviewMode.value) {
      interviewTurns.value.push({ question: selectedQuestion.value.question, answer: answer.value, evaluation: data.evaluation });
      localStorage.setItem("interviewMirrorSessionTurns", JSON.stringify(interviewTurns.value));
    }
  } catch (cause) {
    error.value = cause.message;
  } finally {
    loading.value = false;
  }
}

function clearSession() {
  file.value = null;
  jobDescription.value = "";
  result.value = null;
  evaluation.value = null;
  answer.value = "";
  activeView.value = "dashboard";
}

watch(bankCategory, async (category) => {
  if (!category || category === "全部" || !questionBank.value.length)
    return loadQuestionBank();
  const response = await fetch(
    `/api/question-bank?category=${encodeURIComponent(category)}`,
  );
  questionBank.value = await response.json();
});

onMounted(() => {
  loadLocalState();
  restoreAuth().then(() => {
    if (authUser.value) {
      loadQuestionBank();
      loadProfileVersions();
    }
  });
});
</script>

<template>
  <section v-if="!isAuthenticated" class="auth-screen">
    <div class="auth-intro">
      <span class="brand-mark">IM</span>
      <p class="eyebrow">INTERVIEW MIRROR</p>
      <h1>让每一次准备，<em>都更接近理想岗位。</em></h1>
      <p>
        登录后保存你的候选人资料、岗位分析和练习记录。模型配置也会跟随当前浏览器保存。
      </p>
    </div>
    <div class="auth-panel">
      <div class="auth-tabs">
        <button
          :class="{ active: authMode === 'login' }"
          @click="
            authMode = 'login';
            authError = '';
          "
        >
          登录</button
        ><button
          :class="{ active: authMode === 'register' }"
          @click="
            authMode = 'register';
            authError = '';
          "
        >
          注册
        </button>
      </div>
      <h2>{{ authMode === "login" ? "欢迎回来" : "创建你的账号" }}</h2>
      <p class="auth-caption">
        {{
          authMode === "login"
            ? "继续你的面试准备工作。"
            : "先建立账号，之后可以跨设备保存准备记录。"
        }}
      </p>
      <form @submit.prevent="submitAuth">
        <label class="field-label"
          >邮箱<input
            v-model.trim="authForm.email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            required /></label
        ><label class="field-label"
          >密码<input
            v-model="authForm.password"
            :autocomplete="
              authMode === 'login' ? 'current-password' : 'new-password'
            "
            type="password"
            placeholder="至少 8 位字符"
            minlength="8"
            required
        /></label>
        <div class="auth-api">
          <div class="auth-api-head">
            <div>
              <span class="card-eyebrow">MODEL CONFIGURATION</span
              ><strong>登录后使用哪个 AI？</strong>
            </div>
            <span>{{
              modelConfig.provider === "demo" ? "Demo" : "已配置"
            }}</span>
          </div>
          <label class="field-label"
            >模式<select v-model="modelConfig.provider">
              <option value="demo">Demo（无需 API Key）</option>
              <option value="openai-compatible">OpenAI-compatible API</option>
            </select></label
          ><template v-if="modelConfig.provider === 'openai-compatible'"
            ><label class="field-label"
              >Base URL<input
                v-model.trim="modelConfig.base_url"
                placeholder="https://api.openai.com/v1" /></label
            ><label class="field-label"
              >API Key<input
                v-model="modelConfig.api_key"
                type="password"
                placeholder="sk-..." /></label
            ><label class="field-label"
              >模型名称<input
                v-model.trim="modelConfig.model"
                placeholder="gpt-4o-mini" /></label
            ><label class="field-label"
              >语音转写模型<input
                v-model.trim="modelConfig.transcription_model"
                placeholder="whisper-1" /></label
          ></template>
          <p>语音转写需要服务商支持 /audio/transcriptions；DeepSeek 等聊天接口通常不支持。</p>
        </div>
        <p v-if="authError" class="auth-error" role="alert">{{ authError }}</p>
        <button
          class="primary-button auth-submit"
          :disabled="authLoading"
          type="submit"
        >
          <span>{{
            authLoading
              ? "请稍候..."
              : authMode === "login"
                ? "登录并进入工作台"
                : "注册并开始使用"
          }}</span
          ><b>→</b>
        </button>
      </form>
    </div>
  </section>
  <div
    v-else
    class="app-shell"
    :class="{ 'sidebar-collapsed': sidebarCollapsed }"
  >
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="openView('dashboard')"
        ><span class="brand-mark">IM</span
        ><span class="sidebar-copy"
          ><strong>Interview Mirror</strong
          ><small>AI interview workbench</small></span
        ></a
      >
      <div class="workspace-label">WORKSPACE</div>
      <nav class="nav-list">
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: activeView === item.id }"
          :title="sidebarCollapsed ? item.label : undefined"
          @click="openView(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span
          ><span class="sidebar-copy">{{ item.label }}</span
          ><b v-if="item.id === 'question-bank' && questionBank.length">{{
            questionBank.length
          }}</b>
        </button>
      </nav>
      <div class="sidebar-spacer" />
      <div class="profile-meter">
        <div class="meter-head sidebar-copy">
          <span>我的资料</span><strong>{{ profileCompletion }}%</strong>
        </div>
        <div class="meter-track">
          <i :style="{ width: `${profileCompletion}%` }" />
        </div>
        <button class="sidebar-copy" @click="openView('profile')">
          {{ profileCompletion === 100 ? "资料已完善" : "完善候选人画像" }} →
        </button>
      </div>
      <button
        class="sidebar-settings"
        title="模型设置"
        @click="configOpen = true"
      >
        ⚙ <span class="sidebar-copy">模型设置</span>
      </button>
      <button
        class="sidebar-toggle"
        :title="sidebarCollapsed ? '展开菜单' : '折叠菜单'"
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <span>{{ sidebarCollapsed ? "→" : "←" }}</span
        ><span class="sidebar-copy">{{
          sidebarCollapsed ? "展开菜单" : "折叠菜单"
        }}</span>
      </button>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div>
          <span class="breadcrumb">WORKSPACE /</span
          ><strong>{{ currentNav?.label }}</strong>
        </div>
        <div class="top-actions">
          <span class="api-status"
            ><i />
            {{
              modelConfig.provider === "demo" ? "Demo mode" : modelConfig.model
            }}</span
          ><button
            class="icon-button"
            title="清空本次会话"
            @click="clearSession"
          >
            ↺</button
          ><button
            class="user-avatar"
            :title="`退出 ${authUser.email}`"
            @click="logout"
          >
            {{ authUser.email.slice(0, 1).toUpperCase() }}
          </button>
        </div>
      </header>
      <div class="page-wrap">
        <div v-if="error" class="alert" role="alert">
          <strong>需要注意</strong><span>{{ error }}</span
          ><button @click="error = ''">×</button>
        </div>

        <section v-if="activeView === 'dashboard'" class="view">
          <div class="page-heading">
            <div>
              <p class="eyebrow">YOUR INTERVIEW WORKSPACE</p>
              <h1>准备下一场<br /><em>重要的面试。</em></h1>
              <p class="heading-copy">
                从整理你的候选人画像开始，再用真实问题反复练习。
              </p>
            </div>
            <div class="heading-stat">
              <span>最近一次匹配度</span
              ><strong
                >{{ records[0]?.score || "—"
                }}<small v-if="records[0]">/ 100</small></strong
              ><button
                @click="openView(records.length ? 'job-analysis' : 'profile')"
              >
                {{ records.length ? "查看分析 →" : "开始建立资料 →" }}
              </button>
            </div>
          </div>
          <div class="dashboard-grid">
            <article class="dashboard-card next-card">
              <div class="card-top">
                <span class="card-eyebrow">NEXT STEP</span
                ><span class="card-index">01</span>
              </div>
              <h2>
                {{
                  profileCompletion < 60
                    ? "先建立你的候选人画像"
                    : "生成一份岗位专属分析"
                }}
              </h2>
              <p>
                {{
                  profileCompletion < 60
                    ? "保存你的目标岗位、优势和代表经历，之后每道题都会更像是为你准备的。"
                    : "上传最新简历和目标岗位描述，获取匹配分数、风险点和高概率问题。"
                }}
              </p>
              <button
                class="dark-button"
                @click="
                  openView(profileCompletion < 60 ? 'profile' : 'job-analysis')
                "
              >
                {{ profileCompletion < 60 ? "完善我的资料" : "开始岗位分析" }}
                <b>→</b>
              </button>
            </article>
            <article class="dashboard-card stats-card">
              <div class="card-top">
                <span class="card-eyebrow">PRACTICE OVERVIEW</span
                ><span class="card-icon">◷</span>
              </div>
              <div class="stats-row">
                <div>
                  <strong>{{ records.length }}</strong
                  ><span>次岗位分析</span>
                </div>
                <div>
                  <strong>{{ questionBank.length || "—" }}</strong
                  ><span>道常问题</span>
                </div>
                <div>
                  <strong>{{ evaluation?.overall_score || "—" }}</strong
                  ><span>最近回答分</span>
                </div>
              </div>
              <div class="thin-rule" />
              <p>
                持续练习的价值，不是记住标准答案，而是让你的真实经历变得更有结构。
              </p>
            </article>
          </div>
          <div class="section-bar">
            <div>
              <span class="eyebrow">QUICK ACCESS</span>
              <h2>继续你的准备</h2>
            </div>
            <button class="text-button" @click="openView('question-bank')">
              查看全部题库 →
            </button>
          </div>
          <div class="quick-grid">
            <button class="quick-card" @click="openView('profile')">
              <span>◌</span><strong>我的资料</strong
              ><small>简历之外的你的特色</small></button
            ><button class="quick-card" @click="openView('question-bank')">
              <span>▤</span><strong>常问题库</strong
              ><small>行为题、技术题、动机题</small></button
            ><button class="quick-card" @click="openView('job-analysis')">
              <span>⌁</span><strong>岗位分析</strong
              ><small>简历与岗位的匹配反馈</small>
            </button>
          </div>
        </section>

        <section v-else-if="activeView === 'profile'" class="view">
          <div class="page-heading compact-heading profile-page-heading">
            <div>
              <p class="eyebrow">CANDIDATE PROFILE</p>
              <h1>我的资料</h1>
              <p class="heading-copy">
                简历是事实，你的特色是让面试官记住你的线索。
              </p>
            </div>
            <span class="profile-status">{{ profileVersions.length ? `已建立 ${profileVersions.length} 个资料版本` : "尚未建立资料版本" }}</span>
            <button class="dark-button standalone" @click="saveProfile">
              {{ profileSaved ? "已保存 ✓" : "保存候选人画像" }}
            </button>
          </div>
          <div class="profile-layout">
            <div class="form-sheet">
              <div class="sheet-section">
                <div class="section-title">
                  <span>00</span>
                  <div>
                    <h2>从简历建立资料</h2>
                    <p>上传 PDF 或 DOCX，系统会先提取草稿，确认后才保存为历史版本。</p>
                  </div>
                </div>
                <label class="profile-upload-button profile-upload-card">
                  <span class="upload-icon">↑</span>
                  <span>
                    <strong>{{ profileLoading ? "正在解析你的资料..." : "导入一份新的简历" }}</strong>
                    <small>支持 PDF / DOCX · 自动整理教育、项目、经历和技能</small>
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    hidden
                    :disabled="profileLoading"
                    @change="uploadProfileDocument"
                  />
                </label>
                <p v-if="profileFile" class="field-hint">
                  已解析：{{ profileFile.name }}。以下是待确认草稿。
                </p>
                <div v-if="profileDraft" class="profile-draft">
                  <label
                    >姓名<input v-model="profileDraft.basic_info.name" placeholder="请确认姓名"
                  /></label>
                  <label
                    >年龄（简历明确写出时才会填充）<input
                      v-model="profileDraft.basic_info.age"
                      type="number"
                      min="0"
                      max="120"
                      placeholder="可选"
                  /></label>
                  <label
                    >目标岗位<input v-model="profile.target_role" placeholder="例如：高级产品经理"
                  /></label>
                  <label
                    >教育经历（至少保留一条）<textarea
                      v-model="profileDraft.education[0].school"
                      rows="2"
                      placeholder="例如：北京大学｜计算机科学｜硕士"
                  /></label>
                  <div v-if="profileDraft.project_experience?.length">
                    <label>识别到的项目经历</label>
                    <div
                      v-for="(project, index) in profileDraft.project_experience"
                      :key="`project-${index}`"
                      class="profile-entry"
                    >
                      <input v-model="project.title" placeholder="项目名称" />
                      <textarea
                        v-model="project.description"
                        rows="4"
                        placeholder="项目内容、你的职责和结果"
                      />
                    </div>
                  </div>
                  <div v-if="profileDraft.work_experience?.length">
                    <label>识别到的工作经历</label>
                    <div
                      v-for="(job, index) in profileDraft.work_experience"
                      :key="`job-${index}`"
                      class="profile-entry"
                    >
                      <input v-model="job.title" placeholder="公司/职位/时间" />
                      <textarea
                        v-model="job.description"
                        rows="4"
                        placeholder="工作内容和成果"
                      />
                    </div>
                    <div v-if="profileDraft.awards?.length" class="profile-extra">
                      <label>奖项荣誉</label>
                      <p v-for="award in profileDraft.awards" :key="award">· {{ award }}</p>
                    </div>
                    <div v-if="profileDraft.academic_results?.length" class="profile-extra">
                      <label>学术成果</label>
                      <p v-for="item in profileDraft.academic_results" :key="item">· {{ item }}</p>
                    </div>
                  </div>
                  <p class="field-hint">
                    {{ profileDraft.extraction_note }}
                  </p>
                  <button class="dark-button" :disabled="profileLoading" @click="saveProfileVersion">
                    {{ profileLoading ? "保存中..." : "确认并保存为新版本" }}
                  </button>
                </div>
                <div v-if="profileVersions.length" class="profile-history">
                  <strong>历史版本</strong>
                  <span v-for="version in profileVersions" :key="version.id">
                    v{{ version.version_number }} · {{ version.filename }} · {{ version.created_at }}
                  </span>
                </div>
              </div>
              <div class="sheet-section">
                <div class="section-title">
                  <span>01</span>
                  <div>
                    <h2>求职目标</h2>
                    <p>帮助 AI 理解你希望被如何评价。</p>
                  </div>
                </div>
                <div class="form-row">
                  <label
                    >目标岗位<input
                      v-model="profile.target_role"
                      placeholder="例如：高级产品经理" /></label
                  ><label
                    >目标公司<input
                      v-model="profile.target_company"
                      placeholder="例如：某互联网公司"
                  /></label>
                </div>
                <label
                  >回答风格<select v-model="profile.preferred_style">
                    <option value="structured">结构清晰，重点突出</option>
                    <option value="concise">简洁直接，少铺垫</option>
                    <option value="storytelling">故事化表达，更有记忆点</option>
                  </select></label
                >
              </div>
              <div class="sheet-section">
                <div class="section-title">
                  <span>02</span>
                  <div>
                    <h2>你想强调的优势</h2>
                    <p>这些内容会成为生成题目和反馈时的个性化上下文。</p>
                  </div>
                </div>
                <div class="tag-editor">
                  <span
                    v-for="strength in profile.strengths"
                    :key="strength"
                    class="profile-tag"
                    >{{ strength }}
                    <button @click="removeStrength(strength)">×</button></span
                  ><input
                    v-model="strengthInput"
                    placeholder="输入优势后按 Enter"
                    @keydown.enter.prevent="addStrength"
                  />
                </div>
              </div>
              <div class="sheet-section">
                <div class="section-title">
                  <span>03</span>
                  <div>
                    <h2>代表性经历</h2>
                    <p>写下简历里最希望被问到、也最能代表你的故事。</p>
                  </div>
                </div>
                <textarea
                  v-model="profile.signature_experience"
                  rows="7"
                  placeholder="例如：我曾从 0 到 1 搭建一个增长实验平台，三个月内将实验周期从两周缩短到三天..."
                />
              </div>
              <div class="sheet-section">
                <div class="section-title">
                  <span>04</span>
                  <div>
                    <h2>补充说明</h2>
                    <p>任何简历上没有，但你希望 AI 了解的内容。</p>
                  </div>
                </div>
                <textarea
                  v-model="profile.custom_notes"
                  rows="5"
                  placeholder="比如转行背景、职业空窗、语言偏好、你担心被追问的地方..."
                />
              </div>
            </div>
            <aside class="profile-aside">
              <div class="profile-card">
                <span class="card-eyebrow">YOUR SIGNAL</span>
                <div class="signal-avatar">
                  {{
                    profile.target_role ? profile.target_role.slice(0, 1) : "Y"
                  }}
                </div>
                <h3>{{ profile.target_role || "你的候选人画像" }}</h3>
                <p>{{ profile.target_company || "还没有设置目标公司" }}</p>
                <div class="profile-tags">
                  <span v-for="strength in profile.strengths" :key="strength">{{
                    strength
                  }}</span
                  ><span v-if="!profile.strengths.length">添加你的优势</span>
                </div>
              </div>
              <div class="tip-card">
                <strong>一个好的特色</strong>
                <p>
                  不是“我学习能力强”，而是一个能被追问、能证明你如何工作的具体信号。
                </p>
              </div>
            </aside>
          </div>
        </section>

        <section v-else-if="activeView === 'question-bank'" class="view">
          <div class="page-heading compact-heading">
            <div>
              <p class="eyebrow">AI INTERVIEW PRACTICE</p>
              <h1>AI 面试练习</h1>
              <p class="heading-copy">
                通用题库可以单题练习；完成岗位分析后，AI 会结合你的简历和画像连续追问。
              </p>
            </div>
            <div class="practice-actions">
              <button
                v-if="result?.plan?.questions?.length"
                class="dark-button"
                @click="startPersonalizedInterview"
              >
                开始岗位专属面试 →
              </button>
              <span class="library-count"
                >{{ questionBank.length }} QUESTIONS</span
              >
            </div>
          </div>
          <div v-if="selectedQuestion" class="practice-panel">
            <div class="practice-head">
              <div>
                <span class="eyebrow">AI INTERVIEWER</span>
                <h2>{{ selectedQuestion.question }}</h2>
                <span class="tag">{{ selectedQuestion.category }}</span>
                <span v-if="interviewMode" class="interview-progress"
                  >第 {{ interviewIndex + 1 }} / {{ interviewQuestions.length }} 轮</span
                >
              </div>
              <button
                class="close-button"
                @click="
                  selectedQuestion = null;
                  evaluation = null;
                "
              >
                ×
              </button>
              <button class="speak-button" title="朗读问题" @click="speakQuestion()">
                🔊 朗读问题
              </button>
            </div>
            <div class="practice-grid">
              <div>
                <label class="field-label"
                  >你的回答 <span>{{ answer.length }} 字</span></label
                ><textarea
                  v-model="answer"
                  rows="8"
                  placeholder="可以直接录音。AI 会先转写你的回答，再从结构、证据和表达三个维度评分。"
                /><button
                  v-if="!recording"
                  class="secondary-button"
                  :disabled="voiceLoading"
                  @click="startRecording"
                >
                  {{ voiceLoading ? "正在转写..." : "开始录音" }}
                </button><button
                  v-else
                  class="recording-button"
                  @click="stopRecording"
                >
                  <i /> 停止录音 · {{ formatDuration(recordingElapsed) }} · 剩余 {{ formatDuration(recordingRemaining) }}
                </button><audio
                  v-if="recordingUrl"
                  :src="recordingUrl"
                  controls
                /><button
                  class="primary-button"
                  :disabled="loading || voiceLoading"
                  @click="evaluateCurrentAnswer"
                >
                  <span>{{ loading ? "正在评价..." : "获得回答反馈" }}</span
                  ><b>→</b>
                </button>
              </div>
              <div v-if="!evaluation" class="coach-placeholder">
                <span>◎</span>
                <p>提交回答后，这里会显示你的得分、优势和下一步建议。</p>
              </div>
              <div v-else class="evaluation-card">
                <div class="score-line">
                  <div>
                    <span>OVERALL SCORE</span
                    ><strong>{{ evaluation.overall_score }}</strong
                    ><small>/ 100</small>
                  </div>
                  <div
                    class="score-ring"
                    :style="{
                      '--score': `${evaluation.overall_score * 3.6}deg`,
                    }"
                  />
                </div>
                <div class="dimension-list">
                  <div
                    v-for="(score, name) in evaluation.dimensions"
                    :key="name"
                  >
                    <span>{{ name }}</span
                    ><i><b :style="{ width: `${score}%` }" /></i
                    ><strong>{{ score }}</strong>
                  </div>
                </div>
                <div class="feedback-block">
                  <span>做得好</span>
                  <p v-for="item in evaluation.strengths" :key="item">
                    ✓ {{ item }}
                  </p>
                </div>
                <div class="feedback-block improvement">
                  <span>下一步改进</span>
                  <p v-for="item in evaluation.improvements" :key="item">
                    ↗ {{ item }}
                  </p>
                </div>
                <div class="suggested-answer">
                  <span>更好的回答方式</span>
                  <p>{{ evaluation.suggested_answer }}</p>
                </div>
                <button
                  v-if="interviewMode"
                  class="primary-button follow-up-button"
                  @click="advanceInterview"
                >
                  {{ interviewIndex + 1 < interviewQuestions.length ? "下一轮提问 →" : "结束面试并生成总结 →" }}
                </button>
                <button
                  v-else-if="evaluation.follow_up_questions?.length"
                  class="primary-button follow-up-button"
                  @click="continueInterview"
                >
                  继续回答 AI 追问 →
                </button>
              </div>
            </div>
          </div>
          <div v-if="interviewMode && interviewTurns.length" class="interview-transcript">
            <div class="section-title"><span>LIVE LOG</span><div><h2>本场面试留痕</h2><p>每一轮回答都会保存在这里，结束后用于整场针对性分析。</p></div></div>
            <article v-for="(turn, index) in interviewTurns" :key="`${turn.question}-${index}`" class="transcript-turn"><span>0{{ index + 1 }}</span><div><strong>面试官：{{ turn.question }}</strong><p>你的回答：{{ turn.answer }}</p><small>本轮评分 {{ turn.evaluation.overall_score }} / 100</small></div></article>
          </div>
          <div v-if="sessionAnalysis" class="session-analysis"><div class="score-block"><span>SESSION SCORE</span><strong>{{ sessionAnalysis.overall_score }}</strong><small>/ 100</small></div><div><span class="eyebrow">TARGETED REVIEW</span><h2>整场面试分析</h2><p>{{ sessionAnalysis.summary }}</p><div class="analysis-columns"><div><strong>反复体现的优势</strong><p v-for="item in sessionAnalysis.strengths" :key="item">✓ {{ item }}</p></div><div><strong>优先改进</strong><p v-for="item in sessionAnalysis.priorities" :key="item">↗ {{ item }}</p></div><div><strong>下一步训练</strong><p v-for="item in sessionAnalysis.next_practice_plan" :key="item">→ {{ item }}</p></div></div></div></div>
          <div v-else>
            <div class="filter-row">
              <div class="filter-tabs">
                <button
                  v-for="category in categories"
                  :key="category"
                  :class="{ active: bankCategory === category }"
                  @click="bankCategory = category"
                >
                  {{ category }}
                </button>
              </div>
              <span class="bank-note">选择一道题开始练习和评分</span>
            </div>
            <div v-if="bankLoading" class="loading-state short">
              <span class="spinner" />
            </div>
            <div v-else class="bank-grid">
              <article
                v-for="question in questionBank"
                :key="question.id"
                class="bank-card"
              >
                <div class="bank-card-top">
                  <span class="tag">{{ question.category }}</span
                  ><span class="difficulty">{{ question.difficulty }}</span>
                </div>
                <h3>{{ question.question }}</h3>
                <p>{{ question.intent }}</p>
                <div class="bank-card-footer">
                  <span>{{ question.tips.length }} 个回答提示</span
                  ><button class="text-button" @click="startQuestion(question)">
                    开始回答 →
                  </button>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section v-else-if="activeView === 'job-analysis'" class="view">
          <div class="page-heading compact-heading">
            <div>
              <p class="eyebrow">RESUME × JOB MATCH</p>
              <h1>岗位分析</h1>
              <p class="heading-copy">
                让 AI
                从你的经历里找出匹配点、风险点，以及面试官会继续追问的地方。
              </p>
            </div>
            <span class="flow-label"
              >RESUME <b>×</b> JOB <b>→</b> QUESTIONS</span
            >
          </div>
          <div v-if="!result" class="analysis-start">
            <div class="analysis-form">
              <label class="field-label" for="resume"
                >简历文件 <span>可选：使用“我的资料”最新版本</span></label
              ><label
                class="dropzone"
                for="resume"
                @dragover.prevent
                @drop.prevent="onDrop"
                ><input
                  id="resume"
                  type="file"
                  accept="application/pdf,.pdf"
                  @change="selectFile"
                /><template v-if="!file"
                  ><span class="upload-symbol">↑</span
                  ><strong>拖拽简历到这里</strong
                  ><small>或点击选择 PDF 文件；不上传则使用我的资料</small></template
                ><template v-else
                  ><span class="file-symbol">PDF</span
                  ><strong>{{ file.name }}</strong
                  ><small
                    >{{ formatSize(file.size) }} · 已准备好分析</small
                  ></template
                ></label
              ><label class="field-label" for="job"
                >目标岗位要求
                <span>{{ jobDescription.length }} / 8000</span></label
              ><textarea
                id="job"
                v-model="jobDescription"
                rows="9"
                maxlength="8000"
                placeholder="粘贴职位描述、团队介绍或你想重点准备的能力..."
              />
              <div class="form-footer">
                <span>{{
                  file ? "本次使用新上传简历" : "将使用我的资料最新版本"
                }}</span
                ><button class="link-button" @click="openView('profile')">
                  编辑我的资料 →
                </button>
              </div>
              <button
                class="primary-button"
                :disabled="loading"
                @click="generate"
              >
                <span>{{ loading ? "正在分析资料..." : "开始岗位分析" }}</span
                ><b>→</b>
              </button>
            </div>
            <div class="analysis-explainer">
              <span class="empty-icon">⌁</span>
              <h2>一份分析，三种准备方向</h2>
              <div>
                <strong>匹配度</strong>
                <p>哪些经历与你的目标岗位最相关。</p>
              </div>
              <div>
                <strong>风险点</strong>
                <p>哪些地方可能被面试官继续追问。</p>
              </div>
              <div>
                <strong>练习题</strong>
                <p>从你的简历和岗位要求生成问题。</p>
              </div>
            </div>
          </div>
          <div v-else class="analysis-result">
            <div class="analysis-summary">
              <div class="score-block">
                <span>岗位匹配度</span
                ><strong>{{ result.plan.match_score }}</strong
                ><small>/ 100</small
                ><i><b :style="{ width: `${result.plan.match_score}%` }" /></i>
              </div>
              <div class="summary-copy">
                <span class="eyebrow">MATCH SUMMARY</span>
                <h2>{{ result.plan.match_summary }}</h2>
                <p>{{ result.plan.candidate_summary }}</p>
              </div>
              <button class="outline-button" @click="result = null">
                重新分析
              </button>
            </div>
            <div class="analysis-columns">
              <div>
                <div class="result-heading">
                  <h2>匹配点</h2>
                  <span>{{ result.plan.matching_points.length }} points</span>
                </div>
                <ul class="insight-list positive">
                  <li v-for="point in result.plan.matching_points" :key="point">
                    {{ point }}
                  </li>
                </ul>
              </div>
              <div>
                <div class="result-heading">
                  <h2>风险点</h2>
                  <span>{{ result.plan.risk_points.length }} points</span>
                </div>
                <ul class="insight-list caution">
                  <li v-for="point in result.plan.risk_points" :key="point">
                    {{ point }}
                  </li>
                </ul>
              </div>
            </div>
            <div class="questions-heading">
              <h2>针对这个岗位的问题</h2>
              <div class="questions-heading-actions"><span>{{ result.plan.questions.length }} questions</span><button class="dark-button" @click="startPersonalizedInterview">开始语音面试 →</button></div>
            </div>
            <div class="analysis-question-list">
              <article
                v-for="(question, index) in result.plan.questions"
                :key="question.question"
                class="analysis-question"
              >
                <span>{{ String(index + 1).padStart(2, "0") }}</span>
                <div>
                  <div class="question-top">
                    <span class="tag">{{ question.category }}</span
                    ><span class="difficulty">{{ question.difficulty }}</span>
                  </div>
                  <h3>{{ question.question }}</h3>
                  <p><strong>考察意图：</strong>{{ question.intent }}</p>
                  <p v-if="question.resume_evidence">
                    <strong>简历依据：</strong>{{ question.resume_evidence }}
                  </p>
                  <p v-if="question.job_requirement">
                    <strong>岗位依据：</strong>{{ question.job_requirement }}
                  </p>
                  <p v-if="question.follow_up_points?.length">
                    <strong>可能追问：</strong>{{ question.follow_up_points.join("、") }}
                  </p>
                </div>
                <button
                  class="text-button"
                  @click="
                    startQuestion({ ...question, id: `job-${index}`, tips: [] })
                  "
                >
                  去回答 →
                </button>
              </article>
            </div>
          </div>
        </section>

        <section v-else-if="activeView === 'resume-builder'" class="view">
          <div class="page-heading compact-heading">
            <div>
              <p class="eyebrow">RESUME BUILDER</p>
              <h1>简历生成</h1>
              <p class="heading-copy">
                基于你的原始简历和目标岗位，突出更相关的经历，生成可继续编辑的 DOCX 文档。
              </p>
            </div>
            <span class="flow-label">ORIGINAL <b>→</b> TAILORED RESUME</span>
          </div>
          <div class="analysis-start">
            <div class="analysis-form">
              <div class="adapter-callout">
                <strong>保留事实，只调整表达重点</strong>
                <p>
                  AI 会基于原始简历进行岗位定制，不会凭空添加经历、公司、数字或技能。生成后请打开文档再次核对。
                </p>
              </div>
              <label class="field-label" for="resume-builder-file"
                >原始简历 <span>PDF / DOCX · MAX 10 MB</span></label
              >
              <label class="resume-builder-upload">
                <input
                  id="resume-builder-file"
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  @change="selectResumeBuildFile"
                />
                <span class="upload-symbol">↑</span>
                <strong>{{ resumeBuildFile?.name || "点击选择原始简历" }}</strong>
                <small>{{
                  resumeBuildFile
                    ? "文件已准备好生成"
                    : profileVersions.length
                      ? "未上传时将使用“我的资料”中的最新版本"
                      : "请上传 PDF 或 DOCX 文件"
                }}</small>
              </label>
              <label class="field-label" for="resume-builder-job"
                >目标岗位要求
                <span>{{ jobDescription.length }} / 8000</span></label
              >
              <textarea
                id="resume-builder-job"
                v-model="jobDescription"
                rows="9"
                maxlength="8000"
                placeholder="粘贴职位描述、任职要求和岗位关键词..."
              />
              <div class="form-footer">
                <span>输出格式：可编辑 DOCX 文档</span>
                <button class="link-button" @click="openView('profile')">
                  编辑我的资料 →
                </button>
              </div>
              <button
                class="primary-button"
                :disabled="resumeBuildLoading"
                @click="generateResumeDocument"
              >
                <span>{{
                  resumeBuildLoading ? "正在生成简历..." : "生成岗位定制简历"
                }}</span
                ><b>↓</b>
              </button>
            </div>
            <div class="analysis-explainer application-explainer">
              <span class="empty-icon">▧</span>
              <h2>生成后的文档会包含</h2>
              <div>
                <strong>岗位定制简介</strong>
                <p>将与目标岗位最相关的能力放在更显眼的位置。</p>
              </div>
              <div>
                <strong>经历要点</strong>
                <p>在原有事实基础上调整顺序和表达，突出行动与结果。</p>
              </div>
              <div>
                <strong>原始内容</strong>
                <p>保留原简历文本作为核对依据，生成后可以继续编辑排版。</p>
              </div>
            </div>
          </div>
        </section>
        <section v-else-if="activeView === 'application'" class="view">
          <div class="page-heading compact-heading">
            <div>
              <p class="eyebrow">APPLICATION ADAPTER</p>
              <h1>网申适配</h1>
              <p class="heading-copy">
                根据岗位目标重新组织你的真实经历，让每一份申请材料都更贴近岗位。
              </p>
            </div>
            <span class="flow-label"
              >FACTS <b>→</b> POSITIONING <b>→</b> APPLICATION</span
            >
          </div>
          <div v-if="!applicationResult" class="analysis-start">
            <div class="analysis-form">
              <div class="adapter-callout">
                <strong>同一份简历，不同的表达重点</strong>
                <p>
                  AI
                  会根据岗位要求调整个人简介、经历要点和开放题回答。不会自动添加简历中不存在的事实。
                </p>
              </div>
              <div class="application-form-heading">
                <span class="section-kicker">01</span>
                <div>
                  <strong>基础信息</strong>
                  <p>提供简历和目标岗位，帮助 AI 判断你的匹配重点。</p>
                </div>
              </div>
              <label class="field-label" for="application-resume"
                >简历文件 <span>PDF / MAX 10 MB</span></label
              ><label
                class="dropzone"
                for="application-resume"
                @dragover.prevent
                @drop.prevent="onDrop"
                ><input
                  id="application-resume"
                  type="file"
                  accept="application/pdf,.pdf"
                  @change="selectFile"
                /><template v-if="!file && !profileVersions.length"
                  ><span class="upload-symbol">↑</span
                  ><strong>拖拽简历到这里</strong
                  ><small>或点击选择 PDF 文件</small></template
                ><template v-else-if="!file"
                  ><span class="file-symbol profile-file-symbol">IM</span
                  ><strong>使用“我的资料”中的最近版本</strong
                  ><small>已保存 {{ profileVersions.length }} 个版本 · 无需重复上传</small></template
                ><template v-else
                  ><span class="file-symbol">PDF</span
                  ><strong>{{ file.name }}</strong
                  ><small
                    >{{ formatSize(file.size) }} · 已准备好分析</small
                  ></template
                ></label
              ><label class="field-label" for="application-job"
                >目标岗位要求
                <span>{{ jobDescription.length }} / 8000</span></label
              ><textarea
                id="application-job"
                v-model="jobDescription"
                rows="9"
                maxlength="8000"
                placeholder="粘贴职位描述、申请表问题或岗位关键词..."
              />
              <div class="application-input-section">
                <div class="application-section-heading">
                  <div>
                    <span class="section-kicker">02</span>
                    <strong>申请表问题与填写要求</strong>
                  </div>
                  <span>可选 · 支持自由填写</span>
                </div>
                <p class="application-input-hint">
                  把网申中的个人评价、自我介绍、求职动机等问题粘贴到这里；每道题后补充字数限制、语气或格式要求，AI 会逐项生成。
                </p>
                <textarea
                  id="application-requirements"
                  v-model="applicationRequirements"
                  rows="7"
                  maxlength="12000"
                  placeholder="例如：
1. 请做一个自我介绍，300 字以内，突出与岗位相关的经历。
2. 个人评价，150 字以内，语气真诚简洁。
3. 为什么想申请这个岗位？限 500 字。"
                />
                <div class="application-input-footer">
                  <span>示例：题目 + 字数上限 + 语气/格式要求</span>
                  <span>{{ applicationRequirements.length }} / 12000</span>
                </div>
              </div>
              <div class="application-input-section application-output-note">
                <div class="application-section-heading">
                  <div>
                    <span class="section-kicker">03</span>
                    <strong>生成内容</strong>
                  </div>
                </div>
                <p class="application-input-hint">
                  将生成个人简介、求职动机、经历要点，以及你在上方填写的申请题目答案；未填写申请题目时，会使用常见开放题作为参考。
                </p>
              </div>
              <div class="form-footer">
                <span>已使用 {{ profile.strengths.length }} 项个人优势</span
                ><button class="link-button" @click="openView('profile')">
                  编辑我的资料 →
                </button>
              </div>
              <button
                class="primary-button"
                :disabled="loading"
                @click="adaptApplication"
              >
                <span>{{
                  loading ? "正在调整申请材料..." : "生成网申适配包"
                }}</span
                ><b>→</b>
              </button>
            </div>
            <div class="analysis-explainer application-explainer">
              <span class="empty-icon">□</span>
              <h2>帮你完成网申里的关键输入</h2>
              <div>
                <strong>个人简介</strong>
                <p>结合岗位关键词，生成可直接修改的候选人简介。</p>
              </div>
              <div>
                <strong>经历要点</strong>
                <p>把最相关的项目放在前面，强化结果和个人贡献。</p>
              </div>
              <div>
                <strong>开放问题</strong>
                <p>准备求职动机、优势等常见申请表回答。</p>
              </div>
            </div>
          </div>
          <div v-else class="adaptation-result">
            <div class="adaptation-header">
              <div>
                <span class="eyebrow"
                  >TAILORED FOR
                  {{
                    applicationResult.adaptation.target_role.toUpperCase()
                  }}</span
                >
                <h2>{{ applicationResult.adaptation.positioning }}</h2>
              </div>
              <button class="outline-button" @click="applicationResult = null">
                重新适配
              </button>
            </div>
            <div class="keyword-row">
              <span
                v-for="keyword in applicationResult.adaptation.keywords"
                :key="keyword"
                >{{ keyword }}</span
              >
            </div>
            <div class="adaptation-grid">
              <article class="adaptation-card wide">
                <div class="result-heading">
                  <h2>岗位定制个人简介</h2>
                  <button
                    class="text-button"
                    @click="
                      copyText(applicationResult.adaptation.profile_summary)
                    "
                  >
                    复制
                  </button>
                </div>
                <p class="copy-block">
                  {{ applicationResult.adaptation.profile_summary }}
                </p>
              </article>
              <article class="adaptation-card">
                <h2>求职动机</h2>
                <p class="copy-block">
                  {{ applicationResult.adaptation.motivation_answer }}
                </p>
              </article>
              <article class="adaptation-card wide">
                <h2>经历要点改写</h2>
                <div class="bullet-list">
                  <p
                    v-for="bullet in applicationResult.adaptation
                      .tailored_bullets"
                    :key="bullet"
                  >
                    ＋ {{ bullet }}
                  </p>
                </div>
              </article>
              <article class="adaptation-card wide">
                <h2>网申常见开放题</h2>
                <div class="application-answers">
                  <div
                    v-for="item in applicationResult.adaptation
                      .application_questions"
                    :key="item.question"
                  >
                    <strong>{{ item.question }}</strong>
                    <p>{{ item.answer }}</p>
                  </div>
                </div>
              </article>
            </div>
            <div class="caution-box">
              <strong>提交前请核对</strong>
              <p
                v-for="caution in applicationResult.adaptation.cautions"
                :key="caution"
              >
                ! {{ caution }}
              </p>
            </div>
          </div>
        </section>

        <section v-else class="view">
          <div class="page-heading compact-heading">
            <div>
              <p class="eyebrow">PRACTICE HISTORY</p>
              <h1>练习记录</h1>
              <p class="heading-copy">
                把每次练习留下来，看到自己回答方式的变化。
              </p>
            </div>
          </div>
          <div v-if="!records.length" class="empty-history">
            <span>◷</span>
            <h2>还没有练习记录</h2>
            <p>完成一次岗位分析后，这里会保存你的匹配结果。</p>
            <button
              class="dark-button standalone"
              @click="openView('job-analysis')"
            >
              开始第一次分析 →
            </button>
          </div>
          <div v-else class="record-list">
            <article
              v-for="record in records"
              :key="record.id"
              class="record-row"
            >
              <div class="record-mark">IM</div>
              <div>
                <span>{{ record.createdAt }} · {{ record.filename }}</span>
                <h3>岗位匹配度 {{ record.score }} / 100</h3>
                <p>{{ record.summary }}</p>
              </div>
              <button class="text-button" @click="openView('job-analysis')">
                查看 →
              </button>
            </article>
          </div>
        </section>
      </div>
    </main>

    <div
      v-if="configOpen"
      class="modal-backdrop"
      @click.self="configOpen = false"
    >
      <section class="modal">
        <div class="modal-header">
          <div>
            <p class="eyebrow">MODEL PROVIDER</p>
            <h2>配置你的 AI</h2>
          </div>
          <button class="close-button" @click="configOpen = false">×</button>
        </div>
        <p class="modal-copy">
          配置只在当前浏览器保存，并随请求发送给后端。后端不会持久化你的 API
          Key。
        </p>
        <label class="field-label"
          >模式<select v-model="modelConfig.provider">
            <option value="demo">Demo（无需 API Key）</option>
            <option value="openai-compatible">OpenAI-compatible API</option>
          </select></label
        ><template v-if="modelConfig.provider === 'openai-compatible'"
          ><label class="field-label"
            >Base URL<input
              v-model="modelConfig.base_url"
              placeholder="https://api.openai.com/v1" /></label
            ><label class="field-label"
              >语音转写模型<input
                v-model="modelConfig.transcription_model"
                placeholder="whisper-1" /></label
          ><label class="field-label"
            >API Key<input
              v-model="modelConfig.api_key"
              type="password"
              placeholder="sk-..." /></label
          ><label class="field-label"
            >模型名称<input
              v-model="modelConfig.model"
              placeholder="gpt-4o-mini" /></label
        ></template>
        <div class="modal-actions">
          <button class="secondary-button" @click="saveModelConfig">
            保存并关闭
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
