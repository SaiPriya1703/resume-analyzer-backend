from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from auth import auth_bp
from gpt_analyzer import gpt_bp
import os
import sys
app = Flask(__name__)
CORS(app)

# JWT Config
app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY", "your-secret-key")
jwt = JWTManager(app)

# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(gpt_bp)

@app.route('/')
def home():
    return {'message': 'Resume Analyzer Backend is Live 🎯'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=True)
    sys.stdout.flush()
