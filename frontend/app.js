// O'zbekTil AI - frontend mantiqi (MVP)
const BASE_URL = "http://localhost:8000";
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ============ AUTENTIFIKATSIYA ============
const AUTH_TOKEN_KEY = "ozbektil_token";
const AUTH_USER_KEY = "ozbektil_user";

function getToken() { return localStorage.getItem(AUTH_TOKEN_KEY); }
function getStoredUser() {
  try { return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null"); } catch { return null; }
}
function setSession(token, user) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}
function clearSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(BASE_URL + path, {
    ...options,
    headers,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const message = data && data.detail ? (data.detail.message || JSON.stringify(data.detail)) : "Server xatosi";
    const err = new Error(message);
    err.data = data;
    throw err;
  }
  return data;
}

const authWidget = document.getElementById("auth-widget");
const profileTab = document.getElementById("profile-tab");

function renderAuthWidget() {
  const user = getStoredUser();
  if (!user) {
    authWidget.innerHTML = `
      <button class="auth-link" id="open-login">Kirish</button>
      <button class="btn-ghost-sm" id="open-register">Ro‘yxatdan o‘tish</button>
    `;
    document.getElementById("open-login").addEventListener("click", () => openModal("login"));
    document.getElementById("open-register").addEventListener("click", () => openModal("register"));
    profileTab.hidden = true;
  } else {
    authWidget.innerHTML = `
      <div class="user-chip">
        <span class="user-name">👋 ${escapeHtml(user.username)}</span>
        ${user.is_admin ? '<a href="admin.html">Admin panel</a>' : ""}
        <button id="logout-btn">Chiqish</button>
      </div>
    `;
    document.getElementById("logout-btn").addEventListener("click", () => {
      clearSession();
      renderAuthWidget();
      document.querySelector('.tab[data-tab="check"]').click();
    });
    profileTab.hidden = false;
  }
}
renderAuthWidget();

// ---- Modal boshqaruvi ----
const modals = {
  login: document.getElementById("login-modal"),
  register: document.getElementById("register-modal"),
};

function openModal(name) {
  Object.values(modals).forEach((m) => { m.hidden = true; });
  modals[name].hidden = false;
  modals[name].querySelector("input").focus();
}
function closeModals() {
  Object.values(modals).forEach((m) => { m.hidden = true; });
}
document.querySelectorAll("[data-close-modal]").forEach((btn) => {
  btn.addEventListener("click", closeModals);
});
document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeModals(); });
});
document.querySelectorAll("[data-switch-to]").forEach((btn) => {
  btn.addEventListener("click", () => openModal(btn.dataset.switchTo));
});

// ---- Kirish formasi ----
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.hidden = true;
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  const btn = document.getElementById("login-submit");
  btn.disabled = true;
  btn.textContent = "Kirilmoqda...";
  try {
    const data = await apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    setSession(data.token, data.user);
    renderAuthWidget();
    closeModals();
    loginForm.reset();
  } catch (err) {
    loginError.textContent = err.message;
    loginError.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Kirish";
  }
});

// ---- Ro'yxatdan o'tish formasi ----
const registerForm = document.getElementById("register-form");
const registerError = document.getElementById("register-error");
registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  registerError.hidden = true;
  const username = document.getElementById("register-username").value.trim();
  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;
  const btn = document.getElementById("register-submit");
  btn.disabled = true;
  btn.textContent = "Yuborilmoqda...";
  try {
    const data = await apiRequest("/api/auth/register", { method: "POST", body: JSON.stringify({ username, email, password }) });
    setSession(data.token, data.user);
    renderAuthWidget();
    closeModals();
    registerForm.reset();
  } catch (err) {
    registerError.textContent = err.message;
    registerError.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Ro‘yxatdan o‘tish";
  }
});

// ---- Footer yili ----
document.getElementById("footer-year").textContent = new Date().getFullYear();

// ============ HERO: JONLI NAMOYISH ============
const demoEl = document.getElementById("demo-text");

