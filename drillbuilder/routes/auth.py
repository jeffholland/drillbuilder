from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..extensions import db
from ..models import User

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    data = request.get_json() or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"msg": "username, email and password are required"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"msg": "user with username or email already exists"}), 400

    pw_hash = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=pw_hash)
    db.session.add(user)
    db.session.commit()

    return jsonify({"id": user.id, "username": user.username, "email": user.email}), 201


@bp.post("/login")
def login():
    data = request.get_json() or {}
    username_or_email = data.get("username") or data.get("email")
    password = data.get("password")

    if not username_or_email or not password:
        return jsonify({"msg": "username/email and password required"}), 400

    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "invalid credentials"}), 401

    # jwt identity must be a serializable string used for the subject claim
    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token, "user": {"id": user.id, "username": user.username}})


@bp.post("/logout")
@jwt_required()
def logout():
    # token revocation / blacklists would be implemented here; for now, client should discard token
    return jsonify({"msg": "logged out"}), 200
