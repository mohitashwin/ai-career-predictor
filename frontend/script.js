/**
 * AI Career Path Predictor — Frontend Logic
 * Connects to Flask backend at http://localhost:5000
 */

// ─── Config ───────────────────────────────────────────────
const API_BASE = "https://ai-career-predictor-2csq.onrender.com/api";

// ─── State ────────────────────────────────────────────────
const state = {
  skills: [],
  interests: [],
  chatHistory: [],
  analysisData: null,
};

// ──────────────────────────────────────────────────────────
// TAG INPUT SYSTEM
// ──────────────────────────────────────────────────────────

function initTagInput(inputId, tagsId, stateKey) {
  const input = document.getElementById(inputId);
  const container = document.getElementById(tagsId);
  const wrapper = document.getElementById(`${stateKey}-wrapper`);

  // Click wrapper → focus input
  wrapper?.addEventListener("click", () => input.focus());

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = input.value.trim().replace(/,$/, "");
      if (val) addTag(val, stateKey, container);
      input.value = "";
    }
    // Backspace to remove last tag
    if (e.key === "Backspace" && !input.value && state[stateKey].length > 0) {
      const last = state[stateKey].at(-1);
      removeTag(last, stateKey, container);
    }
  });

  // Also handle paste
  input.addEventListener("paste", (e) => {
    setTimeout(() => {
      const raw = input.value;
      const parts = raw.split(/[,\n]+/).map((s) => s.trim()).filter(Boolean);
      parts.forEach((p) => addTag(p, stateKey, container));
      input.value = "";
    }, 50);
  });
}

function addTag(value, stateKey, container) {
  value = value.trim();
  if (!value || state[stateKey].includes(value)) return;
  state[stateKey].push(value);

  const tag = document.createElement("div");
  tag.className = "tag";
  tag.innerHTML = `
    <span>${escHtml(value)}</span>
    <span class="tag-x" onclick="removeTag('${escHtml(value)}', '${stateKey}', this.parentElement.parentElement)">✕</span>
  `;
  container.appendChild(tag);
}

function removeTag(value, stateKey, container) {
  state[stateKey] = state[stateKey].filter((s) => s !== value);
  // Remove DOM element
  const tags = container.querySelectorAll(".tag");
  tags.forEach((t) => {
    if (t.querySelector("span")?.textContent === value) t.remove();
  });
}

function addQuickSkill(skill) {
  addTag(skill, "skills", document.getElementById("skills-tags"));
}
function addQuickInterest(interest) {
  addTag(interest, "interests", document.getElementById("interests-tags"));
}

// ──────────────────────────────────────────────────────────
// CAREER ANALYSIS
// ──────────────────────────────────────────────────────────

async function analyzeCareer() {
  // Validate
  if (state.skills.length === 0 && state.interests.length === 0) {
    showError("Please add at least one skill or interest before analyzing.");
    return;
  }

  const experience = document.querySelector('input[name="experience"]:checked')?.value || "Beginner";
  const goals = document.getElementById("goals-input").value.trim();

  // Show loading
  showLoading();
  disableForm(true);

  try {
    const response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skills: state.skills,
        interests: state.interests,
        experience_level: experience,
        goals: goals,
      }),
    });

    const result = await response.json();

    if (!result.success) throw new Error(result.error || "Analysis failed");

    state.analysisData = result.data;
    hideLoading();
    renderResults(result.data);
    document.getElementById("results").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    hideLoading();
    showError(`Error: ${err.message}. Make sure the backend is running on port 5000.`);
  } finally {
    disableForm(false);
  }
}

// ──────────────────────────────────────────────────────────
// RENDER RESULTS
// ──────────────────────────────────────────────────────────

function renderResults(data) {
  const section = document.getElementById("results");
  section.style.display = "block";

  // Summary
  document.getElementById("summary-text").textContent = data.summary || "";

  // Render each tab
  renderCareers(data.career_paths || []);
  renderSkillGaps(data.skill_gaps || []);
  renderCourses(data.courses || []);
  renderRoadmap(data.roadmap || []);

  // Activate first tab
  switchTab("careers");
}

