/* ══════════════════════════════════════════════════════════════════════════════
   CareerAI — Frontend Script
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Config ────────────────────────────────────────────────────────────────────
const API_BASE = "https://ai-career-predictor-2csq.onrender.com"; // ← Replace with your Render URL
// const API_BASE = "http://localhost:5000"; // uncomment for local dev

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  skills:    [],
  interests: [],
  level:     "Intermediate",
  analysis:  null,       // last successful analysis result
  chatHistory: [],       // [{role:'user'|'bot', content:'...'}]
};

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTagInput("skills");
  setupTagInput("interests");
  checkHealth();
  smoothNavScroll();
});

// ══ HEALTH CHECK ══════════════════════════════════════════════════════════════
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/api/health`);
    const d = await r.json();
    console.info("[CareerAI] Backend healthy:", d);
  } catch (e) {
    console.warn("[CareerAI] Backend not reachable – using demo fallback.");
  }
}

// ══ TAG INPUT SYSTEM ══════════════════════════════════════════════════════════
function setupTagInput(type) {
  const input = document.getElementById(`${type}-input`);
  const container = document.getElementById(`${type}-container`);

  // Click on container focuses input
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
  const list = type === "skills" ? state.skills : state.interests;
  const clean = value.trim();
  if (!clean || list.includes(clean)) return;

  list.push(clean);
  renderTags(type);

  // Clear input focus so placeholder doesn't re-show awkwardly
  const input = document.getElementById(`${type}-input`);
  input.value = "";
  input.focus();
}

function removeLastTag(type) {
  const list = type === "skills" ? state.skills : state.interests;
  if (list.length) {
    list.pop();
    renderTags(type);
  }
}

function removeTag(type, index) {
  const list = type === "skills" ? state.skills : state.interests;
  list.splice(index, 1);
  renderTags(type);
}

function renderTags(type) {
  const list = type === "skills" ? state.skills : state.interests;
  const container = document.getElementById(`${type}-container`);
  const input = document.getElementById(`${type}-input`);

  // Remove existing tags (keep input)
  container.querySelectorAll(".tag").forEach(t => t.remove());

  list.forEach((tag, i) => {
    const el = document.createElement("span");
    el.className = "tag";
    el.innerHTML = `${escHtml(tag)} <button class="tag__remove" onclick="removeTag('${type}',${i})">×</button>`;
    container.insertBefore(el, input);
  });
}

// ══ LEVEL ══════════════════════════════════════════════════════════════════════
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

  // UI: loading state
  setBtnLoading("analyze-btn", "analyze-btn-text", "analyze-spinner", true);
  hideResultsStates();
  scrollTo("results");

  const payload = {
    skills:    state.skills,
    interests: state.interests,
    level:     state.level,
    goals:     goals,
  };

  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    }, 30000);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    if (!data.career_paths) throw new Error("Invalid response structure");

    state.analysis = data;
    renderResults(data);

  } catch (err) {
    console.error("[CareerAI] Analysis error:", err);
    showResultsError("Analysis failed. Please check your connection and try again.");
  } finally {
    setBtnLoading("analyze-btn", "analyze-btn-text", "analyze-spinner", false, "Analyze My Career Path");
  }
}

function renderResults(data) {
  // Show container, hide placeholder/error
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-error").classList.add("hidden");
  const content = document.getElementById("results-content");
  content.classList.remove("hidden");

  // Summary
  document.getElementById("summary-text").textContent = data.summary || "";

  // Render each tab
  renderCareerPaths(data.career_paths || []);
  renderSkillGaps(data.skill_gaps || []);
  renderCourses(data.courses || []);
  renderRoadmap(data.roadmap || []);

  // Activate first tab
  switchTabById("career");

  // Animate progress bars after a brief delay
  setTimeout(animateAllBars, 200);

  // Update chat context
  state.chatHistory = [];
  document.getElementById("chat-messages").innerHTML = buildBotMessage(
    `Great news! I've analyzed your profile. You have strong alignment with roles like <strong>${
      (data.career_paths[0] || {}).title || "Software Developer"
    }</strong>. I'm ready to answer any follow-up questions about your career plan!`
  );
}

// ── Career Paths ──────────────────────────────────────────────────────────────
function renderCareerPaths(paths) {
  const container = document.getElementById("career-cards");
  container.innerHTML = paths.map(p => `
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
        <div class="meta-row">
          <span class="meta-label">Salary</span>
          <span class="meta-value">${escHtml(p.salary_range || "—")}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Demand</span>
          ${demandBadge(p.demand)}
        </div>
        <div class="meta-row">
          <span class="meta-label">Companies</span>
          <div class="companies">
            ${(p.top_companies || []).map(c => `<span class="co-tag">${escHtml(c)}</span>`).join("")}
          </div>
        </div>
      </div>
    </div>
  `).join("");
}

// ── Skill Gaps ────────────────────────────────────────────────────────────────
function renderSkillGaps(gaps) {
  const container = document.getElementById("skills-list");
  container.innerHTML = gaps.map(g => {
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
  const container = document.getElementById("courses-cards");
  container.innerHTML = courses.map(c => `
    <div class="course-card">
      <div class="course-card__top">
        <span class="course-platform">${escHtml(c.platform)}</span>
        <span class="${c.free ? "free-badge" : "paid-badge"}">${c.free ? "FREE" : "PAID"}</span>
      </div>
      <h4 class="course-card__title">${escHtml(c.title)}</h4>
      <div class="course-card__footer">
        <span class="course-duration">⏱ ${escHtml(c.duration)}</span>
        <a href="${escHtml(c.url || "#")}" target="_blank" rel="noopener" class="course-link">Enroll →</a>
      </div>
    </div>
  `).join("");
}

// ── Roadmap ───────────────────────────────────────────────────────────────────
function renderRoadmap(phases) {
  const container = document.getElementById("roadmap-list");
  container.innerHTML = phases.map(p => `
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

// ══ TABS ══════════════════════════════════════════════════════════════════════
function switchTab(btn, tabId) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("tab--active"));
  btn.classList.add("tab--active");
  switchTabById(tabId);
}

function switchTabById(tabId) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) {
    panel.classList.remove("hidden");
    // Re-animate bars when switching to skill tab
    if (tabId === "skills") setTimeout(animateAllBars, 100);
  }
}

// ══ PROGRESS BAR ANIMATION ════════════════════════════════════════════════════
function animateAllBars() {
  document.querySelectorAll("[data-width]").forEach(el => {
    el.style.width = el.dataset.width + "%";
  });
}

// ══ CHAT ══════════════════════════════════════════════════════════════════════
async function sendChat() {
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendUserMessage(msg);
  state.chatHistory.push({ role: "user", content: msg });

  // Hide suggestions after first real message
  document.getElementById("chat-suggestions").style.display = "none";

  // Typing indicator
  const typingId = appendTypingIndicator();
  setBtnLoading("chat-send-btn", "chat-send-text", "chat-send-spinner", true);

  const historyForAPI = state.chatHistory.slice(-8).map(m => ({
    role: m.role === "bot" ? "assistant" : "user",
    content: m.content,
  }));

  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message:          msg,
        history:          historyForAPI,
        analysis_context: state.analysis || {},
      }),
    }, 20000);

    removeTypingIndicator(typingId);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
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
  const text = btn.textContent.trim();
  document.getElementById("chat-input").value = text;
  sendChat();
}

// ── Chat DOM helpers ──────────────────────────────────────────────────────────
function appendUserMessage(text) {
  const messages = document.getElementById("chat-messages");
  messages.insertAdjacentHTML("beforeend", `
    <div class="msg msg--user">
      <div class="msg__avatar">😊</div>
      <div class="msg__bubble">${escHtml(text)}</div>
    </div>
  `);
  scrollMessages();
}

function appendBotMessage(text) {
  const messages = document.getElementById("chat-messages");
  messages.insertAdjacentHTML("beforeend", buildBotMessage(text));
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
  const messages = document.getElementById("chat-messages");
  messages.insertAdjacentHTML("beforeend", `
    <div class="msg msg--bot" id="${id}">
      <div class="msg__avatar">🤖</div>
      <div class="msg__bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
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

// ══ UI HELPERS ════════════════════════════════════════════════════════════════
function setBtnLoading(btnId, textId, spinnerId, loading, text) {
  const btn    = document.getElementById(btnId);
  const txtEl  = document.getElementById(textId);
  const spinEl = document.getElementById(spinnerId);

  btn.disabled = loading;
  if (loading) {
    if (txtEl) txtEl.classList.add("hidden");
    if (spinEl) spinEl.classList.remove("hidden");
  } else {
    if (txtEl) { txtEl.textContent = text || txtEl.textContent; txtEl.classList.remove("hidden"); }
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
  const errEl = document.getElementById("results-error");
  document.getElementById("results-error-text").textContent = msg;
  errEl.classList.remove("hidden");
}

function demandBadge(demand = "") {
  const map = {
    "very high": "vh",
    "high":      "h",
    "medium":    "m",
    "low":       "m",
  };
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

// ── Smooth nav links ──────────────────────────────────────────────────────────
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

// ── Nav shadow on scroll ──────────────────────────────────────────────────────
window.addEventListener("scroll", () => {
  const nav = document.getElementById("nav");
  if (window.scrollY > 20) {
    nav.style.boxShadow = "0 2px 40px rgba(0,0,0,0.5)";
  } else {
    nav.style.boxShadow = "none";
  }
}, { passive: true });
