import os
import tempfile
import requests
import docx2txt
import PyPDF2
import re
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

    try:
        gpt_result = call_groq(prompt)
        print("📨 GPT Output:", gpt_result[:300], flush=True)

        # --- Flexible parsing ---
        score_match = re.search(r"Match Score[:\-]?\s*(\d+)%", gpt_result, re.IGNORECASE)
        summary_match = re.search(r"Custom Summary[:\-]?\s*\n(.+)", gpt_result, re.IGNORECASE | re.DOTALL)

        # Extract bullet lists
        def extract_bullets(section_title):
            pattern = rf"{section_title}[:\-]?\s*\n((?:[-*•] .*?\n)+)"
            match = re.search(pattern, gpt_result, re.IGNORECASE)
            if not match:
                return []
            
            lines = match.group(1).strip().splitlines()
            extracted = []
            for line in lines:
                line = re.sub(r"^[-*•]\s*", "", line).strip()  # remove bullet
                if ":" in line:
                    key, values = line.split(":", 1)
                    for item in values.split(","):
                        cleaned = item.strip()
                        if cleaned:
                            extracted.append(cleaned)
                else:
                    extracted.append(line)
        return extracted


        skills = extract_bullets("Key Skills Present")
        missing_skills = extract_bullets("Missing Skills")
        suggestions = extract_bullets("Suggestions to Improve Resume")
        score = int(score_match.group(1)) if score_match else 0
        summary = summary_match.group(1).strip() if summary_match else ""

        # --- Logs ---
        print("✅ Parsed Score:", score, flush=True)
        print("✅ Extracted Skills:", skills, flush=True)
        print("✅ Missing Skills:", missing_skills, flush=True)
        print("✅ Suggestions:", suggestions, flush=True)
        print("✅ Summary:", summary[:100], flush=True)

        return jsonify({
            "score": score,
            "skills": skills,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
            "summary": summary
        })

    except Exception as e:
        print("❌ Error in GPT parsing:", e, flush=True)
        return jsonify({"error": str(e)}), 500
