import openai
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

gpt_bp = Blueprint('gpt_bp', __name__)
openai.api_key = "your-openai-api-key"

@gpt_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze():
    data = request.json
    resume = data['resume']
    jd = data['job_description']

    prompt = f"""
    Resume:
    {resume}

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
