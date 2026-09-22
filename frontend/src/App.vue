<script setup>
import { computed, onMounted, ref, watch } from "vue";

const navItems = [
  { id: "dashboard", label: "总览", icon: "⌂" },
  { id: "profile", label: "我的资料", icon: "◌" },
  { id: "question-bank", label: "题库练习", icon: "▤" },
  { id: "job-analysis", label: "岗位分析", icon: "⌁" },
  { id: "records", label: "练习记录", icon: "◷" },
];

const activeView = ref("dashboard");
const file = ref(null);
const jobDescription = ref("");
const loading = ref(false);
const bankLoading = ref(false);
const error = ref("");
const result = ref(null);
const evaluation = ref(null);
const answer = ref("");
const selectedQuestion = ref(null);
const questionBank = ref([]);
const bankCategory = ref("全部");
const configOpen = ref(false);
const profileSaved = ref(false);
const records = ref([]);
const strengthInput = ref("");
const modelConfig = ref({ provider: "demo", base_url: "", api_key: "", model: "gpt-4o-mini", temperature: 0.4 });
const profile = ref({ target_role: "", target_company: "", strengths: [], signature_experience: "", preferred_style: "structured", custom_notes: "" });

const isReady = computed(() => Boolean(file.value && jobDescription.value.trim()));
const apiConfigured = computed(() => modelConfig.value.provider === "demo" || Boolean(modelConfig.value.base_url && modelConfig.value.api_key));
const currentNav = computed(() => navItems.find((item) => item.id === activeView.value));
const categories = computed(() => ["全部", ...new Set(questionBank.value.map((item) => item.category))]);
const profileCompletion = computed(() => {
  const fields = [profile.value.target_role, profile.value.target_company, profile.value.strengths.length, profile.value.signature_experience, profile.value.custom_notes];
  return Math.round((fields.filter(Boolean).length / fields.length) * 100);
});

function loadLocalState() {
  try {
    const savedProfile = JSON.parse(localStorage.getItem("interviewMirrorProfile") || "null");
    const savedConfig = JSON.parse(localStorage.getItem("interviewMirrorModel") || "null");
    const savedRecords = JSON.parse(localStorage.getItem("interviewMirrorRecords") || "[]");
    if (savedProfile) profile.value = savedProfile;
    if (savedConfig) modelConfig.value = savedConfig;
    records.value = savedRecords;
  } catch {
    error.value = "本地配置读取失败，请重新填写。";
  }
}

function saveProfile() {
  localStorage.setItem("interviewMirrorProfile", JSON.stringify(profile.value));
  profileSaved.value = true;
  setTimeout(() => (profileSaved.value = false), 2200);
}

function addStrength() {
  const value = strengthInput.value.trim();
  if (value && !profile.value.strengths.includes(value)) profile.value.strengths.push(value);
  strengthInput.value = "";
}

function removeStrength(strength) {
  profile.value.strengths = profile.value.strengths.filter((item) => item !== strength);
}