const DEMO_STEPS = [
  { text: "Men bugun ", wrong: "universtitetga", correct: "universitetga", tail: " bordim." },
  { text: "Bu kitob ", wrong: "juda juda", correct: "juda", tail: " qiziqarli." },
  { text: "Men kecha universitetga ", wrong: "boradi", correct: "bordi", tail: "." },
];

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function typeText(prefix, word, isWrong) {
  for (let i = 1; i <= word.length; i++) {
    demoEl.innerHTML = prefix + `<span class="${isWrong ? "strike" : "fix"}">${escapeHtml(word.slice(0, i))}</span><span class="demo-cursor"></span>`;
    await sleep(28);
  }
}

async function runDemoStep(step) {
  const prefixHtml = escapeHtml(step.text);
  demoEl.innerHTML = prefixHtml + '<span class="demo-cursor"></span>';
  await sleep(300);
  await typeText(prefixHtml, step.wrong, true);
  await sleep(650);
  const struck = `${prefixHtml}<span class="strike">${escapeHtml(step.wrong)}</span> → `;
  demoEl.innerHTML = struck + '<span class="demo-cursor"></span>';
  await sleep(200);
  for (let i = 1; i <= step.correct.length; i++) {
    demoEl.innerHTML = struck + `<span class="fix">${escapeHtml(step.correct.slice(0, i))}</span><span class="demo-cursor"></span>`;
    await sleep(35);
  }
  demoEl.innerHTML = `${prefixHtml}<span class="strike">${escapeHtml(step.wrong)}</span> → <span class="fix">${escapeHtml(step.correct)}</span>${escapeHtml(step.tail)}`;
  await sleep(2200);
}

async function runDemoLoop() {
  if (prefersReducedMotion) {
    const step = DEMO_STEPS[0];
    demoEl.innerHTML = `${escapeHtml(step.text)}<span class="strike">${escapeHtml(step.wrong)}</span> → <span class="fix">${escapeHtml(step.correct)}</span>${escapeHtml(step.tail)}`;
    return;
  }
  // eslint-disable-next-line no-constant-condition
  while (true) {
    for (const step of DEMO_STEPS) {
      await runDemoStep(step);
      demoEl.innerHTML = "&nbsp;";
      await sleep(250);
    }
  }
}
runDemoLoop();

document.getElementById("hero-cta").addEventListener("click", () => {
  document.querySelector('.tab[data-tab="check"]').click();
  document.getElementById("check-input").scrollIntoView({ behavior: "smooth", block: "center" });
});

// ============ TABLAR ============
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
    if (tab.dataset.tab === "profile") loadProfile();
  });
});

// ============ PROFIL / NATIJALAR ============
async function loadProfile() {
  const box = document.getElementById("profile-result");
  box.innerHTML = '<p class="panel-lede">Yuklanmoqda...</p>';
  try {
    const results = await apiRequest("/api/me/quiz-results");
    if (!results.length) {
      box.innerHTML = '<p class="panel-lede">Hali test topshirmadingiz. "Test" bo‘limiga o‘ting va bilimingizni sinang.</p>';
      return;
    }
    const bestPercent = Math.max(...results.map((r) => r.percent));
    const avgPercent = Math.round(results.reduce((s, r) => s + r.percent, 0) / results.length);
    let html = `<div class="profile-summary">
      <div class="profile-stat"><div class="stat-value">${results.length}</div><div class="stat-label">URINISH</div></div>
      <div class="profile-stat"><div class="stat-value">${avgPercent}%</div><div class="stat-label">O‘RTACHA</div></div>
      <div class="profile-stat"><div class="stat-value">${bestPercent}%</div><div class="stat-label">ENG YAXSHI</div></div>
    </div>`;
    results.forEach((r) => {
      const date = new Date(r.created_at).toLocaleDateString("uz-UZ", { year: "numeric", month: "long", day: "numeric" });
      html += `<div class="attempt-row"><span class="attempt-date">${date}</span><span class="attempt-score">${r.score}/${r.total} (${r.percent}%)</span></div>`;
    });
    box.innerHTML = html;
  } catch (e) {
    box.innerHTML = `<p class="error-message">Natijalarni yuklab bo‘lmadi: ${escapeHtml(e.message)}</p>`;
  }
}

// ============ MATN TEKSHIRISH ============
const checkBtn = document.getElementById("check-btn");
const checkInput = document.getElementById("check-input");
const checkResult = document.getElementById("check-result");

