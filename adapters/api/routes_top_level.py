"""
Top-level resource endpoints (/goals, /measurements, /notifications) that mirror
the master-prompt API surface. These wrap the existing user-scoped repositories
so the resource is always derived from the JWT identity.
"""
from datetime import date, datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from adapters.db.pg_repositories import (
    PGFitnessGoalRepository,
    PGBodyMeasurementRepository,
    PGNotificationRepository,
    PGWorkoutSessionRepository,
    PGMealEntryRepository,
)
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.body_measurement import BodyMeasurement
from domain.entities.badge_notification import Notification

# Reuse the existing workouts/meals blueprints so GET handlers live next to POST.
from adapters.api.routes_workouts import workouts_bp
from adapters.api.routes_meals import meals_bp


goals_bp = Blueprint("goals_top", __name__)
measurements_bp = Blueprint("measurements_top", __name__)
notifications_bp = Blueprint("notifications_top", __name__)


def _session():
    from adapters.api import get_db
    return get_db()


# ---------- /goals ----------

@goals_bp.post("")
@jwt_required()
def create_goal():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    required = ["description", "target_value", "unit", "deadline"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        goal = FitnessGoal(
            user_id=user_id,
            description=data["description"],
            target_value=float(data["target_value"]),
            unit=data["unit"],
            deadline=date.fromisoformat(data["deadline"]),
            current_value=float(data.get("current_value", 0.0)),
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    repo = PGFitnessGoalRepository(_session())
    saved = repo.save(goal)
    return jsonify({
        "id": saved.id,
        "description": saved.description,
        "target_value": saved.target_value,
        "current_value": saved.current_value,
        "unit": saved.unit,
        "deadline": saved.deadline.isoformat(),
        "status": saved.status,
    }), 201


@goals_bp.get("")
@jwt_required()
def list_goals():
    user_id = int(get_jwt_identity())
    repo = PGFitnessGoalRepository(_session())
    goals = repo.get_by_user(user_id)
    return jsonify([
        {
            "id": g.id,
            "description": g.description,
            "target_value": g.target_value,
            "current_value": g.current_value,
            "unit": g.unit,
            "deadline": g.deadline.isoformat(),
            "status": g.status,
        }
        for g in goals
    ]), 200


@goals_bp.patch("/<int:goal_id>/complete")
@jwt_required()
def complete_goal(goal_id: int):
    user_id = int(get_jwt_identity())
    repo = PGFitnessGoalRepository(_session())
    goals = repo.get_by_user(user_id)
    goal = next((g for g in goals if g.id == goal_id), None)
    if goal is None:
        return jsonify({"error": "Goal not found"}), 404

    goal.complete()
    repo.update(goal)
    return jsonify({
        "id": goal.id,
        "status": goal.status,
        "current_value": goal.current_value,
    }), 200


# ---------- /measurements ----------

@measurements_bp.get("")
@jwt_required()
def list_measurements():
    user_id = int(get_jwt_identity())
    repo = PGBodyMeasurementRepository(_session())
    rows = repo.get_by_user(user_id, date(2000, 1, 1), date.today())
    rows.sort(key=lambda r: r.recorded_date, reverse=True)
    return jsonify([
        {
            "id": r.id,
            "measurement_type": r.measurement_type,
            "value": r.value,
            "unit": r.unit,
            "recorded_date": r.recorded_date.isoformat(),
        }
        for r in rows
    ]), 200


@measurements_bp.post("")
@jwt_required()
def create_measurement():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    required = ["measurement_type", "value", "unit", "recorded_date"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        m = BodyMeasurement(
            user_id=user_id,
            measurement_type=data["measurement_type"],
            value=float(data["value"]),
            unit=data["unit"],
            recorded_date=date.fromisoformat(data["recorded_date"]),
            notes=data.get("notes", ""),
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    repo = PGBodyMeasurementRepository(_session())
    saved = repo.save(m)
    return jsonify({
        "id": saved.id,
        "measurement_type": saved.measurement_type,
        "value": saved.value,
        "unit": saved.unit,
        "recorded_date": saved.recorded_date.isoformat(),
        "notes": saved.notes,
    }), 201


@measurements_bp.get("/latest")
@jwt_required()
def latest_measurement():
    user_id = int(get_jwt_identity())
    repo = PGBodyMeasurementRepository(_session())
    rows = repo.get_by_user(user_id, date(2000, 1, 1), date.today())
    if not rows:
        return jsonify({}), 200

    latest = max(rows, key=lambda r: r.recorded_date)
    return jsonify({
        "id": latest.id,
        "measurement_type": latest.measurement_type,
        "value": latest.value,
        "unit": latest.unit,
        "recorded_date": latest.recorded_date.isoformat(),
        "notes": latest.notes,
    }), 200


# ---------- /notifications ----------

@notifications_bp.post("")
@jwt_required()
def create_notification():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    if "message" not in data:
        return jsonify({"error": "message is required"}), 400

    scheduled_at = None
    if data.get("scheduled_at"):
        try:
            scheduled_at = datetime.fromisoformat(data["scheduled_at"])
        except ValueError:
            return jsonify({"error": "scheduled_at must be ISO-8601"}), 400

    notif = Notification(
        user_id=user_id,
        message=data["message"],
        channel=data.get("channel", "email"),
        scheduled_at=scheduled_at,
    )
    repo = PGNotificationRepository(_session())
    saved = repo.save(notif)

    return jsonify({
        "id": saved.id,
        "message": saved.message,
        "channel": saved.channel,
        "status": saved.status,
        "scheduled_at": saved.scheduled_at.isoformat() if saved.scheduled_at else None,
    }), 201


@notifications_bp.get("")
@jwt_required()
def list_notifications():
    user_id = int(get_jwt_identity())
    from adapters.api import get_db
    db = get_db()
    from adapters.db.models import NotificationModel
    rows = db.query(NotificationModel).filter_by(user_id=user_id).all()
    return jsonify([
        {
            "id": r.id,
            "message": r.message,
            "channel": r.channel,
            "status": r.status,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
        }
        for r in rows
    ]), 200


@notifications_bp.get("/due")
@jwt_required()
def due_notifications():
    """Return pending notifications whose scheduled_at has arrived for the logged-in user."""
    user_id = int(get_jwt_identity())
    from adapters.api import get_db
    db = get_db()
    from adapters.db.models import NotificationModel
    now = datetime.utcnow()
    rows = db.query(NotificationModel).filter(
        NotificationModel.user_id == user_id,
        NotificationModel.status == "pending",
        NotificationModel.scheduled_at != None,  # noqa: E711
        NotificationModel.scheduled_at <= now,
    ).all()
    return jsonify([
        {
            "id": r.id,
            "message": r.message,
            "channel": r.channel,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        }
        for r in rows
    ]), 200


@notifications_bp.patch("/<int:notif_id>/deliver")
@jwt_required()
def deliver_notification(notif_id: int):
    """Mark a notification as delivered (shown on-screen to the logged-in user)."""
    user_id = int(get_jwt_identity())
    from adapters.api import get_db
    db = get_db()
    from adapters.db.models import NotificationModel
    row = db.get(NotificationModel, notif_id)
    if not row or row.user_id != user_id:
        return jsonify({"error": "Notification not found"}), 404
    row.status = "delivered"
    row.sent_at = datetime.utcnow()
    db.commit()
    return jsonify({"id": row.id, "status": row.status}), 200


# ---------- /workouts (GET list) and /meals (GET list) ----------

@workouts_bp.get("")
@jwt_required()
def list_workouts():
    user_id = int(get_jwt_identity())
    start_str = request.args.get("start", "2000-01-01")
    end_str = request.args.get("end", date.today().isoformat())
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400

    repo = PGWorkoutSessionRepository(_session())
    sessions = repo.get_by_user(user_id, start, end)
    return jsonify([
        {
            "id": s.id,
            "session_date": s.session_date.isoformat(),
            "exercises": [
                {
                    "name": e.name,
                    "duration_minutes": e.duration_minutes,
                    "sets": e.sets,
                    "reps": e.reps,
                    "notes": e.notes,
                }
                for e in s.exercises
            ],
            "total_duration_minutes": s.total_duration(),
        }
        for s in sessions
    ]), 200


@meals_bp.get("")
@jwt_required()
def list_meals():
    user_id = int(get_jwt_identity())
    target_date_str = request.args.get("date")
    if target_date_str:
        try:
            target = date.fromisoformat(target_date_str)
        except ValueError:
            return jsonify({"error": "date must be YYYY-MM-DD"}), 400
        start = end = target
    else:
        start = date(2000, 1, 1)
        end = date.today()

    repo = PGMealEntryRepository(_session())
    meals = repo.get_by_user(user_id, start, end)
    return jsonify([
        {
            "id": m.id,
            "meal_name": m.meal_name,
            "logged_at": m.logged_at.isoformat() if m.logged_at else None,
            "total_calories": m.total_calories(),
            "food_items": [
                {
                    "name": f.name,
                    "calories": f.calories,
                    "protein_g": f.protein_g,
                    "carbs_g": f.carbs_g,
                    "fat_g": f.fat_g,
                }
                for f in m.food_items
            ],
        }
        for m in meals
    ]), 200
