from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from auth import auth_bp, init_db
from gpt_analyzer import gpt_bp

app = Flask(__name__)
CORS(app)

# JWT Config
app.config['JWT_SECRET_KEY'] = 'your-secret-key'
jwt = JWTManager(app)

# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(gpt_bp)

# Init DB
init_db()

if __name__ == '__main__':
    app.run(debug=True)
