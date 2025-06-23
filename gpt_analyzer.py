import os
import tempfile
import requests
import docx2txt
import PyPDF2
import json
import re
from flask import Blueprint, request, jsonify

# Blueprint setup
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

@gpt_bp.route('/analyze', methods=['POST'])
def analyze():
    print("\U0001F6A8 DEBUG: HEADERS =>", dict(request.headers), flush=True)
    print("\ud83d\udcc2 DEBUG: FILE KEYS =>", list(request.files.keys()), flush=True)
    print("\ud83d\udccb DEBUG: FORM KEYS =>", list(request.form.keys()), flush=True)

    resume = request.files.get('resume')
    job_description = request.form.get('job_description', '')

    if not resume or not job_description:
        return jsonify({"message": "Resume or Job description is missing"}), 422

    resume_text, err = extract_text_from_file(resume)
    if err:
        return jsonify({"error": err}), 400

    prompt = f"""
    Resume:
    {resume_text}

    Job Description:
    {job_description}

    Provide response only as raw JSON without markdown formatting:
    {{
      "score": number (0-100),
      "skills": ["skill1", "skill2", ...],
      "missing_skills": ["skill1", "skill2", ...],
      "suggestions": ["tip1", "tip2", ...],
      "summary": "2-3 sentence summary"
    }}
    """

    try:
        gpt_response = call_groq(prompt)

        print("\n===== FULL GPT OUTPUT =====\n")
        print(gpt_response)
        print("\n===== END =====\n")

        # Remove ```json and ``` wrappers if present
        cleaned_json = re.sub(r"^```json|```$", "", gpt_response.strip(), flags=re.MULTILINE).strip()

        result = json.loads(cleaned_json)

        return jsonify({
            "score": result.get("score", 0),
            "skills": result.get("skills", []),
            "missing_skills": result.get("missing_skills", []),
            "suggestions": result.get("suggestions", []),
            "summary": result.get("summary", "")
        })

    except Exception as e:
        print("\u274c Error parsing GPT JSON:", e, flush=True)
        return jsonify({"error": str(e)}), 500