// ── Career Paths ──
function renderCareers(paths) {
  const container = document.getElementById("careers-container");
  container.innerHTML = paths
    .map(
      (c, i) => `
    <div class="career-card" style="animation-delay:${i * 0.1}s">
      <div class="career-match">
        <div>
          <div class="match-score">${c.match_score}%</div>
          <div class="match-label">Match Score</div>
        </div>
        <div class="match-bar">
          <div class="match-fill" style="width:0%" data-width="${c.match_score}%"></div>
        </div>
      </div>
      <div class="career-title">${escHtml(c.title)}</div>
      <div class="career-desc">${escHtml(c.description)}</div>
      <div class="career-why">💡 ${escHtml(c.why_you)}</div>
      <div class="career-meta">
        <span class="meta-tag">💰 ${escHtml(c.avg_salary)}</span>
        <span class="meta-tag">📈 ${escHtml(c.growth_outlook)}</span>
        <span class="meta-tag">⏱ ${escHtml(c.time_to_job_ready)}</span>
      </div>
    </div>
  `
    )
    .join("");

  // Animate bars after render
  requestAnimationFrame(() => {
    document.querySelectorAll(".match-fill").forEach((el) => {
      el.style.width = el.dataset.width;
    });
  });
}

// ── Skill Gaps ──
const GAP_WIDTHS = { Large: "80%", Medium: "45%", Small: "20%" };
const GAP_CLASSES = { Large: "gap-large", Medium: "gap-medium", Small: "gap-small" };
const BADGE_CLASSES = {
  Critical: "badge-critical",
  High: "badge-high",
  Medium: "badge-medium",
  Low: "badge-medium",
};

function renderSkillGaps(gaps) {
  const container = document.getElementById("skills-container");
  container.innerHTML = gaps
    .map(
      (g) => `
    <div class="skill-item ${GAP_CLASSES[g.gap_size] || "gap-medium"}">
      <div>
        <div class="skill-name">${escHtml(g.skill)}</div>
        <div class="skill-levels">${escHtml(g.current_level)} → ${escHtml(g.target_level)}</div>
      </div>
      <div class="skill-bar-wrap">
        <div class="skill-bar-labels">
          <span>Current: ${escHtml(g.current_level)}</span>
          <span>Target: ${escHtml(g.target_level)}</span>
        </div>
        <div class="skill-bar">
          <div class="skill-fill" style="width:0%" data-width="${GAP_WIDTHS[g.gap_size] || "50%"}"></div>
        </div>
      </div>
      <div class="skill-badge ${BADGE_CLASSES[g.importance] || "badge-high"}">${escHtml(g.importance)}</div>
    </div>
  `
    )
    .join("");

  requestAnimationFrame(() => {
    document.querySelectorAll(".skill-fill").forEach((el) => {
      el.style.width = el.dataset.width;
    });
  });
}

// ── Courses ──
function renderCourses(courses) {
  const container = document.getElementById("courses-container");
  container.innerHTML = courses
    .map(
      (c) => `
    <div class="course-card">
      <div class="course-header">
        <span class="course-platform">${escHtml(c.platform)}</span>
        <span class="${c.free ? "course-free" : "course-paid"}">${c.free ? "FREE" : "Paid"}</span>
      </div>
      <div class="course-title">${escHtml(c.name)}</div>
      <div class="course-meta">
        <span>⏱ ${escHtml(c.duration)}</span>
        <span>📊 ${escHtml(c.level)}</span>
      </div>
      ${
        c.skills_covered?.length
          ? `<div class="course-skills">
          ${c.skills_covered.map((s) => `<span class="course-skill-tag">${escHtml(s)}</span>`).join("")}
        </div>`
          : ""
      }
    </div>
  `
    )
    .join("");
}

