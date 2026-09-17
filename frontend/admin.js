// O'zbekTil AI - Admin panel mantiqi
const BASE_URL = "http://localhost:8000";

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const AUTH_TOKEN_KEY = "ozbektil_token";
const AUTH_USER_KEY = "ozbektil_user";
const ACTIVITY_KEY = "ozbektil_admin_activity";

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

function getRecentActivities() {
  try { return JSON.parse(localStorage.getItem(ACTIVITY_KEY) || "[]"); } catch { return []; }
}

function appendActivity(kind, message) {
  const entries = getRecentActivities();
  entries.unshift({
    id: Date.now() + Math.random(),
    kind,
    message,
    time: new Date().toISOString(),
  });
  localStorage.setItem(ACTIVITY_KEY, JSON.stringify(entries.slice(0, 8)));
  renderActivityLog();
}

function renderActivityLog() {
  const list = document.getElementById("admin-activity-list");
  if (!list) return;
  const entries = getRecentActivities();
  if (!entries.length) {
    list.innerHTML = '<li class="activity-item"><span class="activity-text">Hozircha admin harakati mavjud emas.</span></li>';
    return;
  }
  list.innerHTML = entries.map((entry) => `
    <li class="activity-item">
      <span class="activity-badge ${escapeHtml(entry.kind)}">${escapeHtml(entry.kind)}</span>
      <span class="activity-text">${escapeHtml(entry.message)}</span>
      <span class="activity-time">${new Date(entry.time).toLocaleString("uz-UZ", { dateStyle: "short", timeStyle: "short" })}</span>
    </li>
  `).join("");
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(BASE_URL + path, { ...options, headers });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && data.detail;
    const message = typeof detail === "string"
      ? detail
      : (detail && typeof detail.message === "string" ? detail.message : "Server xatosi");
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return data;
}

const gate = document.getElementById("admin-gate");
const app = document.getElementById("admin-app");

async function bootstrap() {
  const user = getStoredUser();
  if (!user || !getToken()) {
    showGate();
    return;
  }
  try {
    // token va admin huquqini serverdan tasdiqlaymiz
    const me = await apiRequest("/api/auth/me");
    if (!me.is_admin) {
      showGate("Bu bo‘lim faqat administratorlar uchun. Boshqa hisob bilan kiring.");
      return;
    }
    setSession(getToken(), me);
    showApp(me);
  } catch {
    clearSession();
    showGate();
  }
}

function showGate(message) {
  gate.hidden = false;
  app.hidden = true;
  const err = document.getElementById("admin-login-error");
  if (message) {
    err.textContent = message;
    err.hidden = false;
  } else {
    err.textContent = "";
    err.hidden = true;
  }
}

function showApp(user) {
  gate.hidden = true;
  app.hidden = false;
  document.getElementById("admin-username-label").textContent = `👋 ${user.username}`;
  renderActivityLog();
  loadStats();
  const quickWord = new URLSearchParams(window.location.search).get("quickAdd");
  if (quickWord) {
    openWordModal(null);
    document.getElementById("word-word").value = quickWord.trim();
    window.history.replaceState({}, "", window.location.pathname);
  }
}

document.querySelectorAll("[data-password-toggle]").forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const input = document.getElementById(toggle.dataset.passwordToggle);
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    toggle.textContent = isPassword ? "Yashirish" : "Ko‘rsat";
    toggle.setAttribute("aria-label", isPassword ? "Parolni yashirish" : "Parolni ko‘rsatish");
  });
});

document.getElementById("admin-login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errBox = document.getElementById("admin-login-error");
  errBox.hidden = true;
  const username = document.getElementById("admin-username").value.trim();
  const password = document.getElementById("admin-password").value;
  const btn = document.getElementById("admin-login-submit");
  btn.disabled = true;
  btn.textContent = "Kirilmoqda...";
  try {
    const data = await apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    if (!data.user.is_admin) {
      errBox.textContent = "Bu hisob administrator emas.";
      errBox.hidden = false;
      return;
    }
    setSession(data.token, data.user);
    showApp(data.user);
  } catch (err) {
    errBox.textContent = err.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Kirish";
  }
});

document.getElementById("admin-logout-btn").addEventListener("click", () => {
  appendActivity("session", "Admin foydalanuvchisi tizimdan chiqdi.");
  clearSession();
  location.reload();
});

