from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os

from database import users_collection  # Make sure this is correct

auth_bp = Blueprint("auth", __name__)

# Secret key for encoding JWT (make sure this is securely stored in prod)
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")


# ✅ REGISTER ROUTE
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')  # ✅ Corrected
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        return jsonify({"message": "User already exists"}), 409

    hashed_pw = generate_password_hash(password)

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_pw
    })

    return jsonify({"message": "User registered successfully"}), 201


# ✅ LOGIN ROUTE
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = users_collection.find_one({"email": email})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode({
        "user_id": str(user['_id']),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({"token": token, "name": user["name"]}), 200


# ✅ RESET PASSWORD ROUTE
@auth_bp.route('/reset-password', methods=['POST', 'OPTIONS'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')

    if not email or not new_password:
        return jsonify({"error": "Email and new password required"}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    hashed = generate_password_hash(new_password)
    users_collection.update_one({"email": email}, {"$set": {"password": hashed}})
    return jsonify({"message": "Password reset successful"}), 200