// ── Roadmap ──
function renderRoadmap(phases) {
  const container = document.getElementById("roadmap-container");
  container.innerHTML = phases
    .map(
      (p) => `
    <div class="roadmap-phase">
      <div class="phase-indicator">
        <div class="phase-dot">${p.phase}</div>
      </div>
      <div class="phase-body">
        <div class="phase-header">
          <div class="phase-title">${escHtml(p.title)}</div>
          <div class="phase-duration">${escHtml(p.duration)}</div>
        </div>
        <div class="phase-tasks">
          ${p.tasks
            .map(
              (t) => `
            <div class="phase-task">
              <span class="task-check">✓</span>
              <span>${escHtml(t)}</span>
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    </div>
  `
    )
    .join("");
}

// ──────────────────────────────────────────────────────────
// TABS
// ──────────────────────────────────────────────────────────

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach((t) => t.classList.remove("active"));

  document.querySelector(`[data-tab="${tabName}"]`)?.classList.add("active");
  document.getElementById(`tab-${tabName}`)?.classList.add("active");
}

// ──────────────────────────────────────────────────────────
// CHATBOT
// ──────────────────────────────────────────────────────────

async function sendChat() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  document.getElementById("chat-suggestions").style.display = "none";

  // Add user message
  appendChatMessage("user", message, "🧑");
  state.chatHistory.push({ role: "user", content: message });

  // Thinking indicator
  const thinkingId = showThinking();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: state.chatHistory,
      }),
    });

    const data = await res.json();
    removeThinking(thinkingId);

    if (data.success) {
      appendChatMessage("bot", data.reply, "🤖");
      state.chatHistory.push({ role: "assistant", content: data.reply });
    } else {
      appendChatMessage("bot", `Sorry, there was an error: ${data.error}`, "🤖");
    }
  } catch (err) {
    removeThinking(thinkingId);
    appendChatMessage(
      "bot",
      "I couldn't connect to the backend. Make sure the Flask server is running on port 5000.",
      "🤖"
    );
  }
}

function sendSuggestion(btn) {
  document.getElementById("chat-input").value = btn.textContent;
  sendChat();
}

function appendChatMessage(role, text, avatar) {
  const messagesDiv = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">${escHtml(text)}</div>
  `;
  messagesDiv.appendChild(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function showThinking() {
  const id = "thinking-" + Date.now();
  const messagesDiv = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "chat-msg bot thinking";
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>
  `;
  messagesDiv.appendChild(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return id;
}

function removeThinking(id) {
  document.getElementById(id)?.remove();
}

// ──────────────────────────────────────────────────────────
// UI HELPERS
// ──────────────────────────────────────────────────────────

function showLoading() {
  const overlay = document.getElementById("loading-overlay");
  overlay.style.display = "flex";

  // Animate loading steps
  const steps = ["ls-1", "ls-2", "ls-3", "ls-4"];
  steps.forEach((id, i) => {
    const el = document.getElementById(id);
    el.classList.remove("active", "done");
    setTimeout(() => {
      steps.slice(0, i).forEach((prev) => {
        document.getElementById(prev).classList.remove("active");
        document.getElementById(prev).classList.add("done");
      });
      el.classList.add("active");
    }, i * 1500);
  });
}

function hideLoading() {
  document.getElementById("loading-overlay").style.display = "none";
}

function disableForm(disabled) {
  const btn = document.getElementById("analyze-btn");
  btn.disabled = disabled;
  btn.querySelector(".btn-text").textContent = disabled
    ? "Analyzing..."
    : "Analyze My Career Path";
}

function showError(message) {
  let banner = document.getElementById("error-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "error-banner";
    banner.className = "error-banner";
    document.getElementById("analyzer").prepend(banner);
  }
  banner.textContent = message;
  banner.classList.add("show");
  setTimeout(() => banner.classList.remove("show"), 6000);
}

function escHtml(str) {
  if (typeof str !== "string") return String(str ?? "");
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ──────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initTagInput("skills-input", "skills-tags", "skills");
  initTagInput("interests-input", "interests-tags", "interests");

  // Smooth nav link highlighting
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", function () {
      document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
      this.classList.add("active");
    });
  });

  console.log("🚀 AI Career Predictor loaded. Backend at:", API_BASE);
});
