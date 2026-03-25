"""
AI Career Path Predictor & Skill Gap Analyzer
Backend: Flask API with Anthropic Claude integration
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import json
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to call this backend

# Initialize Anthropic client
# Set your API key: export ANTHROPIC_API_KEY="your-key-here"
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT — defines the AI agent's behavior
# ─────────────────────────────────────────────────────────────
CAREER_AGENT_SYSTEM_PROMPT = """
You are an expert Career Path Advisor and Skill Gap Analyst AI. 
Your job is to help users discover ideal career paths and understand 
what skills they need to reach their goals.

When a user provides their current skills and interests, you MUST respond 
with a JSON object (no markdown, no extra text) in this EXACT format:

{
  "career_paths": [
    {
      "title": "Career Title",
      "match_score": 92,
      "description": "Brief description of this career path",
      "why_you": "Why this fits this specific user's profile",
      "avg_salary": "$95,000 - $140,000",
      "growth_outlook": "Very High",
      "time_to_job_ready": "6-12 months"
    }
  ],
  "skill_gaps": [
    {
      "skill": "Skill Name",
      "importance": "Critical",
      "current_level": "Beginner",
      "target_level": "Intermediate",
      "gap_size": "Large"
    }
  ],
  "courses": [
    {
      "name": "Course Name",
      "platform": "Platform Name",
      "duration": "X hours",
      "level": "Beginner/Intermediate/Advanced",
      "free": true,
      "url_hint": "search term to find it",
      "skills_covered": ["skill1", "skill2"]
    }
  ],
  "roadmap": [
    {
      "phase": 1,
      "title": "Phase Title",
      "duration": "1-2 months",
      "tasks": ["Task 1", "Task 2", "Task 3"]
    }
  ],
  "summary": "A personalized 2-3 sentence summary of the user's career outlook"
}

Provide exactly 3 career paths, 5 skill gaps, 4 courses, and 3 roadmap phases.
Match everything tightly to the user's actual skills and interests.
"""

CHATBOT_SYSTEM_PROMPT = """
You are a friendly, expert Career Counselor AI chatbot named "CareerBot".
You help users navigate career decisions, explain skill gaps, suggest learning paths,
and answer questions about job markets and career growth.

Be conversational, encouraging, and specific. Reference tech trends.
Keep responses concise but insightful (3-5 sentences max unless detail is needed).
If asked about specific skills, give concrete advice.
"""


# ─────────────────────────────────────────────────────────────
# ROUTE 1: Career Analysis
# ─────────────────────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze_career():
    """
    Accepts user skills & interests, returns career paths + skill gaps.
    Body: { "skills": [...], "interests": [...], "experience_level": "..." }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    skills = data.get("skills", [])
    interests = data.get("interests", [])
    experience = data.get("experience_level", "Beginner")
    goals = data.get("goals", "")

    if not skills and not interests:
        return jsonify({"error": "Please provide at least skills or interests"}), 400

    # Build user message
    user_message = f"""
Analyze this user's profile and provide career recommendations:

Current Skills: {', '.join(skills) if skills else 'None specified'}
Interests/Passions: {', '.join(interests) if interests else 'None specified'}
Experience Level: {experience}
Career Goals: {goals if goals else 'Open to suggestions'}

Provide a complete career analysis in the required JSON format.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=CAREER_AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = message.content[0].text.strip()

        # Parse JSON response
        result = json.loads(response_text)
        return jsonify({"success": True, "data": result})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse AI response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# ROUTE 2: Chatbot
# ─────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Chatbot endpoint for follow-up Q&A.
    Body: { "message": "...", "history": [...] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # Build conversation history
    messages = []
    for h in history[-10:]:  # Keep last 10 messages for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=CHATBOT_SYSTEM_PROMPT,
            messages=messages,
        )

        reply = response.content[0].text
        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# ROUTE 3: Quick Skill Check
# ─────────────────────────────────────────────────────────────
@app.route("/api/skill-check", methods=["POST"])
def skill_check():
    """
    Returns a quick assessment of a single skill's market value.
    Body: { "skill": "Python", "career": "Data Science" }
    """
    data = request.get_json()
    skill = data.get("skill", "")
    career = data.get("career", "")

    prompt = f"""
Rate the skill "{skill}" for a career in "{career}".
Respond in JSON only:
{{
  "relevance_score": 85,
  "demand_level": "High",
  "description": "One sentence about this skill's importance",
  "related_skills": ["skill1", "skill2", "skill3"]
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        result = json.loads(response.content[0].text.strip())
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# ROUTE 4: Health Check
# ─────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Career Predictor API"})


if __name__ == "__main__":
    print("🚀 AI Career Predictor Backend running on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
