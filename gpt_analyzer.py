import os
import tempfile
import requests
import docx2txt
import PyPDF2
import re
import json
from flask import Blueprint, request, jsonify

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
    print("DEBUG: HEADERS =>", dict(request.headers), flush=True)
    print("DEBUG: FILE KEYS =>", list(request.files.keys()), flush=True)
    print("DEBUG: FORM KEYS =>", list(request.form.keys()), flush=True)

    resume = request.files.get('resume')
    job_description = request.form.get('job_description', '')

    if not resume or not job_description:
        return jsonify({"message": "Resume or Job description is missing"}), 422

    resume_text, err = extract_text_from_file(resume)
    if err:
        return jsonify({"error": err}), 400

    # Ask GPT to give valid JSON output
    prompt = f"""
    You are an AI Resume Analyzer. Compare the resume with the job description and return a JSON object with the following fields only:

    {{
      "score": <integer from 0 to 100>,
      "skills": [list of key skills present in resume],
      "missing_skills": [list of important skills missing from resume],
      "suggestions": [list of suggestions to improve the resume],
      "summary": "<2-3 line summary of the candidate>"
    }}

    Resume:
    {resume_text}

    Job Description:
    {job_description}

    Please respond only with the JSON output.
    """

    try:
        gpt_result = call_groq(prompt)

        # Debug log full GPT response
        print("\n===== FULL GPT OUTPUT =====\n", flush=True)
        print(gpt_result, flush=True)
        print("\n===== END =====\n", flush=True)

        # Clean up triple quotes or code block marks if they exist
        gpt_result_clean = re.sub(r"^```json|```$", "", gpt_result.strip(), flags=re.MULTILINE).strip()

        parsed = json.loads(gpt_result_clean)

        score = parsed.get("score", 0)
        skills = parsed.get("skills", [])
        missing_skills = parsed.get("missing_skills", [])
        suggestions = parsed.get("suggestions", [])
        summary = parsed.get("summary", "")

        print("DEBUG: Parsed Score:", score, flush=True)
        print("DEBUG: Skills:", skills, flush=True)
        print("DEBUG: Missing Skills:", missing_skills, flush=True)
        print("DEBUG: Suggestions:", suggestions, flush=True)
        print("DEBUG: Summary:", summary, flush=True)

        return jsonify({
            "score": score,
            "skills": skills,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
            "summary": summary
        })

    except Exception as e:
        print("ERROR in analyze():", str(e), flush=True)
        return jsonify({"error": str(e)}), 500