// ============ TABLAR ============
document.querySelectorAll("[data-admin-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll("[data-admin-tab]").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".admin-content .panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`admin-${tab.dataset.adminTab}`).classList.add("active");
    if (tab.dataset.adminTab === "users") loadUsers();
    if (tab.dataset.adminTab === "dictionary") loadDictionary();
    if (tab.dataset.adminTab === "quiz") loadQuizQuestions();
  });
});

// ============ STATISTIKA ============
async function loadStats() {
  const grid = document.getElementById("stats-grid");
  try {
    const s = await apiRequest("/api/admin/stats");
    grid.innerHTML = `
      <div class="profile-stat"><div class="stat-value">${s.total_users}</div><div class="stat-label">FOYDALANUVCHI</div></div>
      <div class="profile-stat"><div class="stat-value">${s.total_checks}</div><div class="stat-label">MATN TEKSHIRUVI</div></div>
      <div class="profile-stat"><div class="stat-value">${s.total_quiz_attempts}</div><div class="stat-label">TEST URINISHI</div></div>
      <div class="profile-stat"><div class="stat-value">${s.avg_quiz_percent}%</div><div class="stat-label">O‘RTACHA NATIJA</div></div>
      <div class="profile-stat"><div class="stat-value">${s.total_dictionary_words}</div><div class="stat-label">LUG‘AT SO‘ZLARI</div></div>
      <div class="profile-stat"><div class="stat-value">${s.total_quiz_questions}</div><div class="stat-label">TEST SAVOLLARI</div></div>
    `;
  } catch (e) {
    grid.innerHTML = `<p class="error-message">Statistikani yuklab bo‘lmadi: ${escapeHtml(e.message)}</p>`;
  }
}

// ============ FOYDALANUVCHILAR ============
async function loadUsers() {
  const tbody = document.querySelector("#users-table tbody");
  tbody.innerHTML = `<tr><td colspan="6">Yuklanmoqda...</td></tr>`;
  try {
    const users = await apiRequest("/api/admin/users");
    tbody.innerHTML = users.map((u) => `
      <tr>
        <td>${escapeHtml(u.username)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${new Date(u.created_at).toLocaleDateString("uz-UZ")}</td>
        <td>${u.quiz_attempts}</td>
        <td>${u.is_admin ? '<span class="badge-admin">Admin</span>' : '<span class="badge-user">Foydalanuvchi</span>'}</td>
        <td class="row-actions">
          ${u.is_admin ? "" : `<button class="danger" data-delete-user="${u.id}">O‘chirish</button>`}
        </td>
      </tr>
    `).join("") || `<tr><td colspan="6">Hozircha foydalanuvchi yo‘q.</td></tr>`;

    tbody.querySelectorAll("[data-delete-user]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Bu foydalanuvchini o‘chirmoqchimisiz?")) return;
        try {
          const userId = btn.dataset.deleteUser;
          await apiRequest(`/api/admin/users/${userId}`, { method: "DELETE" });
          appendActivity("user", `Foydalanuvchi #${userId} o‘chirildi.`);
          loadUsers();
          loadStats();
        } catch (e) {
          alert(e.message);
        }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="error-message">${escapeHtml(e.message)}</td></tr>`;
  }
}

// ============ LUG'AT ============
const wordModal = document.getElementById("word-modal");
const wordForm = document.getElementById("word-form");

function resetWordForm() {
  wordForm.reset();
  document.getElementById("word-id").value = "";
  document.getElementById("word-error").hidden = true;
}

function openWordModal(entry) {
  document.getElementById("word-error").hidden = true;
  document.getElementById("word-modal-title").textContent = entry ? "So‘zni tahrirlash" : "Yangi so‘z";
  document.getElementById("word-id").value = entry ? entry.id : "";
  document.getElementById("word-word").value = entry ? entry.word : "";
  document.getElementById("word-turkum").value = entry ? entry.turkum : "";
  document.getElementById("word-talaffuz").value = entry ? entry.talaffuz : "";
  document.getElementById("word-meaning").value = entry ? entry.meaning : "";
  document.getElementById("word-synonyms").value = entry ? (entry.synonyms || []).join(", ") : "";
  document.getElementById("word-antonyms").value = entry ? (entry.antonyms || []).join(", ") : "";
  document.getElementById("word-example").value = entry ? entry.example : "";
  document.getElementById("word-origin").value = entry ? entry.kelib_chiqishi : "";
  wordModal.hidden = false;
}

document.getElementById("add-word-btn").addEventListener("click", () => openWordModal(null));

wordForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errBox = document.getElementById("word-error");
  errBox.hidden = true;
  const id = document.getElementById("word-id").value;
  const payload = {
    word: document.getElementById("word-word").value.trim(),
    turkum: document.getElementById("word-turkum").value.trim(),
    talaffuz: document.getElementById("word-talaffuz").value.trim(),
    meaning: document.getElementById("word-meaning").value.trim(),
    synonyms: document.getElementById("word-synonyms").value.split(",").map((s) => s.trim()).filter(Boolean),
    antonyms: document.getElementById("word-antonyms").value.split(",").map((s) => s.trim()).filter(Boolean),
    example: document.getElementById("word-example").value.trim(),
    kelib_chiqishi: document.getElementById("word-origin").value.trim(),
  };
  if (!payload.word || !payload.meaning) {
    errBox.textContent = "So‘z va ma’nosi maydonlari to‘ldirilishi shart.";
    errBox.hidden = false;
    return;
  }
  const btn = document.getElementById("word-submit");
  btn.disabled = true;
  try {
    if (id) {
      await apiRequest(`/api/admin/dictionary/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      appendActivity("dictionary", `“${payload.word}” so‘zi yangilandi.`);
    } else {
      await apiRequest("/api/admin/dictionary", { method: "POST", body: JSON.stringify(payload) });
      appendActivity("dictionary", `“${payload.word}” so‘zi qo‘shildi.`);
    }
    resetWordForm();
    wordModal.hidden = true;
    loadDictionary();
    loadStats();
  } catch (err) {
    errBox.textContent = err.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
  }
});

