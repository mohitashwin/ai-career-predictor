import os
import json
import re
import io
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

ANALYZE_CONFIG = {"temperature": 0.4, "max_output_tokens": 2500}
CHAT_CONFIG    = {"temperature": 0.7, "max_output_tokens": 600}
RESUME_CONFIG  = {"temperature": 0.3, "max_output_tokens": 1800}
MODEL_NAME     = "gemini-2.0-flash"

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

# ── File text extractors ──────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text.strip()
    except Exception as e:
        log.error("PDF extraction error: %s", e)
        return ""

def extract_text_from_docx(file_bytes):
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text.strip()
    except Exception as e:
        log.error("DOCX extraction error: %s", e)
        return ""

# ── Fallback responses ────────────────────────────────────────────────────────

def fallback_response(skills, interests, level):
    return {
        "career_paths": [
            {
                "title": "Software Engineer",
                "match_percentage": 85,
                "description": "Build software for India's booming IT sector. Demand is very high across TCS, Infosys, and fast-growing startups.",
                "salary_range": "₹6 LPA – ₹25 LPA",
                "demand": "Very High",
                "top_companies": ["TCS", "Infosys", "Wipro", "Google", "Microsoft"]
            },
            {
                "title": "Data Analyst",
                "match_percentage": 72,
                "description": "Analyse data to drive business decisions. Strong demand in fintech, e-commerce and healthcare sectors.",
                "salary_range": "₹4 LPA – ₹18 LPA",
                "demand": "High",
                "top_companies": ["Flipkart", "Paytm", "Razorpay", "Accenture", "Deloitte"]
            },
            {
                "title": "Product Manager",
                "match_percentage": 58,
                "description": "Lead product strategy at India's fastest-growing digital companies with strong cross-functional skills.",
                "salary_range": "₹12 LPA – ₹40 LPA",
                "demand": "High",
                "top_companies": ["Swiggy", "Zomato", "CRED", "Meesho", "PhonePe"]
            },
        ],
        "skill_gaps": [
            {"skill": "Data Structures & Algorithms", "importance": "Critical", "level_needed": "Intermediate", "current_level": 25},
            {"skill": "SQL & Databases",              "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Cloud AWS / Azure",            "importance": "High",     "level_needed": "Beginner",     "current_level": 10},
            {"skill": "Communication Skills",         "importance": "Medium",   "level_needed": "Intermediate", "current_level": 50},
        ],
        "courses": [
            {"title": "Python Bootcamp – Zero to Hero",    "platform": "Udemy",         "duration": "22 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True,  "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
            {"title": "Data Science & ML Program",         "platform": "Great Learning", "duration": "6 months", "difficulty": "Intermediate", "free": True,  "certificate": True,  "url": "https://www.mygreatlearning.com/academy"},
            {"title": "The Complete SQL Bootcamp",         "platform": "Udemy",         "duration": "9 hrs",    "difficulty": "Beginner",     "free": False, "certificate": True,  "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
            {"title": "AWS Cloud Practitioner Essentials", "platform": "Coursera",      "duration": "6 weeks",  "difficulty": "Beginner",     "free": False, "certificate": True,  "url": "https://www.coursera.org/learn/aws-cloud-practitioner-essentials"},
        ],
        "certifications": [
            {"title": "AWS Certified Cloud Practitioner",           "platform": "Amazon AWS",       "difficulty": "Beginner",     "value": "Very High", "url": "https://aws.amazon.com/certification/"},
            {"title": "Google Data Analytics Certificate",          "platform": "Coursera / Google","difficulty": "Beginner",     "value": "High",      "url": "https://grow.google/certificates/data-analytics/"},
            {"title": "Microsoft Azure Fundamentals (AZ-900)",      "platform": "Microsoft",        "difficulty": "Beginner",     "value": "Very High", "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
            {"title": "Meta Front-End Developer Certificate",       "platform": "Coursera / Meta",  "difficulty": "Intermediate", "value": "High",      "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
        ],
        "roadmap": [
            {
                "month": "Month 1-2", "focus": "Strengthen Core Skills",
                "tasks": ["Solve 50 DSA problems on LeetCode", "Complete SQL bootcamp on Udemy", "Build one Python mini-project"],
                "milestone": "Coding fluency"
            },
            {
                "month": "Month 3-4", "focus": "Build Portfolio Projects",
                "tasks": ["Deploy a full-stack web app", "Push 3+ projects to GitHub", "Write LinkedIn posts about your projects"],
                "milestone": "Portfolio ready"
            },
            {
                "month": "Month 5-6", "focus": "Job Readiness",
                "tasks": ["Apply on Naukri.com and LinkedIn", "Attend campus or off-campus drives", "Practice HR and technical mock interviews"],
                "milestone": "First offer"
            },
        ],
        "scores": {
            "job_readiness":   62,
            "career_match":    75,
            "learning_speed":  70,
        },
        "summary": (
            f"Based on your {level} experience with {', '.join(skills[:3]) if skills else 'your current skills'}, "
            "you are well-positioned for India's IT industry. Focus on DSA and cloud skills to maximise your CTC. "
            "This is demo data — set your GEMINI_API_KEY on Render for a personalised AI analysis."
        ),
    }

def fallback_resume_response():
    return {
        "extracted_skills": ["Python", "SQL", "Microsoft Excel", "Communication", "Problem Solving"],
        "recommended_roles": ["Data Analyst", "Business Analyst", "Software Engineer"],
        "missing_skills": ["Machine Learning", "Tableau / Power BI", "Cloud (AWS/Azure)", "Git & GitHub"],
        "resume_score": 58,
        "improvement_tips": [
            "Add quantified achievements (e.g., 'Improved efficiency by 30%')",
            "Include GitHub / Portfolio link prominently",
            "Use strong action verbs: Built, Designed, Optimized, Led",
            "Add a concise professional summary at the top",
            "List certifications with issuer name and year"
        ],
        "ats_keywords": ["Python", "SQL", "Data Analysis", "REST API", "Agile", "Git"],
        "strengths": ["Good educational background", "Relevant technical skills listed"],
    }

# ── Prompts ───────────────────────────────────────────────────────────────────

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
      "top_companies": ["company1", "company2", "company3", "company4", "company5"]
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
      "difficulty": "Beginner or Intermediate or Advanced",
      "free": true or false,
      "certificate": true or false,
      "url": "https://real-url.com"
    }}
  ],
  "certifications": [
    {{
      "title": "Certification name",
      "platform": "Issuing body",
      "difficulty": "Beginner or Intermediate or Advanced",
      "value": "Very High or High or Medium",
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
  "scores": {{
    "job_readiness": <0-100>,
    "career_match": <0-100>,
    "learning_speed": <0-100>
  }},
  "summary": "3-4 sentences personalised for Indian job market with salary in rupees."
}}

Rules:
- Exactly 3 career_paths ranked by match_percentage descending
- Exactly 4 skill_gaps
- Exactly 4 courses (prefer Udemy and Great Learning, use real URLs)
- Exactly 4 certifications most valuable for this profile
- Exactly 3 roadmap phases
- Salaries MUST be in Indian Rupees LPA format: ₹8 LPA – ₹20 LPA
- top_companies: mix Indian (TCS, Infosys, Wipro, HCL, Flipkart, Swiggy, Zomato, Ola, Paytm, CRED, Razorpay, Nykaa, Myntra, Meesho, PhonePe, BYJU's) and relevant MNCs (Google, Microsoft, Amazon, IBM, Accenture)
- job_readiness: honest score based on skill coverage for top career path
- career_match: how well skills+interests align with top career path
- learning_speed: estimate based on experience level (Beginner=40-60, Intermediate=55-75, Advanced=70-90)
- Output ONLY the JSON — nothing else
"""

RESUME_PROMPT = """
You are an expert Indian ATS (Applicant Tracking System) resume reviewer and career coach.

Analyse the following resume text extracted from a candidate's PDF or DOCX:

---RESUME START---
{resume_text}
---RESUME END---

Return ONLY one valid JSON object. No text before or after. No markdown. No code fences.

Schema:
{{
  "extracted_skills": ["skill1", "skill2", ...],
  "recommended_roles": ["role1", "role2", "role3"],
  "missing_skills": ["skill1", "skill2", "skill3", "skill4"],
  "resume_score": <0-100>,
  "improvement_tips": ["tip1", "tip2", "tip3", "tip4", "tip5"],
  "ats_keywords": ["keyword1", "keyword2", ...],
  "strengths": ["strength1", "strength2"],
  "experience_level": "Fresher or Junior or Mid or Senior",
  "top_career_match": "Job title that best matches this resume"
}}

Rules:
- extracted_skills: all technical and soft skills found in the resume
- recommended_roles: 3 best-fit Indian job roles
- missing_skills: 4 skills that would make this resume much stronger
- resume_score: ATS + content quality score (0-100), be honest
  - 80-100: Excellent, ready to apply
  - 60-79: Good, minor improvements needed
  - 40-59: Average, needs significant work
  - 0-39: Poor, major restructuring needed
- improvement_tips: 5 specific, actionable, India-job-market tips
- ats_keywords: important keywords missing or underused
- Output ONLY the JSON — nothing else
"""

CHAT_PROMPT = """
You are CareerBot, an expert Indian AI career advisor inside the CareerAI platform.
You help Indian students and professionals navigate the Indian IT job market.

Career analysis context:
{analysis_context}

Chat history:
{history}

User question: {question}

Reply in 2-4 plain sentences. Be specific to Indian companies, Indian salaries in LPA, 
and practical Indian job search advice (Naukri, LinkedIn, campus placements, off-campus drives).
No bullet points. No markdown. Be warm, encouraging and direct.
"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "CareerAI API running", "version": "3.0.0"})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL_NAME,
        "version": "3.0.0",
        "api_key_set": bool(GEMINI_API_KEY),
        "features": ["analyze", "resume-analyze", "chat", "certifications"]
    })

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
        log.warning("No API key — returning fallback")
        return jsonify(fallback_response(skills, interests, level))

    prompt = ANALYZE_PROMPT.format(
        skills    = ", ".join(skills)    if skills    else "not specified",
        interests = ", ".join(interests) if interests else "not specified",
        level     = level,
        goals     = goals or "get a good high-paying job in India",
    )

    try:
        response = get_model().generate_content(prompt, generation_config=ANALYZE_CONFIG)
        raw = response.text
        log.info("Analyze response (%d chars): %s", len(raw), raw[:200])
        parsed = extract_json(raw)

        if parsed and "career_paths" in parsed:
            # Ensure scores field exists
            if "scores" not in parsed:
                parsed["scores"] = {"job_readiness": 65, "career_match": 75, "learning_speed": 60}
            # Ensure certifications field exists
            if "certifications" not in parsed:
                parsed["certifications"] = fallback_response(skills, interests, level)["certifications"]
            return jsonify(parsed)

        log.warning("JSON parse failed — using fallback")
        return jsonify(fallback_response(skills, interests, level))

    except Exception as exc:
        log.error("Analyze error: %s", exc, exc_info=True)
        return jsonify(fallback_response(skills, interests, level))

@app.route("/api/resume-analyze", methods=["POST", "OPTIONS"])
def resume_analyze():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    file = request.files.get("resume")
    if not file:
        return jsonify({"error": "No file provided. Please upload a PDF or DOCX resume."}), 400

    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".doc")):
        return jsonify({"error": "Unsupported format. Please upload a PDF or DOCX file."}), 400

    file_bytes = file.read()
    if len(file_bytes) > 5 * 1024 * 1024:  # 5MB limit
        return jsonify({"error": "File too large. Please upload a file under 5MB."}), 400

    log.info("Resume analyze | file=%s size=%d", filename, len(file_bytes))

    if filename.endswith(".pdf"):
        resume_text = extract_text_from_pdf(file_bytes)
    else:
        resume_text = extract_text_from_docx(file_bytes)

    if not resume_text or len(resume_text.strip()) < 50:
        log.warning("Could not extract sufficient text from resume")
        return jsonify(fallback_resume_response())

    log.info("Extracted %d characters from resume", len(resume_text))

    if not GEMINI_API_KEY:
        return jsonify(fallback_resume_response())

    # Truncate very long resumes to avoid token limits
    truncated_text = resume_text[:6000] if len(resume_text) > 6000 else resume_text

    prompt = RESUME_PROMPT.format(resume_text=truncated_text)

    try:
        response = get_model().generate_content(prompt, generation_config=RESUME_CONFIG)
        raw = response.text
        log.info("Resume response (%d chars): %s", len(raw), raw[:200])
        parsed = extract_json(raw)

        if parsed and "resume_score" in parsed:
            return jsonify(parsed)

        log.warning("Resume parse failed — using fallback")
        return jsonify(fallback_resume_response())

    except Exception as exc:
        log.error("Resume analyze error: %s", exc, exc_info=True)
        return jsonify(fallback_resume_response())

