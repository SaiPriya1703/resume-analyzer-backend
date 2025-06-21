import os
import tempfile
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
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

# Resume Analysis Route
@gpt_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze():
    # ✅ Add debugging logs to trace input
    print("🧾 Received request to /analyze")
    print("📁 request.files keys:", list(request.files.keys()))
    print("📝 request.form keys:", list(request.form.keys()))

    if 'resume' not in request.files:
        print("❌ Resume missing in request.files")
        return jsonify({"message": "Resume file is required"}), 422

    if 'job_description' not in request.form:
        print("❌ Job description missing in request.form")
        return jsonify({"message": "Job description is required"}), 422

    resume = request.files['resume']
    job_description = request.form.get("job_description", "").strip()

    print("✅ Resume file name:", resume.filename)
    print("✅ Job description:", job_description)

    # Extract text
    resume_text, err = extract_text_from_file(resume)
    if err:
        print("❌ Failed to extract resume text:", err)
        return jsonify({"error": err}), 400

    # Prompt for Groq
    prompt = f"""
    Resume:
    {resume_text}

    Job Description:
    {job_description}

    1. Resume Match Score (0–100%)
    2. Key Skills Present
    3. Missing Skills
    4. Suggestions to Improve Resume
    5. Custom Summary (2-3 lines)
    """

    # Call Groq API
    try:
        result = call_groq(prompt)
        return jsonify({"result": result})
    except Exception as e:
        print("❌ Groq API error:", str(e))
        return jsonify({"error": str(e)}), 500