let dictionaryCache = [];
async function loadDictionary() {
  const tbody = document.querySelector("#dictionary-table tbody");
  tbody.innerHTML = `<tr><td colspan="4">Yuklanmoqda...</td></tr>`;
  try {
    dictionaryCache = await apiRequest("/api/admin/dictionary");
    tbody.innerHTML = dictionaryCache.map((w) => `
      <tr>
        <td>${escapeHtml(w.word)}</td>
        <td>${escapeHtml(w.turkum)}</td>
        <td class="cell-truncate">${escapeHtml(w.meaning)}</td>
        <td class="row-actions">
          <button data-edit-word="${w.id}">Tahrirlash</button>
          <button class="danger" data-delete-word="${w.id}">O‘chirish</button>
        </td>
      </tr>
    `).join("") || `<tr><td colspan="4">Lug‘at bo‘sh.</td></tr>`;

    tbody.querySelectorAll("[data-edit-word]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const entry = dictionaryCache.find((w) => String(w.id) === btn.dataset.editWord);
        openWordModal(entry);
      });
    });
    tbody.querySelectorAll("[data-delete-word]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Bu so‘zni o‘chirmoqchimisiz?")) return;
        try {
          const wordId = btn.dataset.deleteWord;
          await apiRequest(`/api/admin/dictionary/${wordId}`, { method: "DELETE" });
          appendActivity("dictionary", `So‘z #${wordId} o‘chirildi.`);
          loadDictionary();
          loadStats();
        } catch (e) {
          alert(e.message);
        }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="error-message">${escapeHtml(e.message)}</td></tr>`;
  }
}

// ============ TEST SAVOLLARI ============
const questionModal = document.getElementById("question-modal");
const questionForm = document.getElementById("question-form");

function resetQuestionForm() {
  questionForm.reset();
  document.getElementById("question-id").value = "";
  document.getElementById("question-error").hidden = true;
}

function openQuestionModal(q) {
  document.getElementById("question-error").hidden = true;
  document.getElementById("question-modal-title").textContent = q ? "Savolni tahrirlash" : "Yangi savol";
  document.getElementById("question-id").value = q ? q.id : "";
  document.getElementById("question-topic").value = q ? q.topic : "";
  document.getElementById("question-text").value = q ? q.question : "";
  document.getElementById("question-opt-a").value = q ? (q.options.A || "") : "";
  document.getElementById("question-opt-b").value = q ? (q.options.B || "") : "";
  document.getElementById("question-opt-c").value = q ? (q.options.C || "") : "";
  document.getElementById("question-opt-d").value = q ? (q.options.D || "") : "";
  document.getElementById("question-correct").value = q ? q.correct : "";
  document.getElementById("question-explanation").value = q ? q.explanation : "";
  questionModal.hidden = false;
}

document.getElementById("add-question-btn").addEventListener("click", () => openQuestionModal(null));

questionForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errBox = document.getElementById("question-error");
  errBox.hidden = true;
  const id = document.getElementById("question-id").value;
  const options = {};
  ["A", "B", "C", "D"].forEach((key) => {
    const val = document.getElementById(`question-opt-${key.toLowerCase()}`).value.trim();
    if (val) options[key] = val;
  });
  const payload = {
    topic: document.getElementById("question-topic").value.trim(),
    question: document.getElementById("question-text").value.trim(),
    options,
    correct: document.getElementById("question-correct").value.trim().toUpperCase(),
    explanation: document.getElementById("question-explanation").value.trim(),
  };
  if (!payload.topic || !payload.question || Object.keys(options).length < 2) {
    errBox.textContent = "Mavzu, savol va kamida 2 ta variant to‘ldirilishi shart.";
    errBox.hidden = false;
    return;
  }
  if (!options[payload.correct]) {
    errBox.textContent = "To‘g‘ri javob harfi variantlar ichida bo‘lishi kerak (masalan, A yoki B).";
    errBox.hidden = false;
    return;
  }
  const btn = document.getElementById("question-submit");
  btn.disabled = true;
  try {
    if (id) {
      await apiRequest(`/api/admin/quiz/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      appendActivity("quiz", `“${payload.topic}” mavzusidagi savol yangilandi.`);
    } else {
      await apiRequest("/api/admin/quiz", { method: "POST", body: JSON.stringify(payload) });
      appendActivity("quiz", `“${payload.topic}” mavzusiga yangi savol qo‘shildi.`);
    }
    resetQuestionForm();
    questionModal.hidden = true;
    loadQuizQuestions();
    loadStats();
  } catch (err) {
    errBox.textContent = err.message;
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
  }
});

