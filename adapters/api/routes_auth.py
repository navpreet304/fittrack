from datetime import date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token

from adapters.db.pg_repositories import PGUserRepository
from domain.entities.user import User

auth_bp = Blueprint("auth", __name__)


def _get_user_repo():
    from adapters.api import get_db
    return PGUserRepository(get_db())


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["email", "password", "first_name", "last_name", "date_of_birth"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    repo = _get_user_repo()
    if repo.get_by_email(data["email"]):
        return jsonify({"error": "Email already registered"}), 409

    try:
        dob = date.fromisoformat(data["date_of_birth"])
    except ValueError:
        return jsonify({"error": "date_of_birth must be YYYY-MM-DD"}), 400

    user = User(
        email=data["email"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=dob,
        role=data.get("role", "user"),
        height_cm=data.get("height_cm"),
        fitness_level=data.get("fitness_level"),
    )
    user.set_password(data["password"])
    saved = repo.save(user)

    return jsonify({"id": saved.id, "email": saved.email}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "email and password required"}), 400

    repo = _get_user_repo()
    user = repo.get_by_email(data["email"])

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )
    return jsonify({"access_token": token, "user_id": user.id, "role": user.role}), 200
