/* ══════════════════════════════════════════════════════════════════════════════
   CareerAI v3 — Frontend Script
   Features: Analysis, Resume Upload, Analytics Scores, Dark/Light Mode,
             Certifications, Chat with Memory, localStorage History
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Config ────────────────────────────────────────────────────────────────────
const API_BASE = "https://ai-career-predictor-2csq.onrender.com"; // ← Your Render URL
// const API_BASE = "http://localhost:5000"; // uncomment for local dev

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  skills:       [],
  interests:    [],
  level:        "Intermediate",
  analysis:     null,
  resumeFile:   null,
  resumeData:   null,
  chatHistory:  [],
};

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTagInput("skills");
  setupTagInput("interests");
  checkHealth();
  smoothNavScroll();
  initTheme();
  loadHistory();
});

// ══ HEALTH CHECK ═════════════════════════════════════════════════════════════
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/api/health`);
    const d = await r.json();
    console.info("[CareerAI] Backend healthy:", d);
  } catch (e) {
    console.warn("[CareerAI] Backend not reachable — demo fallback active.");
  }
}

// ══ DARK / LIGHT THEME ═══════════════════════════════════════════════════════
function initTheme() {
  const saved = localStorage.getItem("careerai-theme") || "dark";
  setTheme(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  setTheme(current === "dark" ? "light" : "dark");
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.getElementById("theme-icon").textContent = theme === "dark" ? "☀️" : "🌙";
  localStorage.setItem("careerai-theme", theme);
}

// ══ TAG INPUT SYSTEM ══════════════════════════════════════════════════════════
function setupTagInput(type) {
  const input     = document.getElementById(`${type}-input`);
  const container = document.getElementById(`${type}-container`);
  container.addEventListener("click", () => input.focus());
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = input.value.trim().replace(/,$/, "");
      if (val) addTag(type, val);
      input.value = "";
    } else if (e.key === "Backspace" && !input.value) {
      removeLastTag(type);
    }
  });
}

function addTag(type, value) {
  const list  = type === "skills" ? state.skills : state.interests;
  const clean = value.trim();
  if (!clean || list.includes(clean)) return;
  list.push(clean);
  renderTags(type);
  const input = document.getElementById(`${type}-input`);
  input.value = "";
  input.focus();
}

function removeLastTag(type) {
  const list = type === "skills" ? state.skills : state.interests;
  if (list.length) { list.pop(); renderTags(type); }
}

function removeTag(type, index) {
  const list = type === "skills" ? state.skills : state.interests;
  list.splice(index, 1);
  renderTags(type);
}

function renderTags(type) {
  const list      = type === "skills" ? state.skills : state.interests;
  const container = document.getElementById(`${type}-container`);
  const input     = document.getElementById(`${type}-input`);
  container.querySelectorAll(".tag").forEach(t => t.remove());
  list.forEach((tag, i) => {
    const el = document.createElement("span");
    el.className = "tag";
    el.innerHTML = `${escHtml(tag)} <button class="tag__remove" onclick="removeTag('${type}',${i})">×</button>`;
    container.insertBefore(el, input);
  });
}

// ══ LEVEL ═════════════════════════════════════════════════════════════════════
function setLevel(btn) {
  document.querySelectorAll(".level-btn").forEach(b => b.classList.remove("level-btn--active"));
  btn.classList.add("level-btn--active");
  state.level = btn.dataset.level;
}

// ══ ANALYSIS ══════════════════════════════════════════════════════════════════
async function runAnalysis() {
  if (state.skills.length === 0) {
    showResultsError("Please add at least one skill before analyzing.");
    document.getElementById("skills-input").focus();
    return;
  }
  const goals = document.getElementById("goals-input").value.trim();

  setBtnLoading("analyze-btn", "analyze-btn-text", "analyze-spinner", true);
  hideResultsStates();
  showSkeleton(true);
  scrollTo("results");

  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ skills: state.skills, interests: state.interests, level: state.level, goals }),
    }, 35000);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.career_paths) throw new Error("Invalid response structure");

    state.analysis = data;
    showSkeleton(false);
    renderResults(data);
    saveToHistory(data);
  } catch (err) {
    console.error("[CareerAI] Analysis error:", err);
    showSkeleton(false);
    showResultsError("Analysis failed. Please check your connection and try again.");
  } finally {
    setBtnLoading("analyze-btn", "analyze-btn-text", "analyze-spinner", false, "✨ Analyze My Career Path");
  }
}

function renderResults(data) {
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-error").classList.add("hidden");
  const content = document.getElementById("results-content");
  content.classList.remove("hidden");

  // Render analytics scores
  const scores = data.scores || {};
  renderScoreCircle("readiness-fill", "readiness-num", scores.job_readiness || 60, "blue");
  renderScoreCircle("match-fill",     "match-num",     scores.career_match  || 70, "green");
  renderScoreCircle("learning-fill",  "learning-num",  scores.learning_speed|| 65, "gold");

  // Salary from top career path
  const topCareer = (data.career_paths || [])[0] || {};
  document.getElementById("analytics-salary-val").textContent = topCareer.salary_range || "—";

  // Summary
  document.getElementById("summary-text").textContent = data.summary || "";

  // Render tabs
  renderCareerPaths(data.career_paths  || []);
  renderSkillGaps(data.skill_gaps      || []);
  renderCourses(data.courses           || []);
  renderCertifications(data.certifications || []);
  renderRoadmap(data.roadmap           || []);

  switchTabById("career");
  setTimeout(animateAllBars, 200);

  // Update chat context
  state.chatHistory = [];
  document.getElementById("chat-messages").innerHTML = buildBotMessage(
    `Analysis complete! 🎉 You have a strong match with <strong>${topCareer.title || "Software Engineer"}</strong> at ${
      scores.career_match || 70}% career match. Your job readiness score is <strong>${
      scores.job_readiness || 60}/100</strong>. Ask me anything about your career plan!`
  );
}

// ── Score Circle ──────────────────────────────────────────────────────────────
function renderScoreCircle(fillId, numId, score, colorClass) {
  const circumference = 2 * Math.PI * 42; // r = 42
  const fillEl = document.getElementById(fillId);
  const numEl  = document.getElementById(numId);
  if (!fillEl || !numEl) return;

  setTimeout(() => {
    const dash = (score / 100) * circumference;
    fillEl.style.strokeDasharray = `${dash} ${circumference}`;
    // Animate number
    let current = 0;
    const step = Math.ceil(score / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, score);
      numEl.textContent = current;
      if (current >= score) clearInterval(timer);
    }, 30);
  }, 300);
}

// ── Career Paths ──────────────────────────────────────────────────────────────
function renderCareerPaths(paths) {
  document.getElementById("career-cards").innerHTML = paths.map(p => `
    <div class="career-card">
      <div class="career-card__header">
        <h3 class="career-card__title">${escHtml(p.title)}</h3>
        <span class="match-badge">${p.match_percentage}% match</span>
      </div>
      <div class="match-bar">
        <div class="match-bar__track">
          <div class="match-bar__fill" data-width="${p.match_percentage}"></div>
        </div>
      </div>
      <p class="career-card__desc">${escHtml(p.description)}</p>
      <div class="career-card__meta">
        <div class="meta-row"><span class="meta-label">Salary</span><span class="meta-value">${escHtml(p.salary_range || "—")}</span></div>
        <div class="meta-row"><span class="meta-label">Demand</span>${demandBadge(p.demand)}</div>
        <div class="meta-row">
          <span class="meta-label">Companies</span>
          <div class="companies">${(p.top_companies || []).map(c => `<span class="co-tag">${escHtml(c)}</span>`).join("")}</div>
        </div>
      </div>
    </div>
  `).join("");
}

// ── Skill Gaps ────────────────────────────────────────────────────────────────
function renderSkillGaps(gaps) {
  document.getElementById("skills-list").innerHTML = gaps.map(g => {
    const level = g.current_level || 0;
    const fillClass = level < 30 ? "fill--low" : level < 65 ? "fill--mid" : "fill--high";
    return `
      <div class="skill-item">
        <div class="skill-item__header">
          <span class="skill-item__name">${escHtml(g.skill)}</span>
          <div class="skill-item__tags">
            <span class="importance-tag importance-tag--${(g.importance||"medium").toLowerCase()}">${escHtml(g.importance)}</span>
          </div>
        </div>
        <div class="skill-progress">
          <div class="skill-progress__labels">
            <span class="skill-progress__now">Current: ${level}%</span>
            <span class="skill-progress__target">Target: ${escHtml(g.level_needed)}</span>
          </div>
          <div class="skill-progress__track">
            <div class="skill-progress__fill ${fillClass}" data-width="${level}"></div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ── Courses ───────────────────────────────────────────────────────────────────
function renderCourses(courses) {
  document.getElementById("courses-cards").innerHTML = courses.map(c => `
    <div class="course-card">
      <div class="course-card__top">
        <span class="course-platform">${escHtml(c.platform)}</span>
        <span class="${c.free ? 'free-badge' : 'paid-badge'}">${c.free ? '✓ Free' : '💳 Paid'}</span>
      </div>
      <div class="course-card__title">${escHtml(c.title)}</div>
      <div class="course-card__footer">
        <div class="course-card__badges">
          <span class="course-duration">⏱ ${escHtml(c.duration || "—")}</span>
          ${c.difficulty ? `<span class="diff-badge">${escHtml(c.difficulty)}</span>` : ""}
          ${c.certificate ? `<span class="cert-badge">🏆 Certificate</span>` : ""}
        </div>
        <a href="${escHtml(c.url || "#")}" target="_blank" rel="noopener" class="course-link">Enroll →</a>
      </div>
    </div>
  `).join("");
}

// ── Certifications ────────────────────────────────────────────────────────────
function renderCertifications(certs) {
  document.getElementById("certs-grid").innerHTML = certs.map((c, i) => `
    <div class="cert-card" style="--i:${i}">
      <div class="cert-card__top">
        <div class="cert-card__title">${escHtml(c.title)}</div>
        <span class="cert-value ${c.value === 'High' ? 'cert-value--high' : ''}">${escHtml(c.value)}</span>
      </div>
      <div class="cert-card__meta">
        <span class="cert-platform">📌 ${escHtml(c.platform)}</span>
        <span class="diff-badge">${escHtml(c.difficulty)}</span>
      </div>
      <a href="${escHtml(c.url || "#")}" target="_blank" rel="noopener" class="cert-link">Learn More →</a>
    </div>
  `).join("");
}

// ── Roadmap ───────────────────────────────────────────────────────────────────
function renderRoadmap(phases) {
  document.getElementById("roadmap-list").innerHTML = phases.map(p => `
    <div class="roadmap-item">
      <div class="roadmap-item__line">
        <div class="roadmap-dot"></div>
        <div class="roadmap-connector"></div>
      </div>
      <div class="roadmap-card">
        <div class="roadmap-card__top">
          <span class="roadmap-month">${escHtml(p.month)}</span>
          <span class="roadmap-milestone">🏆 ${escHtml(p.milestone)}</span>
        </div>
        <div class="roadmap-focus">${escHtml(p.focus)}</div>
        <div class="roadmap-tasks">
          ${(p.tasks || []).map(t => `<div class="roadmap-task">${escHtml(t)}</div>`).join("")}
        </div>
      </div>
    </div>
  `).join("");
}

// ══ RESUME ANALYZER ══════════════════════════════════════════════════════════

// Drag & Drop
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById("drop-zone").classList.add("drop-zone--active");
}
function handleDragLeave(e) {
  document.getElementById("drop-zone").classList.remove("drop-zone--active");
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById("drop-zone").classList.remove("drop-zone--active");
  const file = e.dataTransfer.files[0];
  if (file) setResumeFile(file);
}
function handleResumeFileSelect(e) {
  const file = e.target.files[0];
  if (file) setResumeFile(file);
}

function setResumeFile(file) {
  const allowed = ["application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword"];
  const nameOk  = /\.(pdf|docx|doc)$/i.test(file.name);

  if (!nameOk) {
    showResumeError("Please upload a PDF or DOCX file.");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showResumeError("File too large. Maximum size is 5MB.");
    return;
  }

  state.resumeFile = file;
  document.getElementById("resume-error").classList.add("hidden");

  // Show preview
  const ext  = file.name.split(".").pop().toUpperCase();
  const size = file.size < 1024 * 1024
    ? `${Math.round(file.size / 1024)} KB`
    : `${(file.size / 1024 / 1024).toFixed(1)} MB`;

  document.getElementById("file-preview-icon").textContent = ext === "PDF" ? "📄" : "📝";
  document.getElementById("file-preview-name").textContent = file.name;
  document.getElementById("file-preview-size").textContent = size;
  document.getElementById("file-preview").classList.remove("hidden");
  document.getElementById("resume-btn").disabled = false;
  document.getElementById("drop-zone").querySelector(".drop-zone__text strong").textContent = "File ready to analyze!";
}

function clearResumeFile() {
  state.resumeFile = null;
  document.getElementById("file-preview").classList.add("hidden");
  document.getElementById("resume-btn").disabled = true;
  document.getElementById("drop-zone").querySelector(".drop-zone__text strong").textContent = "Drag & drop your resume here";
  document.getElementById("resume-file-input").value = "";
}

async function runResumeAnalysis() {
  if (!state.resumeFile) return;

  setBtnLoading("resume-btn", "resume-btn-text", "resume-spinner", true);
  document.getElementById("resume-error").classList.add("hidden");
  document.getElementById("resume-results").classList.add("hidden");

  const formData = new FormData();
  formData.append("resume", state.resumeFile);

  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/resume-analyze`, {
      method: "POST",
      body:   formData,
    }, 40000);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    state.resumeData = data;
    renderResumeResults(data);
    scrollTo("resume");
  } catch (err) {
    console.error("[CareerAI] Resume error:", err);
    showResumeError(err.message || "Resume analysis failed. Please try again.");
  } finally {
    setBtnLoading("resume-btn", "resume-btn-text", "resume-spinner", false, "📊 Analyze Resume");
  }
}

function renderResumeResults(data) {
  const score   = data.resume_score || 0;
  const circumference = 2 * Math.PI * 42;

  // Score circle
  const fillEl = document.getElementById("resume-score-fill");
  const numEl  = document.getElementById("resume-score-num");
  setTimeout(() => {
    const dash = (score / 100) * circumference;
    fillEl.style.strokeDasharray = `${dash} ${circumference}`;
    // Color based on score
    if (score >= 80)      fillEl.style.stroke = "var(--green)";
    else if (score >= 60) fillEl.style.stroke = "var(--gold)";
    else                  fillEl.style.stroke = "var(--red)";

    let n = 0;
    const step  = Math.ceil(score / 40);
    const timer = setInterval(() => {
      n = Math.min(n + step, score);
      numEl.textContent = n;
      if (n >= score) clearInterval(timer);
    }, 30);
  }, 300);

  // Badge
  const badge    = document.getElementById("resume-score-badge");
  const descEl   = document.getElementById("resume-score-desc");
  if (score >= 80) {
    badge.textContent = "✅ Excellent — Ready to Apply";
    badge.classList.add("score-badge--green");
    descEl.textContent = "Your resume is well-optimized for ATS systems. Start applying now!";
  } else if (score >= 60) {
    badge.textContent = "🟡 Good — Minor Improvements Needed";
    descEl.textContent = "A few tweaks will significantly improve your shortlisting rate.";
  } else if (score >= 40) {
    badge.textContent = "🟠 Average — Needs Work";
    badge.classList.add("score-badge--");
    descEl.textContent = "Your resume needs significant improvements to pass ATS filters.";
  } else {
    badge.textContent = "🔴 Weak — Major Restructuring Needed";
    badge.classList.add("score-badge--red");
    descEl.textContent = "Your resume needs a major overhaul. Follow the improvement tips below.";
  }

  // Extracted skills
  document.getElementById("resume-skills-cloud").innerHTML =
    (data.extracted_skills || []).map(s => `<span class="skill-tag">${escHtml(s)}</span>`).join("");

  // Missing skills
  document.getElementById("resume-missing-cloud").innerHTML =
    (data.missing_skills || []).map(s => `<span class="skill-tag">${escHtml(s)}</span>`).join("");

  // Recommended roles
  document.getElementById("resume-roles-grid").innerHTML =
    (data.recommended_roles || []).map((r, i) => `
      <div class="role-item">
        <div class="role-number">${i + 1}</div>
        <div class="role-title">${escHtml(r)}</div>
      </div>
    `).join("");

  // Tips
  document.getElementById("resume-tips-list").innerHTML =
    (data.improvement_tips || []).map((t, i) => `
      <div class="tip-item">
        <span class="tip-num">0${i + 1}</span>
        <span class="tip-text">${escHtml(t)}</span>
      </div>
    `).join("");

  // Strengths
  document.getElementById("resume-strengths-list").innerHTML =
    (data.strengths || []).length > 0
      ? `<div class="resume-section-title">✅ Your Strengths</div>` +
        (data.strengths || []).map(s => `<span class="strength-tag">✓ ${escHtml(s)}</span>`).join("")
      : "";

  // ATS keywords
  document.getElementById("resume-ats-cloud").innerHTML =
    (data.ats_keywords || []).map(k => `<span class="skill-tag">${escHtml(k)}</span>`).join("");

  // Show results, switch to first tab
  document.getElementById("resume-results").classList.remove("hidden");
  document.querySelectorAll(".resume-tabs .tab").forEach(t => t.classList.remove("tab--active"));
  document.querySelectorAll(".resume-tabs .tab")[0].classList.add("tab--active");
  document.querySelectorAll("[id^='tab-r-']").forEach(p => p.classList.add("hidden"));
  document.getElementById("tab-r-skills").classList.remove("hidden");
}

function switchResumeTab(btn, panelId) {
  document.querySelectorAll(".resume-tabs .tab").forEach(t => t.classList.remove("tab--active"));
  btn.classList.add("tab--active");
  document.querySelectorAll("[id^='tab-r-']").forEach(p => p.classList.add("hidden"));
  const panel = document.getElementById(`tab-${panelId}`);
  if (panel) panel.classList.remove("hidden");
}

function showResumeError(msg) {
  const err = document.getElementById("resume-error");
  document.getElementById("resume-error-text").textContent = msg;
  err.classList.remove("hidden");
}

// ══ TABS ══════════════════════════════════════════════════════════════════════
function switchTab(btn, tabId) {
  document.querySelectorAll("#results-tabs .tab").forEach(t => t.classList.remove("tab--active"));
  btn.classList.add("tab--active");
  switchTabById(tabId);
}

function switchTabById(tabId) {
  document.querySelectorAll(".tab-panel[id^='tab-']").forEach(p => {
    // Only hide main results tabs, not resume tabs
    if (!p.id.startsWith("tab-r-")) p.classList.add("hidden");
  });
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) {
    panel.classList.remove("hidden");
    if (tabId === "skills") setTimeout(animateAllBars, 100);
  }
}

// ══ PROGRESS BARS ════════════════════════════════════════════════════════════
function animateAllBars() {
  document.querySelectorAll("[data-width]").forEach(el => {
    el.style.width = el.dataset.width + "%";
  });
}

// ══ CHAT ═════════════════════════════════════════════════════════════════════
async function sendChat() {
  const input = document.getElementById("chat-input");
  const msg   = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendUserMessage(msg);
  state.chatHistory.push({ role: "user", content: msg });
  document.getElementById("chat-suggestions").style.display = "none";

  const typingId = appendTypingIndicator();
  setBtnLoading("chat-send-btn", "chat-send-text", "chat-send-spinner", true);

  const historyForAPI = state.chatHistory.slice(-8).map(m => ({
    role:    m.role === "bot" ? "assistant" : "user",
    content: m.content,
  }));

  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        message:          msg,
        history:          historyForAPI,
        analysis_context: state.analysis || {},
      }),
    }, 22000);

    removeTypingIndicator(typingId);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data  = await res.json();
    const reply = data.reply || "I'm not sure how to answer that. Try rephrasing!";

    appendBotMessage(reply);
    state.chatHistory.push({ role: "bot", content: reply });

  } catch (err) {
    console.error("[CareerAI] Chat error:", err);
    removeTypingIndicator(typingId);
    appendBotMessage("I'm having trouble connecting right now. Please try again in a moment.");
  } finally {
    setBtnLoading("chat-send-btn", "chat-send-text", "chat-send-spinner", false, "Send ↑");
  }
}

function sendSuggestion(btn) {
  document.getElementById("chat-input").value = btn.textContent.trim();
  sendChat();
}

function clearChatHistory() {
  state.chatHistory = [];
  document.getElementById("chat-messages").innerHTML = buildBotMessage(
    "Chat cleared! How can I help you with your career journey? 🚀"
  );
  document.getElementById("chat-suggestions").style.display = "flex";
}

function appendUserMessage(text) {
  document.getElementById("chat-messages").insertAdjacentHTML("beforeend", `
    <div class="msg msg--user">
      <div class="msg__avatar">😊</div>
      <div class="msg__bubble">${escHtml(text)}</div>
    </div>
  `);
  scrollMessages();
}

function appendBotMessage(html) {
  document.getElementById("chat-messages").insertAdjacentHTML("beforeend", buildBotMessage(html));
  scrollMessages();
}

function buildBotMessage(html) {
  return `
    <div class="msg msg--bot">
      <div class="msg__avatar">🤖</div>
      <div class="msg__bubble">${html}</div>
    </div>
  `;
}

function appendTypingIndicator() {
  const id = "typing-" + Date.now();
  document.getElementById("chat-messages").insertAdjacentHTML("beforeend", `
    <div class="msg msg--bot" id="${id}">
      <div class="msg__avatar">🤖</div>
      <div class="msg__bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    </div>
  `);
  scrollMessages();
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollMessages() {
  const m = document.getElementById("chat-messages");
  m.scrollTop = m.scrollHeight;
}

// ══ LOCAL STORAGE HISTORY ════════════════════════════════════════════════════
const HISTORY_KEY = "careerai-history";
const MAX_HISTORY = 5;

function saveToHistory(data) {
  try {
    const history = getHistory();
    const entry = {
      id:        Date.now(),
      date:      new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
      skills:    state.skills.slice(0, 5),
      level:     state.level,
      topCareer: (data.career_paths[0] || {}).title || "—",
      score:     (data.scores || {}).job_readiness || 0,
      data:      data,
    };
    history.unshift(entry);
    if (history.length > MAX_HISTORY) history.pop();
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    loadHistory();
  } catch (e) {
    console.warn("Could not save to history:", e);
  }
}

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch { return []; }
}

function loadHistory() {
  const history = getHistory();
  const list    = document.getElementById("history-list");
  const btn     = document.getElementById("clear-history-btn");
  if (!list) return;

  if (history.length === 0) {
    list.innerHTML = `
      <div class="placeholder">
        <div class="placeholder__icon">📂</div>
        <p class="placeholder__text">Your previous analyses will appear here automatically.</p>
      </div>`;
    btn.style.display = "none";
    return;
  }

  btn.style.display = "";
  list.innerHTML = history.map(h => `
    <div class="history-item" onclick="loadHistoryItem(${h.id})">
      <div class="history-item__icon">📊</div>
      <div class="history-item__info">
        <div class="history-item__title">${escHtml(h.topCareer)} · ${escHtml(h.level)}</div>
        <div class="history-item__meta">${escHtml(h.date)} · Skills: ${h.skills.map(escHtml).join(", ")}</div>
      </div>
      <div class="history-item__score">Readiness: ${h.score}%</div>
    </div>
  `).join("");
}

function loadHistoryItem(id) {
  const history = getHistory();
  const item    = history.find(h => h.id === id);
  if (!item) return;
  state.analysis = item.data;
  showSkeleton(false);
  renderResults(item.data);
  scrollTo("results");
}

function clearAllHistory() {
  if (!confirm("Clear all saved analyses?")) return;
  localStorage.removeItem(HISTORY_KEY);
  loadHistory();
}

// ══ SKELETON ═════════════════════════════════════════════════════════════════
function showSkeleton(show) {
  const sk = document.getElementById("results-skeleton");
  if (!sk) return;
  if (show) {
    sk.classList.remove("hidden");
    document.getElementById("results-placeholder").classList.add("hidden");
  } else {
    sk.classList.add("hidden");
  }
}

// ══ UI HELPERS ════════════════════════════════════════════════════════════════
function setBtnLoading(btnId, textId, spinnerId, loading, text) {
  const btn    = document.getElementById(btnId);
  const txtEl  = document.getElementById(textId);
  const spinEl = document.getElementById(spinnerId);
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    if (txtEl)  txtEl.classList.add("hidden");
    if (spinEl) spinEl.classList.remove("hidden");
  } else {
    if (txtEl)  { txtEl.textContent = text || txtEl.textContent; txtEl.classList.remove("hidden"); }
    if (spinEl) spinEl.classList.add("hidden");
  }
}

function hideResultsStates() {
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-content").classList.add("hidden");
  document.getElementById("results-error").classList.add("hidden");
}

function showResultsError(msg) {
  hideResultsStates();
  showSkeleton(false);
  document.getElementById("results-error-text").textContent = msg;
  document.getElementById("results-error").classList.remove("hidden");
}

function demandBadge(demand = "") {
  const map = { "very high": "vh", "high": "h", "medium": "m", "low": "m" };
  const cls = map[demand.toLowerCase()] || "m";
  return `<span class="demand-badge demand-badge--${cls}">${escHtml(demand)}</span>`;
}

function scrollTo(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function fetchWithTimeout(url, options, timeoutMs = 20000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (e) {
    clearTimeout(id);
    throw e;
  }
}

function smoothNavScroll() {
  document.querySelectorAll(".nav__link").forEach(link => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (href && href.startsWith("#")) {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
}

window.addEventListener("scroll", () => {
  const nav = document.getElementById("nav");
  nav.style.boxShadow = window.scrollY > 20 ? "0 2px 40px rgba(0,0,0,0.5)" : "none";
}, { passive: true });