let quizCache = [];
async function loadQuizQuestions() {
  const tbody = document.querySelector("#quiz-table tbody");
  tbody.innerHTML = `<tr><td colspan="4">Yuklanmoqda...</td></tr>`;
  try {
    quizCache = await apiRequest("/api/admin/quiz");
    tbody.innerHTML = quizCache.map((q) => `
      <tr>
        <td>${escapeHtml(q.topic)}</td>
        <td class="cell-truncate">${escapeHtml(q.question)}</td>
        <td>${escapeHtml(q.correct)}</td>
        <td class="row-actions">
          <button data-edit-question="${q.id}">Tahrirlash</button>
          <button class="danger" data-delete-question="${q.id}">O‘chirish</button>
        </td>
      </tr>
    `).join("") || `<tr><td colspan="4">Savollar yo‘q.</td></tr>`;

    tbody.querySelectorAll("[data-edit-question]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = quizCache.find((item) => String(item.id) === btn.dataset.editQuestion);
        openQuestionModal(q);
      });
    });
    tbody.querySelectorAll("[data-delete-question]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Bu savolni o‘chirmoqchimisiz?")) return;
        try {
          const questionId = btn.dataset.deleteQuestion;
          await apiRequest(`/api/admin/quiz/${questionId}`, { method: "DELETE" });
          appendActivity("quiz", `Savol #${questionId} o‘chirildi.`);
          loadQuizQuestions();
          loadStats();
        } catch (e) {
          alert(e.message);
        }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="error-message">${escapeHtml(e.message)}</td></tr>`;
  }
}

// ============ MODAL YOPISH (umumiy) ============
document.querySelectorAll("[data-close-modal]").forEach((btn) => {
  btn.addEventListener("click", () => {
    resetWordForm();
    resetQuestionForm();
    wordModal.hidden = true;
    questionModal.hidden = true;
  });
});
document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      resetWordForm();
      resetQuestionForm();
      wordModal.hidden = true;
      questionModal.hidden = true;
    }
  });
});

bootstrap();