function validateFile(selected) {
  error.value = "";
  if (selected.type !== "application/pdf") return (error.value = "请上传 PDF 格式的简历。");
  if (selected.size > 10 * 1024 * 1024) return (error.value = "简历不能超过 10 MB。");
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

function openView(view) {
  activeView.value = view;
  error.value = "";
  if (view === "question-bank" && !questionBank.value.length) loadQuestionBank();
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
  formData.append("resume", file.value);
  formData.append("job_description", jobDescription.value);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  formData.append("profile", JSON.stringify(profile.value));
  try {
    const response = await fetch("/api/interviews/generate", { method: "POST", body: formData });
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

function saveRecord(data) {
  const record = {
    id: data.request_id,
    filename: data.resume_filename,
    score: data.plan.match_score,
    summary: data.plan.match_summary,
    createdAt: new Date().toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }),
  };
  records.value = [record, ...records.value.filter((item) => item.id !== record.id)].slice(0, 8);
  localStorage.setItem("interviewMirrorRecords", JSON.stringify(records.value));
}

function startQuestion(question) {
  selectedQuestion.value = question;
  answer.value = "";
  evaluation.value = null;
  activeView.value = "question-bank";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function evaluateCurrentAnswer() {
  if (!selectedQuestion.value || !answer.value.trim()) return (error.value = "先写下你的回答，再进行评价。");
  loading.value = true;
  error.value = "";
  const formData = new FormData();
  formData.append("question_json", JSON.stringify(selectedQuestion.value));
  formData.append("answer", answer.value);
  formData.append("model_config", JSON.stringify(modelConfig.value));
  try {
    const response = await fetch("/api/interviews/evaluate", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "评价失败。");
    evaluation.value = data.evaluation;
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
  if (!category || category === "全部" || !questionBank.value.length) return loadQuestionBank();
  const response = await fetch(`/api/question-bank?category=${encodeURIComponent(category)}`);
  questionBank.value = await response.json();
});

onMounted(() => {
  loadLocalState();
  loadQuestionBank();
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="openView('dashboard')"><span class="brand-mark">IM</span><span><strong>Interview Mirror</strong><small>AI interview workbench</small></span></a>
      <div class="workspace-label">WORKSPACE</div>
      <nav class="nav-list"><button v-for="item in navItems" :key="item.id" :class="{ active: activeView === item.id }" @click="openView(item.id)"><span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span><b v-if="item.id === 'question-bank' && questionBank.length">{{ questionBank.length }}</b></button></nav>
      <div class="sidebar-spacer" />
      <div class="profile-meter"><div class="meter-head"><span>我的资料</span><strong>{{ profileCompletion }}%</strong></div><div class="meter-track"><i :style="{ width: `${profileCompletion}%` }" /></div><button @click="openView('profile')">{{ profileCompletion === 100 ? "资料已完善" : "完善候选人画像" }} →</button></div>
      <button class="sidebar-settings" @click="configOpen = true">⚙ <span>模型设置</span></button>
    </aside>

    <main class="main-content">
      <header class="topbar"><div><span class="breadcrumb">WORKSPACE /</span><strong>{{ currentNav?.label }}</strong></div><div class="top-actions"><span class="api-status"><i /> {{ modelConfig.provider === "demo" ? "Demo mode" : modelConfig.model }}</span><button class="icon-button" title="清空本次会话" @click="clearSession">↺</button><span class="user-avatar">Y</span></div></header>
      <div class="page-wrap">
        <div v-if="error" class="alert" role="alert"><strong>需要注意</strong><span>{{ error }}</span><button @click="error = ''">×</button></div>

        <section v-if="activeView === 'dashboard'" class="view">
          <div class="page-heading"><div><p class="eyebrow">YOUR INTERVIEW WORKSPACE</p><h1>准备下一场<br /><em>重要的面试。</em></h1><p class="heading-copy">从整理你的候选人画像开始，再用真实问题反复练习。</p></div><div class="heading-stat"><span>最近一次匹配度</span><strong>{{ records[0]?.score || "—" }}<small v-if="records[0]">/ 100</small></strong><button @click="openView(records.length ? 'job-analysis' : 'profile')">{{ records.length ? "查看分析 →" : "开始建立资料 →" }}</button></div></div>
          <div class="dashboard-grid"><article class="dashboard-card next-card"><div class="card-top"><span class="card-eyebrow">NEXT STEP</span><span class="card-index">01</span></div><h2>{{ profileCompletion < 60 ? "先建立你的候选人画像" : "生成一份岗位专属分析" }}</h2><p>{{ profileCompletion < 60 ? "保存你的目标岗位、优势和代表经历，之后每道题都会更像是为你准备的。" : "上传最新简历和目标岗位描述，获取匹配分数、风险点和高概率问题。" }}</p><button class="dark-button" @click="openView(profileCompletion < 60 ? 'profile' : 'job-analysis')">{{ profileCompletion < 60 ? "完善我的资料" : "开始岗位分析" }} <b>→</b></button></article><article class="dashboard-card stats-card"><div class="card-top"><span class="card-eyebrow">PRACTICE OVERVIEW</span><span class="card-icon">◷</span></div><div class="stats-row"><div><strong>{{ records.length }}</strong><span>次岗位分析</span></div><div><strong>{{ questionBank.length || "—" }}</strong><span>道常问题</span></div><div><strong>{{ evaluation?.overall_score || "—" }}</strong><span>最近回答分</span></div></div><div class="thin-rule" /><p>持续练习的价值，不是记住标准答案，而是让你的真实经历变得更有结构。</p></article></div>
          <div class="section-bar"><div><span class="eyebrow">QUICK ACCESS</span><h2>继续你的准备</h2></div><button class="text-button" @click="openView('question-bank')">查看全部题库 →</button></div><div class="quick-grid"><button class="quick-card" @click="openView('profile')"><span>◌</span><strong>我的资料</strong><small>简历之外的你的特色</small></button><button class="quick-card" @click="openView('question-bank')"><span>▤</span><strong>常问题库</strong><small>行为题、技术题、动机题</small></button><button class="quick-card" @click="openView('job-analysis')"><span>⌁</span><strong>岗位分析</strong><small>简历与岗位的匹配反馈</small></button></div>
        </section>

        <section v-else-if="activeView === 'profile'" class="view"><div class="page-heading compact-heading"><div><p class="eyebrow">CANDIDATE PROFILE</p><h1>我的资料</h1><p class="heading-copy">简历是事实，你的特色是让面试官记住你的线索。</p></div><button class="dark-button standalone" @click="saveProfile">{{ profileSaved ? "已保存 ✓" : "保存候选人画像" }}</button></div><div class="profile-layout"><div class="form-sheet"><div class="sheet-section"><div class="section-title"><span>01</span><div><h2>求职目标</h2><p>帮助 AI 理解你希望被如何评价。</p></div></div><div class="form-row"><label>目标岗位<input v-model="profile.target_role" placeholder="例如：高级产品经理" /></label><label>目标公司<input v-model="profile.target_company" placeholder="例如：某互联网公司" /></label></div><label>回答风格<select v-model="profile.preferred_style"><option value="structured">结构清晰，重点突出</option><option value="concise">简洁直接，少铺垫</option><option value="storytelling">故事化表达，更有记忆点</option></select></label></div><div class="sheet-section"><div class="section-title"><span>02</span><div><h2>你想强调的优势</h2><p>这些内容会成为生成题目和反馈时的个性化上下文。</p></div></div><div class="tag-editor"><span v-for="strength in profile.strengths" :key="strength" class="profile-tag">{{ strength }} <button @click="removeStrength(strength)">×</button></span><input v-model="strengthInput" placeholder="输入优势后按 Enter" @keydown.enter.prevent="addStrength" /></div></div><div class="sheet-section"><div class="section-title"><span>03</span><div><h2>代表性经历</h2><p>写下简历里最希望被问到、也最能代表你的故事。</p></div></div><textarea v-model="profile.signature_experience" rows="7" placeholder="例如：我曾从 0 到 1 搭建一个增长实验平台，三个月内将实验周期从两周缩短到三天..." /></div><div class="sheet-section"><div class="section-title"><span>04</span><div><h2>补充说明</h2><p>任何简历上没有，但你希望 AI 了解的内容。</p></div></div><textarea v-model="profile.custom_notes" rows="5" placeholder="比如转行背景、职业空窗、语言偏好、你担心被追问的地方..." /></div></div><aside class="profile-aside"><div class="profile-card"><span class="card-eyebrow">YOUR SIGNAL</span><div class="signal-avatar">{{ profile.target_role ? profile.target_role.slice(0, 1) : "Y" }}</div><h3>{{ profile.target_role || "你的候选人画像" }}</h3><p>{{ profile.target_company || "还没有设置目标公司" }}</p><div class="profile-tags"><span v-for="strength in profile.strengths" :key="strength">{{ strength }}</span><span v-if="!profile.strengths.length">添加你的优势</span></div></div><div class="tip-card"><strong>一个好的特色</strong><p>不是“我学习能力强”，而是一个能被追问、能证明你如何工作的具体信号。</p></div></aside></div></section>

        <section v-else-if="activeView === 'question-bank'" class="view"><div class="page-heading compact-heading"><div><p class="eyebrow">PRACTICE LIBRARY</p><h1>常问题库</h1><p class="heading-copy">先练习通用能力，再用岗位分析做定向追问。</p></div><span class="library-count">{{ questionBank.length }} QUESTIONS</span></div><div v-if="selectedQuestion" class="practice-panel"><div class="practice-head"><div><span class="eyebrow">ANSWER COACH</span><h2>{{ selectedQuestion.question }}</h2><span class="tag">{{ selectedQuestion.category }}</span></div><button class="close-button" @click="selectedQuestion = null; evaluation = null">×</button></div><div class="practice-grid"><div><label class="field-label">你的回答 <span>{{ answer.length }} 字</span></label><textarea v-model="answer" rows="10" placeholder="尽量用一个真实经历回答。可以先写草稿，AI 会从结构、证据和表达三个维度给建议。" /><button class="primary-button" :disabled="loading" @click="evaluateCurrentAnswer"><span>{{ loading ? "正在评价..." : "获得回答反馈" }}</span><b>→</b></button></div><div v-if="!evaluation" class="coach-placeholder"><span>◎</span><p>提交回答后，这里会显示你的得分、优势和下一步建议。</p></div><div v-else class="evaluation-card"><div class="score-line"><div><span>OVERALL SCORE</span><strong>{{ evaluation.overall_score }}</strong><small>/ 100</small></div><div class="score-ring" :style="{ '--score': `${evaluation.overall_score * 3.6}deg` }" /></div><div class="dimension-list"><div v-for="(score, name) in evaluation.dimensions" :key="name"><span>{{ name }}</span><i><b :style="{ width: `${score}%` }" /></i><strong>{{ score }}</strong></div></div><div class="feedback-block"><span>做得好</span><p v-for="item in evaluation.strengths" :key="item">✓ {{ item }}</p></div><div class="feedback-block improvement"><span>下一步改进</span><p v-for="item in evaluation.improvements" :key="item">↗ {{ item }}</p></div><div class="suggested-answer"><span>建议重组方式</span><p>{{ evaluation.suggested_answer }}</p></div></div></div></div><div v-else><div class="filter-row"><div class="filter-tabs"><button v-for="category in categories" :key="category" :class="{ active: bankCategory === category }" @click="bankCategory = category">{{ category }}</button></div><span class="bank-note">选择一道题开始练习和评分</span></div><div v-if="bankLoading" class="loading-state short"><span class="spinner" /></div><div v-else class="bank-grid"><article v-for="question in questionBank" :key="question.id" class="bank-card"><div class="bank-card-top"><span class="tag">{{ question.category }}</span><span class="difficulty">{{ question.difficulty }}</span></div><h3>{{ question.question }}</h3><p>{{ question.intent }}</p><div class="bank-card-footer"><span>{{ question.tips.length }} 个回答提示</span><button class="text-button" @click="startQuestion(question)">开始回答 →</button></div></article></div></div></section>

        <section v-else-if="activeView === 'job-analysis'" class="view"><div class="page-heading compact-heading"><div><p class="eyebrow">RESUME × JOB MATCH</p><h1>岗位分析</h1><p class="heading-copy">让 AI 从你的经历里找出匹配点、风险点，以及面试官会继续追问的地方。</p></div><span class="flow-label">RESUME <b>×</b> JOB <b>→</b> QUESTIONS</span></div><div v-if="!result" class="analysis-start"><div class="analysis-form"><label class="field-label" for="resume">简历文件 <span>PDF / MAX 10 MB</span></label><label class="dropzone" for="resume" @dragover.prevent @drop.prevent="onDrop"><input id="resume" type="file" accept="application/pdf,.pdf" @change="selectFile" /><template v-if="!file"><span class="upload-symbol">↑</span><strong>拖拽简历到这里</strong><small>或点击选择 PDF 文件</small></template><template v-else><span class="file-symbol">PDF</span><strong>{{ file.name }}</strong><small>{{ formatSize(file.size) }} · 已准备好分析</small></template></label><label class="field-label" for="job">目标岗位要求 <span>{{ jobDescription.length }} / 8000</span></label><textarea id="job" v-model="jobDescription" rows="9" maxlength="8000" placeholder="粘贴职位描述、团队介绍或你想重点准备的能力..." /><div class="form-footer"><span>已使用 {{ profile.strengths.length }} 项个人优势</span><button class="link-button" @click="openView('profile')">编辑我的资料 →</button></div><button class="primary-button" :disabled="loading" @click="generate"><span>{{ loading ? "正在分析资料..." : "开始岗位分析" }}</span><b>→</b></button></div><div class="analysis-explainer"><span class="empty-icon">⌁</span><h2>一份分析，三种准备方向</h2><div><strong>匹配度</strong><p>哪些经历与你的目标岗位最相关。</p></div><div><strong>风险点</strong><p>哪些地方可能被面试官继续追问。</p></div><div><strong>练习题</strong><p>从你的简历和岗位要求生成问题。</p></div></div></div><div v-else class="analysis-result"><div class="analysis-summary"><div class="score-block"><span>岗位匹配度</span><strong>{{ result.plan.match_score }}</strong><small>/ 100</small><i><b :style="{ width: `${result.plan.match_score}%` }" /></i></div><div class="summary-copy"><span class="eyebrow">MATCH SUMMARY</span><h2>{{ result.plan.match_summary }}</h2><p>{{ result.plan.candidate_summary }}</p></div><button class="outline-button" @click="result = null">重新分析</button></div><div class="analysis-columns"><div><div class="result-heading"><h2>匹配点</h2><span>{{ result.plan.matching_points.length }} points</span></div><ul class="insight-list positive"><li v-for="point in result.plan.matching_points" :key="point">{{ point }}</li></ul></div><div><div class="result-heading"><h2>风险点</h2><span>{{ result.plan.risk_points.length }} points</span></div><ul class="insight-list caution"><li v-for="point in result.plan.risk_points" :key="point">{{ point }}</li></ul></div></div><div class="questions-heading"><h2>针对这个岗位的问题</h2><span>{{ result.plan.questions.length }} questions</span></div><div class="analysis-question-list"><article v-for="(question, index) in result.plan.questions" :key="question.question" class="analysis-question"><span>{{ String(index + 1).padStart(2, "0") }}</span><div><div class="question-top"><span class="tag">{{ question.category }}</span><span class="difficulty">{{ question.difficulty }}</span></div><h3>{{ question.question }}</h3><p><strong>考察意图：</strong>{{ question.intent }}</p></div><button class="text-button" @click="startQuestion({ ...question, id: `job-${index}`, tips: [] })">去回答 →</button></article></div></div></section>

        <section v-else class="view"><div class="page-heading compact-heading"><div><p class="eyebrow">PRACTICE HISTORY</p><h1>练习记录</h1><p class="heading-copy">把每次练习留下来，看到自己回答方式的变化。</p></div></div><div v-if="!records.length" class="empty-history"><span>◷</span><h2>还没有练习记录</h2><p>完成一次岗位分析后，这里会保存你的匹配结果。</p><button class="dark-button standalone" @click="openView('job-analysis')">开始第一次分析 →</button></div><div v-else class="record-list"><article v-for="record in records" :key="record.id" class="record-row"><div class="record-mark">IM</div><div><span>{{ record.createdAt }} · {{ record.filename }}</span><h3>岗位匹配度 {{ record.score }} / 100</h3><p>{{ record.summary }}</p></div><button class="text-button" @click="openView('job-analysis')">查看 →</button></article></div></section>
      </div>
    </main>

    <div v-if="configOpen" class="modal-backdrop" @click.self="configOpen = false"><section class="modal"><div class="modal-header"><div><p class="eyebrow">MODEL PROVIDER</p><h2>配置你的 AI</h2></div><button class="close-button" @click="configOpen = false">×</button></div><p class="modal-copy">配置只在当前浏览器保存，并随请求发送给后端。后端不会持久化你的 API Key。</p><label class="field-label">模式<select v-model="modelConfig.provider"><option value="demo">Demo（无需 API Key）</option><option value="openai-compatible">OpenAI-compatible API</option></select></label><template v-if="modelConfig.provider === 'openai-compatible'"><label class="field-label">Base URL<input v-model="modelConfig.base_url" placeholder="https://api.openai.com/v1" /></label><label class="field-label">API Key<input v-model="modelConfig.api_key" type="password" placeholder="sk-..." /></label><label class="field-label">模型名称<input v-model="modelConfig.model" placeholder="gpt-4o-mini" /></label></template><div class="modal-actions"><button class="secondary-button" @click="localStorage.setItem('interviewMirrorModel', JSON.stringify(modelConfig)); configOpen = false">保存并关闭</button></div></section></div>
  </div>
</template>
