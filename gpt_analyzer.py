import openai
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import os
import tempfile

import docx2txt
import PyPDF2  # or pdfplumber if you prefer

gpt_bp = Blueprint('gpt_bp', __name__)
openai.api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key")  # use .env or Render secret

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

@gpt_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze():
    if 'file' not in request.files or 'job_description' not in request.form:
        return jsonify({"error": "Missing file or job_description"}), 400

    file = request.files['file']
    jd = request.form['job_description']

    resume_text, err = extract_text_from_file(file)
    if err:
        return jsonify({"error": err}), 400

    prompt = f"""
    Resume:
    {resume_text}

    Job Description:
    {jd}

    1. Resume Match Score (%)
    2. Missing Skills
    3. Suggestions to Improve Resume
    4. Custom Summary (2-3 lines)
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message['content']
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