@app.route("/api/certifications", methods=["GET"])
def certifications():
    """Return top Indian IT certifications regardless of profile."""
    certs = [
        {"title": "AWS Certified Solutions Architect",      "platform": "Amazon AWS",        "difficulty": "Intermediate", "value": "Very High", "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/"},
        {"title": "AWS Cloud Practitioner",                 "platform": "Amazon AWS",        "difficulty": "Beginner",     "value": "High",      "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/"},
        {"title": "Google Cloud Associate Engineer",        "platform": "Google Cloud",      "difficulty": "Intermediate", "value": "Very High", "url": "https://cloud.google.com/certification/cloud-engineer"},
        {"title": "Microsoft Azure Fundamentals (AZ-900)",  "platform": "Microsoft",         "difficulty": "Beginner",     "value": "High",      "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
        {"title": "Google Data Analytics Certificate",      "platform": "Google / Coursera", "difficulty": "Beginner",     "value": "High",      "url": "https://grow.google/certificates/data-analytics/"},
        {"title": "TensorFlow Developer Certificate",       "platform": "Google",            "difficulty": "Advanced",     "value": "Very High", "url": "https://www.tensorflow.org/certificate"},
        {"title": "Meta Front-End Developer Certificate",   "platform": "Meta / Coursera",   "difficulty": "Intermediate", "value": "High",      "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
        {"title": "Certified Kubernetes Administrator",     "platform": "CNCF",              "difficulty": "Advanced",     "value": "Very High", "url": "https://www.cncf.io/certification/cka/"},
    ]
    return jsonify({"certifications": certs})

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

    # Only send relevant parts of context to keep prompt concise
    context_text = ""
    if context:
        summary = context.get("summary", "")
        top_career = (context.get("career_paths") or [{}])[0].get("title", "")
        scores = context.get("scores", {})
        context_text = f"Summary: {summary}\nTop career path: {top_career}\nScores: {json.dumps(scores)}"
    else:
        context_text = "No analysis yet."

    prompt = CHAT_PROMPT.format(
        analysis_context = context_text,
        history          = history_text,
        question         = question,
    )

    try:
        response = get_model().generate_content(prompt, generation_config=CHAT_CONFIG)
        reply = (response.text or "").strip()
        if not reply:
            reply = "I couldn't generate a response. Please rephrase your question."
        log.info("Chat reply: %s", reply[:100])
        return jsonify({"reply": reply})
    except Exception as exc:
        log.error("Chat error: %s", exc, exc_info=True)
        return jsonify({"reply": f"Technical error: {str(exc)[:120]}. Please try again."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
