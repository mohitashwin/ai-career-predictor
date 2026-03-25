from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# 🔑 Get API key from Render
API_KEY = os.environ.get("API_KEY")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"


def ask_ai(prompt):
    response = requests.post(
        URL,
        json={
            "contents": [{"parts": [{"text": prompt}]}]
        }
    )
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "AI response error"


# ✅ HOME (optional)
@app.route("/")
def home():
    return "AI Career Predictor Backend Running 🚀"


# ✅ ANALYZE
@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    skills = data.get("skills", [])
    interests = data.get("interests", [])
    experience = data.get("experience_level", "")
    goals = data.get("goals", "")

    prompt = f"""
    Suggest 3 career paths, skill gaps, and roadmap:

    Skills: {skills}
    Interests: {interests}
    Experience: {experience}
    Goals: {goals}
    """

    result = ask_ai(prompt)

    return jsonify({
        "success": True,
        "data": {
            "summary": result,
            "career_paths": [],
            "skill_gaps": [],
            "courses": [],
            "roadmap": []
        }
    })


# ✅ CHAT
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")

    reply = ask_ai(message)

    return jsonify({"success": True, "reply": reply})


# ✅ HEALTH
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