function fallbackLocalCheck(text) {
  const replacements = [
    ["universtitetga", "universitetga"],
    ["boradi", "bordi"],
    ["bormoqchi", "bormoqchi"],
    ["juda juda", "juda"],
    ["hammasi hammasi", "hammasi"],
    ["teztez", "tez-tez"],
    ["o'zi o'zi", "o'zi"],
    ["qilib", "qilib"],
  ];

  let corrected = text;
  const spellingErrors = [];

  replacements.forEach(([wrong, right]) => {
    const regex = new RegExp(`\\b${wrong.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "gi");
    if (regex.test(corrected)) {
      corrected = corrected.replace(regex, right);
      spellingErrors.push({
        wrong,
        correct: right,
        explanation: "Keng tarqalgan imlo xatosi",
        position: 0,
      });
    }
  });

  const grammarErrors = [];
  const styleErrors = [];
  if (/\b(kecha|ertaga|bugun)\b/i.test(text) && /\bboradi\b/i.test(text)) {
    grammarErrors.push({
      issue: "Fe’l zamoni mos kelmayapti.",
      suggestion: "Vaqt ko‘rsatkichi bilan mos keladigan shakl ishlating."
    });
  }

  if (/\b(\w+)\s+\1\b/i.test(text)) {
    styleErrors.push({
      issue: "Takroriy so‘zlar uchraryapti.",
      suggestion: "Takrorni bitta holda qoldiring."
    });
  }

  return {
    original_text: text,
    corrected_text: corrected,
    spelling_errors: spellingErrors,
    grammar_errors: grammarErrors,
    style_errors: styleErrors,
    total_errors: spellingErrors.length + grammarErrors.length + styleErrors.length,
  };
}

checkBtn.addEventListener("click", async () => {
  const text = checkInput.value.trim();
  checkResult.hidden = false;
  if (!text) {
    checkResult.innerHTML = '<p class="error-message">Iltimos, matn kiriting.</p>';
    return;
  }
  checkBtn.disabled = true;
  checkBtn.textContent = "Tekshirilmoqda...";
  try {
    const data = await apiRequest("/api/check-text", { method: "POST", body: JSON.stringify({ text }) });
    renderCheckResult(data);
  } catch (e) {
    const fallbackData = fallbackLocalCheck(text);
    renderCheckResult(fallbackData);
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = "Tekshirish";
  }
});

function renderCheckResult(data) {
  const styleErrors = data.style_errors || [];
  const allErrors = [...data.spelling_errors, ...data.grammar_errors, ...styleErrors];
  let html = `<div class="corrected-text">${escapeHtml(data.corrected_text)}</div>`;

  if (allErrors.length === 0) {
    html += '<p class="no-errors">✅ Xato topilmadi. Ajoyib!</p>';
    checkResult.innerHTML = html;
    return;
  }

  html += `<div class="error-summary">
    ${data.spelling_errors.length ? `<span class="error-count imlo">Imlo: ${data.spelling_errors.length}</span>` : ""}
    ${data.grammar_errors.length ? `<span class="error-count grammatika">Grammatika: ${data.grammar_errors.length}</span>` : ""}
    ${styleErrors.length ? `<span class="error-count uslub">Uslub: ${styleErrors.length}</span>` : ""}
  </div>`;

  data.spelling_errors.forEach((err) => {
    html += `
      <div class="error-item">
        <span class="error-tag imlo">imlo</span>
        <div class="error-detail">
          <span class="wrong">${escapeHtml(err.wrong)}</span>
          <span class="arrow">→</span>
          <span class="correct">${escapeHtml(err.correct)}</span>
          <span class="explanation">${escapeHtml(err.explanation)}</span>
        </div>
      </div>`;
  });
  data.grammar_errors.forEach((err) => {
    html += `
      <div class="error-item">
        <span class="error-tag grammatika">grammatika</span>
        <div class="error-detail"><span class="explanation">${escapeHtml(err.issue)} ${escapeHtml(err.suggestion)}</span></div>
      </div>`;
  });
  styleErrors.forEach((err) => {
    html += `
      <div class="error-item">
        <span class="error-tag uslub">uslub</span>
        <div class="error-detail"><span class="explanation">${escapeHtml(err.issue)} ${escapeHtml(err.suggestion)}</span></div>
      </div>`;
  });
  checkResult.innerHTML = html;
}

// ============ LUG'AT ============
const dictBtn = document.getElementById("dict-btn");
const dictInput = document.getElementById("dict-input");
const dictResult = document.getElementById("dict-result");
const dictSuggestions = document.getElementById("dict-suggestions");
const wordOfDayBox = document.getElementById("word-of-day");
const wordOfDayBtn = document.getElementById("wod-word");

apiRequest("/api/dictionary").then((data) => {
  const words = data.words || [];
  window.__dictWords = words;
  dictSuggestions.innerHTML = words.map((w) => `<option value="${escapeHtml(w)}">`).join("");
}).catch(() => { window.__dictWords = []; });

apiRequest("/api/word-of-day").then((entry) => {
  wordOfDayBtn.textContent = entry.word;
  wordOfDayBox.hidden = false;
  wordOfDayBtn.addEventListener("click", () => {
    dictInput.value = entry.word;
    renderDictResult(entry);
    dictResult.hidden = false;
    dictResult.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}).catch(() => {});

async function runDictSearch() {
  const q = dictInput.value.trim();
  dictResult.hidden = false;
  if (!q) {
    dictResult.innerHTML = '<p class="error-message">Qidirish uchun so‘z kiriting.</p>';
    return;
  }
  try {
    const entry = await apiRequest(`/api/dictionary?q=${encodeURIComponent(q)}`);
    renderDictResult(entry);
  } catch (e) {
    const backendSuggestions = (e.data && e.data.detail && e.data.detail.suggestions) || [];
    const localWords = Array.isArray(window.__dictWords) ? window.__dictWords : [];
    const fallbackSuggestions = [...backendSuggestions, ...localWords]
      .filter((w, idx, arr) => typeof w === "string" && w.toLowerCase().includes(q.toLowerCase()) && arr.indexOf(w) === idx)
      .slice(0, 8);
    const suggestions = fallbackSuggestions.length ? fallbackSuggestions : backendSuggestions.slice(0, 8);

    let html = `<p class="error-message">“${escapeHtml(q)}” lug‘atda topilmadi.</p>`;
    if (suggestions.length) {
      html += `<p>Ehtimol, shuni izlagandirsiz: ${suggestions.map((s) => `<span class="pill" data-dict-suggestion="${escapeHtml(s)}">${escapeHtml(s)}</span>`).join(" ")}</p>`;
      html += `<script>document.querySelectorAll('[data-dict-suggestion]').forEach((el) => { el.addEventListener('click', () => { document.getElementById('dict-input').value = el.dataset.dictSuggestion; runDictSearch(); }); });</script>`;
    }
    html += `<p><a class="btn-ghost-sm" href="admin.html?quickAdd=${encodeURIComponent(q)}" target="_blank" rel="noopener">Lug‘atga qo‘shish</a></p>`;
    dictResult.innerHTML = html;
  }
}
dictBtn.addEventListener("click", runDictSearch);
dictInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runDictSearch(); });

function renderDictResult(entry) {
  const synonyms = entry.synonyms.map((s) => `<span class="pill">${escapeHtml(s)}</span>`).join(" ") || "—";
  const antonyms = entry.antonyms.map((s) => `<span class="pill">${escapeHtml(s)}</span>`).join(" ") || "—";
  dictResult.innerHTML = `
    <h2 class="dict-word">${escapeHtml(entry.word)}</h2>
    <div class="dict-meta">${escapeHtml(entry.turkum)} · ${escapeHtml(entry.talaffuz)}</div>
    <p class="dict-meaning">${escapeHtml(entry.meaning)}</p>
    <div class="dict-row"><span class="label">Sinonimlar</span><span>${synonyms}</span></div>
    <div class="dict-row"><span class="label">Antonimi</span><span>${antonyms}</span></div>
    <p class="dict-example">“${escapeHtml(entry.example)}”</p>
    ${entry.kelib_chiqishi ? `<div class="dict-origin"><span class="origin-label">Kelib chiqishi</span>${escapeHtml(entry.kelib_chiqishi)}</div>` : ""}
  `;
}

// ============ TEST ============
const quizForm = document.getElementById("quiz-form");
const quizSubmitBtn = document.getElementById("quiz-submit-btn");
const quizResult = document.getElementById("quiz-result");
const progressTrack = document.getElementById("quiz-progress-track");
const progressFill = document.getElementById("quiz-progress-fill");
const progressLabel = document.getElementById("quiz-progress-label");
let quizQuestions = [];

const FALLBACK_QUIZ = [
  {
    id: 1,
    topic: "Imlo",
    question: "Qaysi variant to‘g‘ri yozilgan?",
    options: { A: "universitetga", B: "universtitetga", C: "universiteta", D: "universtetga" },
    correct: "A",
    explanation: "So‘zning to‘g‘ri shakli “universitetga” bo‘ladi."
  },
  {
    id: 2,
    topic: "Grammatika",
    question: "Qaysi gap grammatik jihatdan to‘g‘ri?",
    options: { A: "Men kecha universitetga bordim.", B: "Men kecha universitetga boradi.", C: "Men kecha universitetga boring.", D: "Men kecha universitetga boraman." },
    correct: "A",
    explanation: "O‘tgan zamon fe’li “bordim” bo‘lishi kerak."
  },
  {
    id: 3,
    topic: "Uslub",
    question: "Qaysi ibora eng toza va aniq uslubda yozilgan?",
    options: { A: "Juda juda qiziqarli", B: "Juda qiziqarli", C: "Qiziqarli juda juda", D: "Juda qiziqarli juda" },
    correct: "B",
    explanation: "Takroriy so‘zlar uslubiy jihatdan noqulay bo‘ladi."
  },
  {
    id: 4,
    topic: "Imlo",
    question: "Qaysi ikkinchi qism to‘g‘ri?",
    options: { A: "hamma vaqt", B: "hamma-vakt", C: "hammavakt", D: "hamma vaqti" },
    correct: "A",
    explanation: "“Hamma vaqt” iborasi to‘g‘ri va aniq shakl."
  }
];

function renderFallbackQuiz() {
  quizForm.innerHTML = quizQuestions.map((q) => `
    <div class="quiz-q">
      <div class="q-topic">${escapeHtml(q.topic)}</div>
      <div class="q-text">${q.id}. ${escapeHtml(q.question)}</div>
      <div class="q-options">
        ${Object.entries(q.options).map(([key, val]) => `
          <label>
            <input type="radio" name="q${q.id}" value="${key}">
            <span>${key}) ${escapeHtml(val)}</span>
          </label>
        `).join("")}
      </div>
    </div>
  `).join("");
  quizSubmitBtn.hidden = false;
  progressTrack.hidden = false;
  quizForm.addEventListener("change", updateQuizProgress);
  updateQuizProgress();
}

function updateQuizProgress() {
  const answered = quizQuestions.filter((q) => quizForm.querySelector(`input[name="q${q.id}"]:checked`)).length;
  const percent = quizQuestions.length ? Math.round((answered / quizQuestions.length) * 100) : 0;
  progressFill.style.width = `${percent}%`;
  progressLabel.textContent = `${answered}/${quizQuestions.length} savolga javob berildi`;
}

async function loadQuiz() {
  try {
    quizQuestions = await apiRequest("/api/quiz");
  } catch (e) {
    quizQuestions = FALLBACK_QUIZ;
  }
  renderFallbackQuiz();
}
loadQuiz().catch(() => {
  quizQuestions = FALLBACK_QUIZ;
  renderFallbackQuiz();
});

quizSubmitBtn.addEventListener("click", async () => {
  const answers = {};
  quizQuestions.forEach((q) => {
    const checked = quizForm.querySelector(`input[name="q${q.id}"]:checked`);
    if (checked) answers[q.id] = checked.value;
  });
  if (Object.keys(answers).length === 0) {
    quizResult.hidden = false;
    quizResult.innerHTML = '<p class="error-message">Kamida bitta savolga javob bering.</p>';
    return;
  }
  try {
    const data = await apiRequest("/api/quiz/submit", { method: "POST", body: JSON.stringify({ answers }) });
    renderQuizResult(data);
  } catch (e) {
    const answeredIds = Object.keys(answers)
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id));
    const results = [];
    let score = 0;
    const topicStats = {};

    answeredIds.forEach((id) => {
      const q = quizQuestions.find((item) => item.id === id);
      if (!q) return;
      const correct = answers[id] === q.correct;
      if (correct) score += 1;
      if (!topicStats[q.topic]) topicStats[q.topic] = { correct: 0, total: 0 };
      topicStats[q.topic].total += 1;
      if (correct) topicStats[q.topic].correct += 1;
      results.push({
        topic: q.topic,
        correct,
        explanation: q.explanation,
      });
    });

    const total = answeredIds.length;
    const percent = total ? Math.round((score / total) * 100) : 0;
    let html = `<div class="quiz-summary">Natija: ${score}/${total} (${percent}%)</div>`;
    html += `<div class="quiz-recommendation">Demo test rejimida natija hisoblandi. Backend qaytib kelganda haqiqiy ma’lumotlar ishlatiladi.</div>`;
    html += '<div class="topic-bars">';
    Object.entries(topicStats).forEach(([topic, stat]) => {
      const pct = Math.round((stat.correct / stat.total) * 100);
      html += `
        <div class="topic-bar-row">
          <div class="topic-bar-label"><span>${escapeHtml(topic)}</span><span>${stat.correct}/${stat.total}</span></div>
          <div class="topic-bar-track"><div class="topic-bar-fill${pct < 60 ? " weak" : ""}" style="width:${pct}%"></div></div>
        </div>`;
    });
    html += '</div>';
    results.forEach((r) => {
      html += `
        <div class="quiz-detail">
          <span class="${r.correct ? "status-ok" : "status-bad"}">${r.correct ? "✅ To‘g‘ri" : "❌ Noto‘g‘ri"}</span>
          — ${escapeHtml(r.topic)}: ${escapeHtml(r.explanation)}
        </div>`;
    });
    quizResult.hidden = false;
    quizResult.innerHTML = html;
    quizResult.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

function renderQuizResult(data) {
  quizResult.hidden = false;

  // mavzular kesimida to'g'ri/noto'g'ri sonini hisoblaymiz
  const topicStats = {};
  data.results.forEach((r) => {
    if (!topicStats[r.topic]) topicStats[r.topic] = { correct: 0, total: 0 };
    topicStats[r.topic].total += 1;
    if (r.correct) topicStats[r.topic].correct += 1;
  });

  let html = `<div class="quiz-summary">Natija: ${data.score}/${data.total} (${data.percent}%)</div>`;
  html += `<div class="quiz-recommendation">${escapeHtml(data.recommendation)}</div>`;

  html += '<div class="topic-bars">';
  Object.entries(topicStats).forEach(([topic, stat]) => {
    const pct = Math.round((stat.correct / stat.total) * 100);
    const weak = pct < 60;
    html += `
      <div class="topic-bar-row">
        <div class="topic-bar-label"><span>${escapeHtml(topic)}</span><span>${stat.correct}/${stat.total}</span></div>
        <div class="topic-bar-track"><div class="topic-bar-fill${weak ? " weak" : ""}" style="width:${pct}%"></div></div>
      </div>`;
  });
  html += "</div>";

  data.results.forEach((r) => {
    html += `
      <div class="quiz-detail">
        <span class="${r.correct ? "status-ok" : "status-bad"}">${r.correct ? "✅ To‘g‘ri" : "❌ Noto‘g‘ri"}</span>
        — ${escapeHtml(r.topic)}: ${escapeHtml(r.explanation)}
      </div>`;
  });
  quizResult.innerHTML = html;
  quizResult.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ============ AI YORDAMCHI ============
const assistBtn = document.getElementById("assist-btn");
const assistInput = document.getElementById("assist-input");
const assistResult = document.getElementById("assist-result");

assistBtn.addEventListener("click", async () => {
  const text = assistInput.value.trim();
  const mode = document.querySelector('input[name="mode"]:checked').value;
  assistResult.hidden = false;
  if (!text) {
    assistResult.innerHTML = '<p class="error-message">Iltimos, matn kiriting.</p>';
    return;
  }
  assistBtn.disabled = true;
  assistBtn.textContent = "Ishlanmoqda...";
  try {
    const data = await apiRequest("/api/ai-assist", { method: "POST", body: JSON.stringify({ text, mode }) });
    let html = `<div class="assist-output">${escapeHtml(data.result)}</div>`;
    if (data.note) html += `<p class="assist-note">${escapeHtml(data.note)}</p>`;
    assistResult.innerHTML = html;
  } catch (e) {
    assistResult.innerHTML = `<p class="error-message">Xatolik: ${escapeHtml(e.message)}</p>`;
  } finally {
    assistBtn.disabled = false;
    assistBtn.textContent = "Yubor";
  }
});
