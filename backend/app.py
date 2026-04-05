import os
import json
import re
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # allow all origins

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
log.info("API key present: %s", bool(GEMINI_API_KEY))
genai.configure(api_key=GEMINI_API_KEY)

ANALYZE_CONFIG = {"temperature": 0.4, "max_output_tokens": 2048}
CHAT_CONFIG    = {"temperature": 0.7, "max_output_tokens": 600}
MODEL_NAME     = "gemini-1.5-flash"

def get_model():
    return genai.GenerativeModel(MODEL_NAME)

def extract_json(raw):
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None

def fallback_response(skills, interests, level):
    return {
        "career_paths": [
            {"title": "Software Engineer",    "match_percentage": 85, "description": "Build software for India's booming IT sector. Demand is very high across TCS, Infosys, and startups.",         "salary_range": "₹6 LPA – ₹25 LPA",  "demand": "Very High", "top_companies": ["TCS", "Infosys", "Wipro"]},
            {"title": "Data Analyst",         "match_percentage": 72, "description": "Analyse data to drive business decisions. Strong demand in fintech and e-commerce sectors.",                    "salary_range": "₹4 LPA – ₹18 LPA",  "demand": "High",      "top_companies": ["Flipkart", "Paytm", "Razorpay"]},
            {"title": "Product Manager",      "match_percentage": 58, "description": "Lead product strategy at India's fastest-growing digital companies.",                                            "salary_range": "₹12 LPA – ₹40 LPA", "demand": "High",      "top_companies": ["Swiggy", "Zomato", "CRED"]},
        ],
        "skill_gaps": [
            {"skill": "Data Structures & Algorithms", "importance": "Critical", "level_needed": "Intermediate", "current_level": 25},
            {"skill": "SQL & Databases",              "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Cloud AWS / Azure",            "importance": "High",     "level_needed": "Beginner",     "current_level": 10},
            {"skill": "Communication Skills",         "importance": "Medium",   "level_needed": "Intermediate", "current_level": 50},
        ],
        "courses": [
            {"title": "Python Bootcamp – Zero to Hero",     "platform": "Udemy",         "duration": "22 hrs",   "free": False, "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
            {"title": "Data Science & ML Program",          "platform": "Great Learning", "duration": "6 months", "free": True,  "url": "https://www.mygreatlearning.com/academy"},
            {"title": "The Complete SQL Bootcamp",          "platform": "Udemy",         "duration": "9 hrs",    "free": False, "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
            {"title": "AWS Cloud Foundations",              "platform": "Great Learning", "duration": "8 weeks",  "free": True,  "url": "https://www.mygreatlearning.com/academy"},
        ],
        "roadmap": [
            {"month": "Month 1-2", "focus": "Strengthen Core Skills",   "tasks": ["Solve 50 DSA problems on LeetCode",  "Complete SQL bootcamp on Udemy",     "Build one Python mini-project"],               "milestone": "Coding fluency"},
            {"month": "Month 3-4", "focus": "Build Portfolio Projects", "tasks": ["Deploy a full-stack web app",         "Push projects to GitHub",            "Write LinkedIn posts about your projects"],    "milestone": "Portfolio ready"},
            {"month": "Month 5-6", "focus": "Job Readiness",           "tasks": ["Apply on Naukri.com and LinkedIn",    "Attend campus or off-campus drives", "Practice HR and technical mock interviews"],   "milestone": "First offer"},
        ],
        "summary": f"Based on your {level} experience with {', '.join(skills[:3]) if skills else 'your current skills'}, you are well-positioned for India's IT industry. Focus on DSA and cloud skills to maximise your CTC. This is demo data — your GEMINI_API_KEY on Render needs to be correctly set for a personalised AI analysis.",
    }

ANALYZE_PROMPT = """
You are an expert Indian career counsellor for the Indian IT and technology job market.

User profile:
Skills: {skills}
Interests: {interests}
Experience Level: {level}
Career Goals: {goals}

Return ONLY one valid JSON object. No text before or after. No markdown. No code fences.

Schema:
{{
  "career_paths": [
    {{
      "title": "Job title",
      "match_percentage": <0-100>,
      "description": "2 sentences about this role in India.",
      "salary_range": "₹X LPA – ₹Y LPA",
      "demand": "Very High or High or Medium or Low",
      "top_companies": ["Indian/MNC company", "company2", "company3"]
    }}
  ],
  "skill_gaps": [
    {{
      "skill": "Skill name",
      "importance": "Critical or High or Medium",
      "level_needed": "Beginner or Intermediate or Advanced",
      "current_level": <0-100>
    }}
  ],
  "courses": [
    {{
      "title": "Course title",
      "platform": "Udemy or Great Learning or NPTEL or Coursera",
      "duration": "X hrs or X weeks",
      "free": true or false,
      "url": "https://real-url.com"
    }}
  ],
  "roadmap": [
    {{
      "month": "Month 1-2",
      "focus": "Focus area",
      "tasks": ["task1", "task2", "task3"],
      "milestone": "Achievement"
    }}
  ],
  "summary": "3-4 sentences personalised for Indian job market with salary in rupees."
}}

Rules:
- Exactly 3 career_paths (ranked by match_percentage descending)
- Exactly 4 skill_gaps
- Exactly 4 courses (prefer Udemy and Great Learning, use real URLs)
- Exactly 3 roadmap phases
- Salaries MUST be in Indian Rupees LPA format like ₹8 LPA – ₹20 LPA
- Top companies: mix of Indian companies (TCS, Infosys, Wipro, HCL, Flipkart, Swiggy, Zomato, Ola, Paytm, CRED, Razorpay, Nykaa, Myntra) and relevant MNCs
- Output only the JSON — nothing else
"""

CHAT_PROMPT = """
You are CareerBot, an expert Indian AI career advisor inside the CareerAI platform.
You help Indian students and professionals with the Indian IT job market.

Career analysis context:
{analysis_context}

Chat history:
{history}

User question: {question}

Reply in 2-4 plain sentences. Focus on Indian companies, Indian salaries in LPA, and practical Indian job search advice (Naukri, LinkedIn, campus placements). No bullet points. No markdown.
"""

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "CareerAI API running", "version": "2.0.0"})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_NAME, "version": "2.0.0", "api_key_set": bool(GEMINI_API_KEY)})

