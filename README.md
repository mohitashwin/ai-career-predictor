# 🧠 AI Career Path Predictor & Skill Gap Analyzer

A full-stack AI application that predicts career paths, analyzes skill gaps,
recommends courses, and provides a personalized learning roadmap — powered by Anthropic Claude.

---

## 📁 Project Structure

```
ai-career-predictor/
├── backend/
│   ├── app.py              ← Flask API server (main backend)
│   ├── requirements.txt    ← Python dependencies
│   └── .env.example        ← Environment variables template
│
├── frontend/
│   ├── index.html          ← Main UI page
│   ├── style.css           ← All styling (dark futuristic theme)
│   └── script.js           ← Frontend logic + API calls
│
└── README.md               ← This file
```

---

## 🔗 How Everything Connects

```
User fills form (HTML)
       ↓
JavaScript collects skills/interests
       ↓
fetch() → POST /api/analyze (Flask)
       ↓
Flask calls Anthropic Claude API
       ↓
Claude returns structured JSON
       ↓
Flask sends JSON to frontend
       ↓
JavaScript renders Career Cards, Skill Gaps, Courses, Roadmap
       ↓
User chats with CareerBot via /api/chat
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.8+
- An Anthropic API key (get one at https://console.anthropic.com)

---

### Step 1: Get Your API Key

1. Go to https://console.anthropic.com
2. Sign up / log in
3. Navigate to API Keys → Create Key
4. Copy your key

---

### Step 2: Set Up the Backend

```bash
# Navigate to backend folder
cd ai-career-predictor/backend

# Create a virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
# On Mac/Linux:
export ANTHROPIC_API_KEY="your-key-here"
# On Windows:
set ANTHROPIC_API_KEY=your-key-here

# Start the backend server
python app.py
```

You should see:
```
🚀 AI Career Predictor Backend running on http://localhost:5000
```

---

### Step 3: Open the Frontend

Option A — Simply open the HTML file:
```bash
open frontend/index.html
# or double-click index.html in your file explorer
```

Option B — Serve with Python (recommended):
```bash
cd ai-career-predictor/frontend
python -m http.server 8080
# Then open http://localhost:8080
```

---

### Step 4: Use the App

1. Add your skills (Python, Excel, Communication, etc.)
2. Add your interests (Data Analysis, AI, Finance, etc.)
3. Select your experience level
4. Optionally add career goals
5. Click "Analyze My Career Path"
6. Wait ~5-10 seconds for AI analysis
7. Explore Career Paths, Skill Gaps, Courses, and Roadmap tabs
8. Ask follow-up questions in the CareerBot chat

---

## 🌐 API Endpoints

| Method | Endpoint         | Description                          |
|--------|-----------------|--------------------------------------|
| POST   | /api/analyze    | Main career analysis endpoint        |
| POST   | /api/chat       | Chatbot conversation endpoint        |
| POST   | /api/skill-check| Quick skill relevance check          |
| GET    | /api/health     | Health check                         |

### /api/analyze — Request Body
```json
{
  "skills": ["Python", "SQL", "Excel"],
  "interests": ["Data Analysis", "Machine Learning"],
  "experience_level": "Intermediate",
  "goals": "High salary, remote work"
}
```

### /api/chat — Request Body
```json
{
  "message": "What salary can I expect as a Data Scientist?",
  "history": [
    {"role": "user", "content": "previous message"},
    {"role": "assistant", "content": "previous reply"}
  ]
}
```

---

## 📊 Sample Output

### Career Paths
```json
{
  "career_paths": [
    {
      "title": "Data Scientist",
      "match_score": 92,
      "description": "Build ML models and extract insights from data",
      "why_you": "Your Python + SQL + ML interest is a perfect foundation",
      "avg_salary": "$110,000 - $160,000",
      "growth_outlook": "Very High",
      "time_to_job_ready": "6-12 months"
    }
  ]
}
```

### Skill Gaps
```json
{
  "skill_gaps": [
    {
      "skill": "Machine Learning",
      "importance": "Critical",
      "current_level": "Beginner",
      "target_level": "Intermediate",
      "gap_size": "Large"
    }
  ]
}
```

---

## 🛠️ Customization

### Change the AI Model
In `backend/app.py`, modify:
```python
model="claude-sonnet-4-20250514"  # Change model here
```

### Add New Career Domains
Edit `CAREER_AGENT_SYSTEM_PROMPT` in `app.py` to specialize in specific industries.

### Change Backend Port
```python
app.run(debug=True, host="0.0.0.0", port=8000)  # Change port here
```
Then update `API_BASE` in `frontend/script.js`:
```javascript
const API_BASE = "http://localhost:8000/api";
```

---

## 🔒 Security Notes

- Never commit your `.env` file or expose your API key
- In production, add rate limiting and authentication
- Use HTTPS in production (disable debug mode)

---

## 📦 Tech Stack

| Layer     | Technology           |
|-----------|---------------------|
| AI        | Anthropic Claude     |
| Backend   | Python + Flask       |
| Frontend  | HTML + CSS + JS      |
| Fonts     | Syne + DM Sans       |
| Hosting   | Any (Render, Fly.io) |

---

## 🐛 Troubleshooting

**CORS Error**: Make sure `flask-cors` is installed and the backend is running.

**"Failed to fetch"**: Backend not running. Start with `python app.py`.

**JSON parse error**: Claude returned unexpected format. Check your API key is valid.

**No results showing**: Open browser console (F12) and check for JavaScript errors.

---

Built with ❤️ using Anthropic Claude
