# Debug redeploy trigger
import os
import tempfile
import requests
from flask import Blueprint, request, jsonify
import docx2txt
import PyPDF2

gpt_bp = Blueprint('gpt_bp', __name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Extract text from uploaded resume
def extract_text_from_file(file):
    ext = file.filename.split('.')[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp:
        file.save(tmp.name)

        if ext == 'pdf':
            with open(tmp.name, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        elif ext == 'docx':
            text = docx2txt.process(tmp.name)
        else:
            return None, f"Unsupported file format: {ext}"

        return text, None

# Call Groq API using Mixtral model
def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["choices"][0]["message"]["content"]

# 🔍 DEBUG-ONLY Analyze Route (no GPT call, just data inspection)
@gpt_bp.route('/analyze', methods=['POST'])
def analyze():
    print("🚨 DEBUG: HEADERS =>", dict(request.headers), flush=True)
    print("📂 DEBUG: FILE KEYS =>", list(request.files.keys()), flush=True)
    print("📋 DEBUG: FORM KEYS =>", list(request.form.keys()), flush=True)

    resume = request.files.get('resume', None)
    job_description = request.form.get('job_description', '')

    print("✅ Extracted resume:", resume.filename if resume else None, flush=True)
    print("✅ Extracted job_description:", job_description[:100], flush=True)  # Only show first 100 characters

    if not resume:
        return jsonify({"message": "Resume file is missing"}), 422
    if not job_description:
        return jsonify({"message": "Job description is missing"}), 422

    return jsonify({"message": "Data received properly!"}), 200