@app.route("/api/test", methods=["GET"])
def test_gemini():
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not set on server"}), 500
    try:
        resp = get_model().generate_content("Say hello in one word.")
        return jsonify({"status": "ok", "gemini_reply": resp.text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    data      = request.get_json(silent=True) or {}
    skills    = data.get("skills", [])
    interests = data.get("interests", [])
    level     = data.get("level", "Intermediate")
    goals     = data.get("goals", "")
    log.info("Analyze | skills=%s level=%s", skills, level)
    if not GEMINI_API_KEY:
        return jsonify(fallback_response(skills, interests, level))
    prompt = ANALYZE_PROMPT.format(
        skills    = ", ".join(skills)    if skills    else "not specified",
        interests = ", ".join(interests) if interests else "not specified",
        level     = level,
        goals     = goals or "get a good job in India",
    )
    try:
        response = get_model().generate_content(prompt, generation_config=ANALYZE_CONFIG)
        raw = response.text
        log.info("Analyze response (%d chars): %s", len(raw), raw[:150])
        parsed = extract_json(raw)
        if parsed and "career_paths" in parsed:
            return jsonify(parsed)
        log.warning("Parse failed, using fallback")
        return jsonify(fallback_response(skills, interests, level))
    except Exception as exc:
        log.error("Analyze error: %s", exc, exc_info=True)
        return jsonify(fallback_response(skills, interests, level))

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    data     = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    history  = data.get("history") or []
    context  = data.get("analysis_context") or {}
    log.info("Chat | question: %s", question[:100])
    if not question:
        return jsonify({"error": "Empty message"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"reply": "CareerBot is offline. Please set GEMINI_API_KEY in your Render environment variables."})
    history_lines = []
    for m in history[-6:]:
        role    = str(m.get("role", "user")).capitalize()
        content = str(m.get("content", ""))
        history_lines.append(f"{role}: {content}")
    history_text = "\n".join(history_lines) or "No prior messages."
    context_text = json.dumps(context, indent=2) if context else "No analysis yet."
    prompt = CHAT_PROMPT.format(
        analysis_context = context_text,
        history          = history_text,
        question         = question,
    )
    try:
        log.info("Calling Gemini for chat response...")
        response = get_model().generate_content(prompt, generation_config=CHAT_CONFIG)
        reply = (response.text or "").strip()
        if not reply:
            reply = "I could not generate a response. Please rephrase your question."
        log.info("Chat reply: %s", reply[:100])
        return jsonify({"reply": reply})
    except Exception as exc:
        log.error("Chat error: %s", exc, exc_info=True)
        return jsonify({"reply": f"Technical error: {str(exc)[:100]}. Please try again."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
