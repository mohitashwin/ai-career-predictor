import os
import json
import re
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    log.warning("GEMINI_API_KEY is not set – AI features will return fallback data.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict | None:
    """Strip markdown fences and return parsed JSON, or None."""
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: find first { ... } block
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def fallback_response(skills: list, interests: list, level: str) -> dict:
    """Return a safe, structured fallback when Gemini fails or is unavailable."""
    return {
        "career_paths": [
            {
                "title": "Software Developer",
                "match_percentage": 80,
                "description": "Build scalable applications using your existing technical skills.",
                "salary_range": "$70,000 – $130,000",
                "demand": "Very High",
                "top_companies": ["Google", "Microsoft", "Amazon"],
            },
            {
                "title": "Data Analyst",
                "match_percentage": 70,
                "description": "Turn raw data into actionable business insights.",
                "salary_range": "$60,000 – $110,000",
                "demand": "High",
                "top_companies": ["Meta", "Netflix", "Spotify"],
            },
            {
                "title": "Product Manager",
                "match_percentage": 55,
                "description": "Lead cross-functional teams to ship great products.",
                "salary_range": "$90,000 – $150,000",
                "demand": "High",
                "top_companies": ["Apple", "Airbnb", "Stripe"],
            },
        ],
        "skill_gaps": [
            {"skill": "System Design", "importance": "Critical", "level_needed": "Intermediate", "current_level": 20},
            {"skill": "Cloud (AWS/GCP)", "importance": "High", "level_needed": "Beginner", "current_level": 10},
            {"skill": "SQL & Databases", "importance": "High", "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Communication", "importance": "Medium", "level_needed": "Intermediate", "current_level": 50},
        ],
        "courses": [
            {"title": "CS50 – Introduction to Computer Science", "platform": "edX", "duration": "12 weeks", "free": True, "url": "https://cs50.harvard.edu"},
            {"title": "Google Data Analytics Certificate", "platform": "Coursera", "duration": "6 months", "free": False, "url": "https://coursera.org"},
            {"title": "AWS Cloud Practitioner", "platform": "AWS", "duration": "8 weeks", "free": False, "url": "https://aws.amazon.com/training"},
            {"title": "SQL for Data Science", "platform": "Coursera", "duration": "4 weeks", "free": True, "url": "https://coursera.org"},
        ],
        "roadmap": [
            {"month": "Month 1–2", "focus": "Strengthen Core Skills", "tasks": ["Review data structures", "Practice 50 LeetCode problems", "Complete SQL basics"], "milestone": "Coding fluency"},
            {"month": "Month 3–4", "focus": "Build Projects", "tasks": ["Deploy a full-stack app", "Contribute to open source", "Create a portfolio site"], "milestone": "First public project"},
            {"month": "Month 5–6", "focus": "Job Readiness", "tasks": ["Optimise LinkedIn & resume", "Apply to 20+ positions", "Mock interviews"], "milestone": "First offer"},
        ],
        "summary": f"Based on your {level} experience with {', '.join(skills[:3]) if skills else 'various skills'}, you have strong potential across tech roles.",
    }


ANALYZE_PROMPT = """
You are a professional career counsellor with deep knowledge of the global job market.
A user has provided the following profile:

Skills: {skills}
Interests: {interests}
Experience Level: {level}
Career Goals: {goals}

Return ONLY a single valid JSON object — no prose, no markdown, no code fences.
The JSON must EXACTLY match this schema:

{{
  "career_paths": [
    {{
      "title": "string",
      "match_percentage": integer (0-100),
      "description": "string (2 sentences)",
      "salary_range": "string e.g. $70,000 – $120,000",
      "demand": "string: Very High | High | Medium | Low",
      "top_companies": ["string", "string", "string"]
    }}
  ],
  "skill_gaps": [
    {{
      "skill": "string",
      "importance": "string: Critical | High | Medium",
      "level_needed": "string: Beginner | Intermediate | Advanced",
      "current_level": integer (0-100, estimated from profile)
    }}
  ],
  "courses": [
    {{
      "title": "string",
      "platform": "string",
      "duration": "string",
      "free": boolean,
      "url": "string"
    }}
  ],
  "roadmap": [
    {{
      "month": "string e.g. Month 1-2",
      "focus": "string",
      "tasks": ["string", "string", "string"],
      "milestone": "string"
    }}
  ],
  "summary": "string (3-4 sentence personalised overview)"
}}

Rules:
- Return exactly 3 career_paths ranked by match_percentage descending.
- Return exactly 4-5 skill_gaps most critical for those careers.
- Return exactly 4 courses directly addressing the skill_gaps.
- Return exactly 3 roadmap phases spanning 6 months.
- All strings must be professional, specific, and personalised to the profile.
- DO NOT include any text outside the JSON object.
"""


CHAT_PROMPT = """
You are CareerBot, an expert AI career advisor embedded in CareerAI — a professional career intelligence platform.
You have access to the user's career analysis:

{analysis_context}

Chat history so far:
{history}

User's new question: {question}

Reply in 2-4 sentences. Be specific, actionable, and encouraging.
Do NOT use bullet points or markdown. Plain conversational text only.
"""

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": "gemini-1.5-flash", "version": "2.0.0"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    skills    = data.get("skills", [])
    interests = data.get("interests", [])
    level     = data.get("level", "Intermediate")
    goals     = data.get("goals", "")

    log.info("Analyze request | skills=%s | interests=%s | level=%s", skills, interests, level)

    if not GEMINI_API_KEY:
        log.warning("No API key – returning fallback.")
        return jsonify(fallback_response(skills, interests, level))

    prompt = ANALYZE_PROMPT.format(
        skills=", ".join(skills) if skills else "not specified",
        interests=", ".join(interests) if interests else "not specified",
        level=level,
        goals=goals or "not specified",
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )
        raw = response.text
        log.debug("Raw Gemini response: %s", raw[:300])

        parsed = extract_json(raw)
        if parsed and "career_paths" in parsed:
            log.info("Successfully parsed Gemini response.")
            return jsonify(parsed)

        log.warning("JSON parse failed – using fallback. Raw snippet: %s", raw[:200])
        return jsonify(fallback_response(skills, interests, level))

    except Exception as exc:
        log.error("Gemini API error: %s", exc, exc_info=True)
        return jsonify(fallback_response(skills, interests, level))


@app.route("/api/chat", methods=["POST"])
def chat():
    data     = request.get_json(silent=True) or {}
    question = data.get("message", "").strip()
    history  = data.get("history", [])          # list of {role, content}
    context  = data.get("analysis_context", {})

    log.info("Chat request | question=%s", question[:80])

    if not question:
        return jsonify({"error": "Empty message"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"reply": "CareerBot is currently offline. Please add your GEMINI_API_KEY to the backend .env file."})

    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in history[-6:]
    ) or "No prior messages."

    context_text = json.dumps(context, indent=2) if context else "No analysis performed yet."

    prompt = CHAT_PROMPT.format(
        analysis_context=context_text,
        history=history_text,
        question=question,
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=512,
            ),
        )
        reply = response.text.strip()
        log.info("Chat reply generated (%d chars)", len(reply))
        return jsonify({"reply": reply})

    except Exception as exc:
        log.error("Chat API error: %s", exc, exc_info=True)
        return jsonify({"reply": "I'm having trouble connecting right now. Please try again in a moment."}), 200


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
