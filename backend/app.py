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

# ── Smart Fallback responses ──────────────────────────────────────────────────

# Skill → career domain mapping
SKILL_DOMAINS = {
    "web":     ["html", "css", "javascript", "react", "angular", "vue", "nodejs", "node.js", "express", "django", "flask", "php", "bootstrap", "tailwind", "typescript"],
    "data":    ["python", "sql", "pandas", "numpy", "matplotlib", "tableau", "power bi", "excel", "r", "statistics", "data analysis", "etl", "spark"],
    "ml":      ["machine learning", "deep learning", "tensorflow", "keras", "pytorch", "scikit-learn", "nlp", "computer vision", "ai", "neural network", "llm"],
    "mobile":  ["android", "ios", "flutter", "react native", "kotlin", "swift", "dart", "xamarin"],
    "cloud":   ["aws", "azure", "gcp", "docker", "kubernetes", "devops", "terraform", "jenkins", "ci/cd", "linux"],
    "backend": ["java", "c++", "c#", "golang", "go", "rust", "spring", "microservices", "rest api", "graphql"],
    "security":["cybersecurity", "ethical hacking", "network security", "penetration testing", "siem", "firewall"],
}

CAREER_PROFILES = {
    "web": {
        "title": "Full Stack Web Developer",
        "description": "Build end-to-end web applications for India's booming startup and IT ecosystem. Companies like Flipkart, Swiggy and Razorpay hire full stack developers at all levels.",
        "salary_range": "₹5 LPA – ₹22 LPA",
        "demand": "Very High",
        "top_companies": ["Flipkart", "Swiggy", "Razorpay", "TCS", "Infosys"],
        "gaps": [
            {"skill": "System Design", "importance": "Critical", "level_needed": "Intermediate", "current_level": 20},
            {"skill": "TypeScript",    "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Docker & CI/CD","importance": "High",     "level_needed": "Beginner",     "current_level": 15},
            {"skill": "SQL & Databases","importance": "Medium",  "level_needed": "Intermediate", "current_level": 40},
        ],
        "courses": [
            {"title": "The Complete Web Developer Bootcamp",  "platform": "Udemy",         "duration": "65 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-web-development-bootcamp/"},
            {"title": "Full Stack Development Program",       "platform": "Great Learning", "duration": "6 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "React – The Complete Guide",           "platform": "Udemy",         "duration": "48 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/"},
            {"title": "Node.js, Express & MongoDB Bootcamp",  "platform": "Udemy",         "duration": "42 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/nodejs-express-mongodb-bootcamp/"},
        ],
        "certs": [
            {"title": "Meta Front-End Developer Certificate",  "platform": "Coursera / Meta",    "difficulty": "Intermediate", "value": "Very High", "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
            {"title": "AWS Certified Developer – Associate",   "platform": "Amazon AWS",         "difficulty": "Intermediate", "value": "Very High", "url": "https://aws.amazon.com/certification/certified-developer-associate/"},
            {"title": "Google UX Design Certificate",          "platform": "Coursera / Google",  "difficulty": "Beginner",     "value": "High",      "url": "https://grow.google/certificates/ux-design/"},
            {"title": "Microsoft Azure Fundamentals (AZ-900)", "platform": "Microsoft",          "difficulty": "Beginner",     "value": "High",      "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
        ],
        "roadmap_focus": ["Master React & Node.js", "Build 3 full-stack portfolio projects", "Deploy on AWS and crack FAANG interviews"],
    },
    "data": {
        "title": "Data Analyst",
        "description": "Analyse business data to drive decisions across fintech, e-commerce and healthcare. India's data economy is growing at 25% YoY with strong demand on platforms like Naukri.",
        "salary_range": "₹4 LPA – ₹18 LPA",
        "demand": "Very High",
        "top_companies": ["Flipkart", "Paytm", "Accenture", "Deloitte", "HDFC Bank"],
        "gaps": [
            {"skill": "Advanced SQL",         "importance": "Critical", "level_needed": "Advanced",      "current_level": 30},
            {"skill": "Tableau / Power BI",   "importance": "High",     "level_needed": "Intermediate",  "current_level": 20},
            {"skill": "Python – Pandas/NumPy","importance": "High",     "level_needed": "Intermediate",  "current_level": 35},
            {"skill": "Statistics & Prob.",   "importance": "Medium",   "level_needed": "Intermediate",  "current_level": 40},
        ],
        "courses": [
            {"title": "Google Data Analytics Certificate",    "platform": "Coursera",      "duration": "6 months", "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://grow.google/certificates/data-analytics/"},
            {"title": "Data Science & ML Program",            "platform": "Great Learning", "duration": "6 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "The Complete SQL Bootcamp",            "platform": "Udemy",         "duration": "9 hrs",    "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
            {"title": "Tableau for Data Science",             "platform": "Udemy",         "duration": "17 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/tableau10/"},
        ],
        "certs": [
            {"title": "Google Data Analytics Certificate",        "platform": "Coursera / Google", "difficulty": "Beginner",     "value": "Very High", "url": "https://grow.google/certificates/data-analytics/"},
            {"title": "Microsoft Power BI Data Analyst (PL-300)", "platform": "Microsoft",         "difficulty": "Intermediate", "value": "Very High", "url": "https://learn.microsoft.com/en-us/certifications/power-bi-data-analyst-associate/"},
            {"title": "AWS Certified Cloud Practitioner",         "platform": "Amazon AWS",        "difficulty": "Beginner",     "value": "High",      "url": "https://aws.amazon.com/certification/"},
            {"title": "IBM Data Analyst Professional Certificate","platform": "Coursera / IBM",    "difficulty": "Beginner",     "value": "High",      "url": "https://www.coursera.org/professional-certificates/ibm-data-analyst"},
        ],
        "roadmap_focus": ["Master SQL and Python for data wrangling", "Build 2 dashboards with Tableau/Power BI", "Apply on Naukri and crack analytics interviews"],
    },
    "ml": {
        "title": "Machine Learning Engineer",
        "description": "Design and deploy ML models for India's AI-first companies. Demand is surging across Bangalore, Hyderabad and Chennai with top salaries at product companies.",
        "salary_range": "₹8 LPA – ₹35 LPA",
        "demand": "Very High",
        "top_companies": ["Google", "Microsoft", "Amazon", "CRED", "PhonePe"],
        "gaps": [
            {"skill": "MLOps & Model Deployment", "importance": "Critical", "level_needed": "Intermediate", "current_level": 15},
            {"skill": "Deep Learning / PyTorch",  "importance": "High",     "level_needed": "Intermediate", "current_level": 25},
            {"skill": "Cloud ML (AWS SageMaker)", "importance": "High",     "level_needed": "Beginner",     "current_level": 10},
            {"skill": "Statistics & Probability", "importance": "Medium",   "level_needed": "Advanced",     "current_level": 35},
        ],
        "courses": [
            {"title": "Machine Learning A-Z",                   "platform": "Udemy",         "duration": "44 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/machinelearning/"},
            {"title": "Deep Learning Specialization",           "platform": "Coursera",      "duration": "3 months", "difficulty": "Advanced",     "free": False, "certificate": True, "url": "https://www.coursera.org/specializations/deep-learning"},
            {"title": "AI & ML Program",                        "platform": "Great Learning", "duration": "6 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "PyTorch for Deep Learning Bootcamp",     "platform": "Udemy",         "duration": "22 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/pytorch-for-deep-learning/"},
        ],
        "certs": [
            {"title": "TensorFlow Developer Certificate",           "platform": "Google",           "difficulty": "Intermediate", "value": "Very High", "url": "https://www.tensorflow.org/certificate"},
            {"title": "AWS Certified ML – Specialty",               "platform": "Amazon AWS",       "difficulty": "Advanced",     "value": "Very High", "url": "https://aws.amazon.com/certification/certified-machine-learning-specialty/"},
            {"title": "IBM Machine Learning Professional Certificate","platform": "Coursera / IBM",  "difficulty": "Intermediate", "value": "High",      "url": "https://www.coursera.org/professional-certificates/ibm-machine-learning"},
            {"title": "Google Cloud Professional ML Engineer",      "platform": "Google Cloud",     "difficulty": "Advanced",     "value": "Very High", "url": "https://cloud.google.com/certification/machine-learning-engineer"},
        ],
        "roadmap_focus": ["Build end-to-end ML pipelines with Python", "Deploy models using Flask/FastAPI on AWS", "Contribute to Kaggle and publish on GitHub"],
    },
    "mobile": {
        "title": "Mobile App Developer",
        "description": "Build Android/iOS apps for India's 700M+ smartphone users. Startups like Meesho, ShareChat and Ola hire mobile developers aggressively.",
        "salary_range": "₹5 LPA – ₹20 LPA",
        "demand": "High",
        "top_companies": ["Meesho", "ShareChat", "Ola", "Nykaa", "BYJU's"],
        "gaps": [
            {"skill": "Flutter / Dart",        "importance": "Critical", "level_needed": "Intermediate", "current_level": 20},
            {"skill": "REST API Integration",  "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Firebase & Push Notif.","importance": "High",     "level_needed": "Beginner",     "current_level": 15},
            {"skill": "Play Store Deployment", "importance": "Medium",   "level_needed": "Beginner",     "current_level": 10},
        ],
        "courses": [
            {"title": "Flutter & Dart – Complete Guide",        "platform": "Udemy",         "duration": "42 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/learn-flutter-dart-to-build-ios-android-apps/"},
            {"title": "Android Development Bootcamp",           "platform": "Udemy",         "duration": "27 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-android-oreo-developer-course/"},
            {"title": "Mobile App Development Program",         "platform": "Great Learning", "duration": "4 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "React Native – Practical Guide",         "platform": "Udemy",         "duration": "36 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/react-native-the-practical-guide/"},
        ],
        "certs": [
            {"title": "Google Associate Android Developer",     "platform": "Google",           "difficulty": "Intermediate", "value": "Very High", "url": "https://developers.google.com/certification/associate-android-developer"},
            {"title": "AWS Certified Cloud Practitioner",       "platform": "Amazon AWS",       "difficulty": "Beginner",     "value": "High",      "url": "https://aws.amazon.com/certification/"},
            {"title": "Meta Front-End Developer Certificate",   "platform": "Coursera / Meta",  "difficulty": "Intermediate", "value": "High",      "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
            {"title": "Microsoft Azure Fundamentals (AZ-900)",  "platform": "Microsoft",        "difficulty": "Beginner",     "value": "High",      "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
        ],
        "roadmap_focus": ["Master Flutter and publish an app on Play Store", "Integrate APIs and Firebase into your app", "Apply to mobile-first startups on LinkedIn and AngelList"],
    },
    "cloud": {
        "title": "DevOps / Cloud Engineer",
        "description": "Manage cloud infrastructure and CI/CD pipelines for India's fast-scaling tech companies. AWS and Azure certified engineers command premium salaries across Bangalore and Pune.",
        "salary_range": "₹7 LPA – ₹28 LPA",
        "demand": "Very High",
        "top_companies": ["Wipro", "HCL", "Infosys", "Amazon", "Microsoft"],
        "gaps": [
            {"skill": "Kubernetes & Docker", "importance": "Critical", "level_needed": "Intermediate", "current_level": 20},
            {"skill": "Terraform / IaC",     "importance": "High",     "level_needed": "Intermediate", "current_level": 15},
            {"skill": "CI/CD – Jenkins/GitHub Actions", "importance": "High", "level_needed": "Beginner", "current_level": 25},
            {"skill": "Monitoring – Grafana/Prometheus", "importance": "Medium", "level_needed": "Beginner", "current_level": 10},
        ],
        "courses": [
            {"title": "AWS Certified Solutions Architect",      "platform": "Udemy",         "duration": "27 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/"},
            {"title": "Docker & Kubernetes Bootcamp",           "platform": "Udemy",         "duration": "23 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/"},
            {"title": "DevOps Program",                         "platform": "Great Learning", "duration": "5 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "Linux Command Line Bootcamp",            "platform": "Udemy",         "duration": "15 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-linux-command-line-bootcamp/"},
        ],
        "certs": [
            {"title": "AWS Certified Solutions Architect – Associate", "platform": "Amazon AWS",  "difficulty": "Intermediate", "value": "Very High", "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/"},
            {"title": "Microsoft Azure Administrator (AZ-104)",        "platform": "Microsoft",   "difficulty": "Intermediate", "value": "Very High", "url": "https://learn.microsoft.com/en-us/certifications/azure-administrator/"},
            {"title": "Certified Kubernetes Administrator (CKA)",      "platform": "CNCF",        "difficulty": "Advanced",     "value": "Very High", "url": "https://www.cncf.io/certification/cka/"},
            {"title": "Google Cloud Associate Cloud Engineer",         "platform": "Google Cloud","difficulty": "Intermediate", "value": "High",      "url": "https://cloud.google.com/certification/cloud-engineer"},
        ],
        "roadmap_focus": ["Get AWS Cloud Practitioner certified", "Build a CI/CD pipeline project with Docker", "Apply for DevOps roles at Wipro, HCL and cloud-native startups"],
    },
    "backend": {
        "title": "Backend Software Engineer",
        "description": "Design scalable APIs and server-side systems for India's unicorn startups. Java and Go engineers are highly sought after at companies like Zerodha, Razorpay and PhonePe.",
        "salary_range": "₹6 LPA – ₹28 LPA",
        "demand": "Very High",
        "top_companies": ["Zerodha", "Razorpay", "PhonePe", "TCS", "Google"],
        "gaps": [
            {"skill": "System Design",        "importance": "Critical", "level_needed": "Advanced",     "current_level": 20},
            {"skill": "Microservices & APIs", "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "SQL + NoSQL Databases","importance": "High",     "level_needed": "Intermediate", "current_level": 35},
            {"skill": "Cloud Deployment",     "importance": "Medium",   "level_needed": "Beginner",     "current_level": 15},
        ],
        "courses": [
            {"title": "Java Programming Masterclass",           "platform": "Udemy",         "duration": "80 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/"},
            {"title": "System Design for Interviews",           "platform": "Udemy",         "duration": "19 hrs",   "difficulty": "Advanced",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/system-design-interview-prep/"},
            {"title": "Backend Development Program",            "platform": "Great Learning", "duration": "5 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "The Complete SQL Bootcamp",              "platform": "Udemy",         "duration": "9 hrs",    "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
        ],
        "certs": [
            {"title": "Oracle Certified Java Programmer (OCP)", "platform": "Oracle",          "difficulty": "Intermediate", "value": "Very High", "url": "https://education.oracle.com/java-se-programmer-ii/pexam_1Z0-829"},
            {"title": "AWS Certified Developer – Associate",    "platform": "Amazon AWS",      "difficulty": "Intermediate", "value": "Very High", "url": "https://aws.amazon.com/certification/certified-developer-associate/"},
            {"title": "MongoDB Associate Developer",            "platform": "MongoDB University","difficulty": "Intermediate","value": "High",      "url": "https://university.mongodb.com/certification"},
            {"title": "Microsoft Azure Fundamentals (AZ-900)",  "platform": "Microsoft",       "difficulty": "Beginner",     "value": "High",      "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
        ],
        "roadmap_focus": ["Master DSA and solve 100 LeetCode problems", "Build and deploy 2 REST API projects", "Practice system design and apply to product companies"],
    },
    "security": {
        "title": "Cybersecurity Analyst",
        "description": "Protect India's digital infrastructure from threats. Demand for security professionals is growing rapidly across BFSI, government and IT sectors.",
        "salary_range": "₹5 LPA – ₹22 LPA",
        "demand": "High",
        "top_companies": ["TCS", "Wipro", "HCL", "IBM", "Accenture"],
        "gaps": [
            {"skill": "Penetration Testing",   "importance": "Critical", "level_needed": "Intermediate", "current_level": 20},
            {"skill": "SIEM Tools",            "importance": "High",     "level_needed": "Beginner",     "current_level": 15},
            {"skill": "Network Security",      "importance": "High",     "level_needed": "Intermediate", "current_level": 25},
            {"skill": "Cloud Security",        "importance": "Medium",   "level_needed": "Beginner",     "current_level": 10},
        ],
        "courses": [
            {"title": "The Complete Cybersecurity Bootcamp",    "platform": "Udemy",         "duration": "28 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-internet-security-privacy-course-volume-1/"},
            {"title": "Ethical Hacking Bootcamp",               "platform": "Udemy",         "duration": "34 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/learn-ethical-hacking-from-scratch/"},
            {"title": "Cybersecurity Program",                  "platform": "Great Learning", "duration": "5 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "CompTIA Security+ Prep",                 "platform": "Udemy",         "duration": "21 hrs",   "difficulty": "Intermediate", "free": False, "certificate": True, "url": "https://www.udemy.com/course/securityplus/"},
        ],
        "certs": [
            {"title": "CompTIA Security+",                         "platform": "CompTIA",      "difficulty": "Intermediate", "value": "Very High", "url": "https://www.comptia.org/certifications/security"},
            {"title": "Certified Ethical Hacker (CEH)",            "platform": "EC-Council",   "difficulty": "Intermediate", "value": "Very High", "url": "https://www.eccouncil.org/programs/certified-ethical-hacker-ceh/"},
            {"title": "AWS Certified Security – Specialty",        "platform": "Amazon AWS",   "difficulty": "Advanced",     "value": "High",      "url": "https://aws.amazon.com/certification/certified-security-specialty/"},
            {"title": "Microsoft Azure Security Engineer (AZ-500)","platform": "Microsoft",    "difficulty": "Advanced",     "value": "High",      "url": "https://learn.microsoft.com/en-us/certifications/azure-security-engineer/"},
        ],
        "roadmap_focus": ["Get CompTIA Security+ certified", "Practice on TryHackMe and HackTheBox platforms", "Apply for SOC Analyst and InfoSec roles on Naukri"],
    },
    "default": {
        "title": "Software Engineer",
        "description": "Build software for India's booming IT sector. Demand is very high across TCS, Infosys and fast-growing startups across Bangalore, Hyderabad and Pune.",
        "salary_range": "₹6 LPA – ₹25 LPA",
        "demand": "Very High",
        "top_companies": ["TCS", "Infosys", "Wipro", "Google", "Microsoft"],
        "gaps": [
            {"skill": "Data Structures & Algorithms", "importance": "Critical", "level_needed": "Intermediate", "current_level": 25},
            {"skill": "SQL & Databases",              "importance": "High",     "level_needed": "Intermediate", "current_level": 30},
            {"skill": "Cloud AWS / Azure",            "importance": "High",     "level_needed": "Beginner",     "current_level": 10},
            {"skill": "Communication Skills",         "importance": "Medium",   "level_needed": "Intermediate", "current_level": 50},
        ],
        "courses": [
            {"title": "Python Bootcamp – Zero to Hero",    "platform": "Udemy",         "duration": "22 hrs",   "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
            {"title": "Data Science & ML Program",         "platform": "Great Learning", "duration": "6 months", "difficulty": "Intermediate", "free": True,  "certificate": True, "url": "https://www.mygreatlearning.com/academy"},
            {"title": "The Complete SQL Bootcamp",         "platform": "Udemy",         "duration": "9 hrs",    "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
            {"title": "AWS Cloud Practitioner Essentials", "platform": "Coursera",      "duration": "6 weeks",  "difficulty": "Beginner",     "free": False, "certificate": True, "url": "https://www.coursera.org/learn/aws-cloud-practitioner-essentials"},
        ],
        "certs": [
            {"title": "AWS Certified Cloud Practitioner",           "platform": "Amazon AWS",       "difficulty": "Beginner",     "value": "Very High", "url": "https://aws.amazon.com/certification/"},
            {"title": "Google Data Analytics Certificate",          "platform": "Coursera / Google","difficulty": "Beginner",     "value": "High",      "url": "https://grow.google/certificates/data-analytics/"},
            {"title": "Microsoft Azure Fundamentals (AZ-900)",      "platform": "Microsoft",        "difficulty": "Beginner",     "value": "Very High", "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
            {"title": "Meta Front-End Developer Certificate",       "platform": "Coursera / Meta",  "difficulty": "Intermediate", "value": "High",      "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
        ],
        "roadmap_focus": ["Solve 50 DSA problems and complete SQL bootcamp", "Build and deploy 2 projects on GitHub", "Apply on Naukri.com and attend campus drives"],
    }
}

SECOND_CAREERS = {
    "web":      ("Data Analyst",            72, "₹4 LPA – ₹18 LPA", "High",      ["Flipkart", "Paytm", "Accenture", "Razorpay", "Deloitte"]),
    "data":     ("Software Engineer",       70, "₹6 LPA – ₹25 LPA", "Very High", ["TCS", "Infosys", "Wipro", "Google", "Microsoft"]),
    "ml":       ("Data Scientist",          78, "₹8 LPA – ₹30 LPA", "Very High", ["Google", "Amazon", "Flipkart", "PhonePe", "CRED"]),
    "mobile":   ("Full Stack Developer",    68, "₹5 LPA – ₹22 LPA", "Very High", ["Meesho", "Flipkart", "Razorpay", "TCS", "Infosys"]),
    "cloud":    ("Backend Engineer",        70, "₹6 LPA – ₹28 LPA", "Very High", ["Zerodha", "Razorpay", "PhonePe", "TCS", "IBM"]),
    "backend":  ("DevOps Engineer",         68, "₹7 LPA – ₹28 LPA", "Very High", ["Wipro", "HCL", "Amazon", "Microsoft", "Infosys"]),
    "security": ("Cloud Security Engineer", 65, "₹7 LPA – ₹25 LPA", "High",      ["TCS", "IBM", "Accenture", "HCL", "Wipro"]),
    "default":  ("Data Analyst",            68, "₹4 LPA – ₹18 LPA", "High",      ["Flipkart", "Paytm", "Razorpay", "Accenture", "Deloitte"]),
}

THIRD_CAREERS = {
    "web":      ("Product Manager",   55, "₹12 LPA – ₹40 LPA", "High",   ["Swiggy", "Zomato", "CRED", "Meesho", "PhonePe"]),
    "data":     ("Business Analyst",  60, "₹5 LPA – ₹20 LPA",  "High",   ["Accenture", "Deloitte", "KPMG", "Cognizant", "Capgemini"]),
    "ml":       ("ML Research Eng.",  62, "₹12 LPA – ₹45 LPA", "High",   ["Google", "Microsoft", "Amazon", "Adobe", "Nvidia"]),
    "mobile":   ("Product Manager",   55, "₹12 LPA – ₹40 LPA", "High",   ["Swiggy", "Zomato", "CRED", "Meesho", "PhonePe"]),
    "cloud":    ("Cloud Architect",   60, "₹14 LPA – ₹45 LPA", "High",   ["AWS", "Microsoft", "Google", "Infosys", "Wipro"]),
    "backend":  ("Software Architect",58, "₹16 LPA – ₹50 LPA", "Medium", ["Google", "Microsoft", "Zerodha", "Razorpay", "Freshworks"]),
    "security": ("CISO / Security Mgr",52,"₹15 LPA – ₹50 LPA", "Medium", ["TCS", "Wipro", "IBM", "Accenture", "HDFC Bank"]),
    "default":  ("Product Manager",   55, "₹12 LPA – ₹40 LPA", "High",   ["Swiggy", "Zomato", "CRED", "Meesho", "PhonePe"]),
}

def _detect_domain(skills, interests):
    """Detect primary career domain from skills and interests."""
    all_text = " ".join(skills + interests).lower()
    scores = {domain: 0 for domain in SKILL_DOMAINS}
    for domain, keywords in SKILL_DOMAINS.items():
        for kw in keywords:
            if kw in all_text:
                scores[domain] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"

def _calc_scores(skills, level):
    """Calculate personalized scores based on skill count and experience level."""
    skill_count = len(skills)
    base = {"Beginner": 40, "Intermediate": 58, "Advanced": 72}.get(level, 55)
    bonus = min(skill_count * 3, 20)
    job_readiness  = min(base + bonus, 92)
    career_match   = min(base + bonus + 5, 95)
    learning_speed = {"Beginner": 45 + bonus, "Intermediate": 60 + bonus // 2, "Advanced": 72 + bonus // 3}.get(level, 60)
    learning_speed = min(learning_speed, 95)
    # Add small variation so different skill sets give slightly different numbers
    variation = (skill_count % 5) * 2
    return {
        "job_readiness":  job_readiness  + variation,
        "career_match":   career_match   + variation,
        "learning_speed": learning_speed + variation,
    }

def fallback_response(skills, interests, level):
    domain  = _detect_domain(skills, interests)
    profile = CAREER_PROFILES[domain]
    scores  = _calc_scores(skills, level)
    s2      = SECOND_CAREERS[domain]
    s3      = THIRD_CAREERS[domain]

    top_match  = min(scores["career_match"], 92)
    sec_match  = s2[1]
    third_match= s3[1]

    skill_str  = ", ".join(skills[:3]) if skills else "your current skills"
    top_title  = profile["title"]

    roadmap_tasks = {
        "Month 1-2": (f"Strengthen Core — {profile['roadmap_focus'][0]}",
                      [f"Complete the top-rated {profile['courses'][0]['title']} course",
                       f"Solve 30 DSA problems on LeetCode",
                       f"Set up GitHub and push your first project"],
                      "Core skills solid"),
        "Month 3-4": (f"Build Portfolio — {profile['roadmap_focus'][1]}",
                      [f"Build 2 real-world projects relevant to {top_title}",
                       f"Deploy projects online (Render / Vercel / AWS)",
                       f"Write 3 LinkedIn posts showcasing your work"],
                      "Portfolio live"),
        "Month 5-6": (f"Job Readiness — {profile['roadmap_focus'][2]}",
                      [f"Apply to 20+ jobs on Naukri.com and LinkedIn",
                       f"Attend campus or off-campus recruitment drives",
                       f"Practice mock interviews for {top_title} roles"],
                      "First offer"),
    }

    return {
        "career_paths": [
            {
                "title": top_title,
                "match_percentage": top_match,
                "description": profile["description"],
                "salary_range": profile["salary_range"],
                "demand": profile["demand"],
                "top_companies": profile["top_companies"],
            },
            {
                "title": s2[0],
                "match_percentage": sec_match,
                "description": f"Strong alternative path leveraging your {skill_str} background. Growing demand across India's IT sector.",
                "salary_range": s2[2],
                "demand": s2[3],
                "top_companies": s2[4],
            },
            {
                "title": s3[0],
                "match_percentage": third_match,
                "description": "A higher-responsibility role that becomes accessible with 2-3 years of experience in your primary path.",
                "salary_range": s3[2],
                "demand": s3[3],
                "top_companies": s3[4],
            },
        ],
        "skill_gaps": profile["gaps"],
        "courses":    profile["courses"],
        "certifications": profile["certs"],
        "roadmap": [
            {"month": month, "focus": val[0], "tasks": val[1], "milestone": val[2]}
            for month, val in roadmap_tasks.items()
        ],
        "scores": scores,
        "summary": (
            f"Based on your {level} experience with {skill_str}, your strongest career match is "
            f"{top_title} with a {top_match}% alignment score. "
            f"India's demand for {top_title}s is {profile['demand'].lower()} with salaries ranging {profile['salary_range']}. "
            f"Focus on the skill gaps and roadmap below to maximise your CTC and land your first offer."
        ),
    }


# ── Smart Resume Fallback ─────────────────────────────────────────────────────

RESUME_SKILL_KEYWORDS = {
    "python": "Python", "sql": "SQL", "java": "Java", "javascript": "JavaScript",
    "react": "React.js", "node": "Node.js", "html": "HTML", "css": "CSS",
    "c++": "C++", "c#": "C#", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "tensorflow": "TensorFlow", "keras": "Keras",
    "pandas": "Pandas", "numpy": "NumPy", "tableau": "Tableau", "power bi": "Power BI",
    "aws": "AWS", "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes",
    "git": "Git & GitHub", "linux": "Linux", "mongodb": "MongoDB", "mysql": "MySQL",
    "postgresql": "PostgreSQL", "flask": "Flask", "django": "Django",
    "excel": "Microsoft Excel", "communication": "Communication", "agile": "Agile",
    "flutter": "Flutter", "android": "Android", "ios": "iOS", "swift": "Swift",
    "kotlin": "Kotlin", "spring": "Spring Boot", "golang": "Go / Golang",
    "cybersecurity": "Cybersecurity", "networking": "Networking",
}

def fallback_resume_response(resume_text=""):
    """Smart resume fallback that detects skills from actual resume text."""
    text_lower = resume_text.lower() if resume_text else ""

    # Detect skills from resume text
    found_skills = []
    for keyword, label in RESUME_SKILL_KEYWORDS.items():
        if keyword in text_lower and label not in found_skills:
            found_skills.append(label)

    if not found_skills:
        found_skills = ["Python", "SQL", "Microsoft Excel", "Communication", "Problem Solving"]

    # Detect experience level from text
    if any(w in text_lower for w in ["senior", "lead", "architect", "principal", "manager", "6 years", "7 years", "8 years"]):
        exp_level, resume_score, missing_focus = "Senior", 74, ["Leadership", "Cloud Architecture", "System Design", "Mentoring"]
    elif any(w in text_lower for w in ["3 years", "4 years", "5 years", "mid", "associate"]):
        exp_level, resume_score, missing_focus = "Mid", 63, ["Machine Learning", "Cloud (AWS/Azure)", "System Design", "Docker"]
    elif any(w in text_lower for w in ["1 year", "2 years", "junior", "associate"]):
        exp_level, resume_score, missing_focus = "Junior", 55, ["DSA & LeetCode", "Cloud (AWS/Azure)", "Git & GitHub", "REST APIs"]
    else:
        exp_level, resume_score, missing_focus = "Fresher", 48, ["DSA & LeetCode", "Cloud Basics (AWS)", "Git & GitHub", "SQL Queries"]

    # Adjust score based on how many skills found
    resume_score = min(resume_score + len(found_skills) * 2, 88)

    # Detect recommended roles from skills
    domain = _detect_domain(found_skills, [])
    role_map = {
        "web":      ["Full Stack Developer", "Frontend Developer", "UI Engineer"],
        "data":     ["Data Analyst", "Business Analyst", "BI Developer"],
        "ml":       ["ML Engineer", "Data Scientist", "AI Research Engineer"],
        "mobile":   ["Mobile App Developer", "Android Developer", "Flutter Developer"],
        "cloud":    ["DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer"],
        "backend":  ["Backend Engineer", "Software Engineer", "API Developer"],
        "security": ["Cybersecurity Analyst", "SOC Analyst", "InfoSec Engineer"],
        "default":  ["Software Engineer", "Data Analyst", "Business Analyst"],
    }
    recommended_roles = role_map.get(domain, role_map["default"])

    return {
        "extracted_skills": found_skills[:10],
        "recommended_roles": recommended_roles,
        "missing_skills": missing_focus,
        "resume_score": resume_score,
        "experience_level": exp_level,
        "top_career_match": recommended_roles[0],
        "improvement_tips": [
            "Add quantified achievements (e.g., 'Reduced load time by 40%' or 'Increased sales by ₹2L')",
            "Include a prominent GitHub / Portfolio link so recruiters can see your work",
            "Use strong action verbs: Built, Designed, Optimised, Led, Automated, Deployed",
            "Add a concise 3-line professional summary at the very top of your resume",
            "List certifications with the issuing body and year to boost ATS score",
        ],
        "ats_keywords": ["Python", "SQL", "REST API", "Agile", "Git", "Cloud", "Data Analysis", "CI/CD"],
        "strengths": [
            f"Strong technical skill set with {len(found_skills)} relevant skills detected",
            "Good educational background relevant to India's IT industry",
        ],
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

# ── Smart Chat Fallback ───────────────────────────────────────────────────────

def _smart_chat_reply(question, context):
    """Return a context-aware reply based on question keywords."""
    q = question.lower()
    top_career  = (context.get("career_paths") or [{}])[0].get("title", "Software Engineer")
    salary      = (context.get("career_paths") or [{}])[0].get("salary_range", "₹6 LPA – ₹25 LPA")
    readiness   = (context.get("scores") or {}).get("job_readiness", 65)
    top_company = ((context.get("career_paths") or [{}])[0].get("top_companies") or ["TCS"])[0]

    if any(w in q for w in ["salary", "pay", "ctc", "lpa", "package", "earn"]):
        return (f"For a {top_career} role in India, you can expect a starting salary of {salary}. "
                f"Companies like {top_company} and other top firms offer competitive packages. "
                f"With 2-3 years of experience and strong DSA skills, you can push into the higher range. "
                f"Bangalore and Hyderabad typically offer 15-20% higher salaries than other cities.")

    if any(w in q for w in ["naukri", "linkedin", "apply", "job search", "where to find", "find job", "job portal"]):
        return (f"The best platforms for {top_career} jobs in India are Naukri.com, LinkedIn, and Instahyre. "
                f"For freshers, also check your college placement portal and off-campus drives by TCS, Infosys and Wipro. "
                f"Apply to at least 20-30 companies to improve your chances. "
                f"Keep your LinkedIn profile updated with your GitHub projects and certifications.")

    if any(w in q for w in ["interview", "prepare", "crack", "tips", "how to", "dsa", "leetcode", "coding"]):
        return (f"To crack {top_career} interviews in India, focus on DSA fundamentals — solve at least 100 LeetCode problems (Easy + Medium). "
                f"Practice system design basics and brush up on your core subjects like OS, DBMS and CN. "
                f"Mock interviews on platforms like Pramp or InterviewBit are very helpful. "
                f"Most Indian product companies like Razorpay and Zerodha have 3-4 rounds including a coding test, technical interview and HR round.")

    if any(w in q for w in ["course", "learn", "study", "skill", "improve", "upskill", "certification", "certif"]):
        return (f"For your {top_career} path, I recommend starting with Udemy's top-rated courses and Great Learning's free programs. "
                f"Get the AWS Cloud Practitioner certification first — it's beginner-friendly and highly valued by Indian recruiters. "
                f"Set aside 1-2 hours daily for learning and aim to complete one certification every 2 months. "
                f"Great Learning Academy offers free certificates that you can directly add to your LinkedIn profile.")

    if any(w in q for w in ["resume", "cv", "ats", "profile", "portfolio"]):
        return (f"For a strong {top_career} resume in India, keep it to 1 page for freshers and lead with a 3-line summary. "
                f"Add quantified achievements like 'Built a web app with 500+ users' or 'Reduced API response time by 30%'. "
                f"Include your GitHub link and make sure your top 2-3 projects are clearly described with tech stack used. "
                f"Use ATS-friendly keywords like REST API, Python, SQL, Agile, and Git to pass automated screening.")

    if any(w in q for w in ["company", "companies", "tcs", "infosys", "wipro", "google", "amazon", "startup", "mnc"]):
        return (f"For {top_career} roles, {top_company} is a great target along with other top Indian and MNC companies. "
                f"Service companies like TCS, Infosys and Wipro are great for freshers with structured training programs. "
                f"Product startups like Razorpay, Zerodha and CRED pay 30-50% more but expect stronger technical skills. "
                f"Start with service companies if you're a fresher, then switch to product companies after 1-2 years.")

    if any(w in q for w in ["readiness", "score", "percentage", "how ready", "prepared"]):
        return (f"Your current job readiness score is {readiness}/100 for a {top_career} role. "
                f"This means you have a solid foundation but there are specific skill gaps to close. "
                f"Focus on the top skill gaps in your analysis — closing even 2 of them can push your score above 80. "
                f"Aim to have 2 deployed projects and at least 1 certification before applying.")

    if any(w in q for w in ["roadmap", "plan", "path", "timeline", "months", "next step", "what should"]):
        return (f"Your 6-month plan for becoming a {top_career}: Months 1-2 focus on core skills and DSA. "
                f"Months 3-4 build 2 real projects and push them to GitHub with a live demo. "
                f"Months 5-6 start applying on Naukri and LinkedIn — target at least 5 applications per week. "
                f"Consistency matters more than speed — 2 hours of focused learning daily will take you far.")

    if any(w in q for w in ["hi", "hello", "hey", "start", "help", "what can"]):
        return (f"Hi! I'm CareerBot, your AI career advisor for the Indian job market. "
                f"Based on your analysis, you're on track for a {top_career} role with a salary of {salary}. "
                f"You can ask me about salaries, interview prep, best courses, job portals, resume tips, or your 6-month roadmap. "
                f"What would you like to know?")

    # Default smart reply using context
    return (f"Great question! For your {top_career} career path in India, focus on building strong fundamentals and practical projects. "
            f"The salary range you can target is {salary}, and your job readiness is currently at {readiness}/100. "
            f"I recommend checking your skill gaps section and working on the top 2 gaps first. "
            f"Feel free to ask me about salaries, interview tips, courses, resume advice, or job search strategies!")


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
        return jsonify(fallback_resume_response(""))

    log.info("Extracted %d characters from resume", len(resume_text))

    # 🔥 FORCE FALLBACK (for demo) — smart: analyses actual resume text
    return jsonify(fallback_resume_response(resume_text))

    if not GEMINI_API_KEY:
        return jsonify(fallback_resume_response(resume_text))

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
        return jsonify(fallback_resume_response(resume_text))

    except Exception as exc:
        log.error("Resume analyze error: %s", exc, exc_info=True)
        return jsonify(fallback_resume_response(resume_text))

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
        return jsonify({"reply": _smart_chat_reply(question, context)})

    # 🔥 FORCE FALLBACK (for demo) — smart keyword-based reply
    return jsonify({"reply": _smart_chat_reply(question, context)})

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
