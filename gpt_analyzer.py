import os
import tempfile
import requests
import docx2txt
import PyPDF2
from flask import Blueprint, request, jsonify

gpt_bp = Blueprint('gpt_bp', __name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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

def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(response.text)
    return response.json()["choices"][0]["message"]["content"]

@gpt_bp.route('/analyze', methods=['POST'])
def analyze():
    import json

    print("🚨 DEBUG: HEADERS =>", dict(request.headers), flush=True)
    print("📂 DEBUG: FILE KEYS =>", list(request.files.keys()), flush=True)
    print("📋 DEBUG: FORM KEYS =>", list(request.form.keys()), flush=True)

    resume = request.files.get('resume')
    job_description = request.form.get('job_description', '')

    if not resume or not job_description:
        return jsonify({"message": "Resume or Job description is missing"}), 422

    resume_text, err = extract_text_from_file(resume)
    if err:
        return jsonify({"error": err}), 400

    # ✅ Structured prompt requesting JSON
    prompt = f"""
You are a resume screening assistant.

Analyze the following resume and job description, then return ONLY the following JSON structure:

{{
  "score": 0-100, 
  "skills": ["Skill 1", "Skill 2", ...],
  "missing_skills": ["Skill A", "Skill B", ...],
  "suggestions": ["Tip 1", "Tip 2", ...],
  "summary": "2-3 line summary"
}}

Resume:
\"\"\"
{resume_text}
\"\"\"

Job Description:
\"\"\"
{job_description}
\"\"\"
"""

    try:
        gpt_response = call_groq(prompt)

        print("\n===== FULL GPT OUTPUT =====\n")
        print(gpt_response)
        print("\n===== END =====\n")

        # ✅ Parse GPT JSON safely
        result = json.loads(gpt_response)

        return jsonify({
            "score": result.get("score", 0),
            "skills": result.get("skills", []),
            "missing_skills": result.get("missing_skills", []),
            "suggestions": result.get("suggestions", []),
            "summary": result.get("summary", "")
        })

    except Exception as e:
        print("❌ Error parsing GPT JSON:", e, flush=True)
        return jsonify({"error": str(e)}), 500
