from datetime import date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from adapters.db.pg_repositories import (
    PGWorkoutSessionRepository, PGBadgeRepository, PGUserRepository, PGNotificationRepository
)
from domain.entities.workout_session import WorkoutSession, Exercise
from domain.entities.badge_notification import Notification
from domain.services.badge_checker import BadgeChecker

workouts_bp = Blueprint("workouts", __name__)


def _get_repos():
    from adapters.api import get_db
    db = get_db()
    return (
        PGWorkoutSessionRepository(db),
        PGBadgeRepository(db),
        PGUserRepository(db),
        PGNotificationRepository(db),
    )


@workouts_bp.post("")
@jwt_required()
def log_workout():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided"}), 400
    if "session_date" not in data or "exercises" not in data:
        return jsonify({"error": "session_date and exercises are required"}), 400
    if not isinstance(data["exercises"], list) or len(data["exercises"]) == 0:
        return jsonify({"error": "exercises must be a non-empty list"}), 400

    try:
        session_date = date.fromisoformat(data["session_date"])
    except ValueError:
        return jsonify({"error": "session_date must be YYYY-MM-DD"}), 400

    session = WorkoutSession(user_id=user_id, session_date=session_date)

    for ex_data in data["exercises"]:
        if "name" not in ex_data or "duration_minutes" not in ex_data:
            return jsonify({"error": "Each exercise needs name and duration_minutes"}), 400
        session.add_exercise(Exercise(
            name=ex_data["name"],
            duration_minutes=int(ex_data["duration_minutes"]),
            sets=ex_data.get("sets", 0),
            reps=ex_data.get("reps", 0),
            notes=ex_data.get("notes", ""),
        ))

    workout_repo, badge_repo, user_repo, notif_repo = _get_repos()
    saved = workout_repo.save(session)

    # check for new badges
    all_sessions = workout_repo.get_by_user(user_id, date(2000, 1, 1), date.today())
    existing_badges = badge_repo.get_by_user(user_id)
    checker = BadgeChecker()
    new_badges = checker.check_all(
        user_id=user_id,
        sessions=all_sessions,
        meals=[],
        goals=[],
        existing_badges=existing_badges,
    )
    awarded = []
    for badge in new_badges:
        badge_repo.save(badge)
        awarded.append({"name": badge.name, "description": badge.description})
        # create a pending notification so the user is informed of their new badge
        notif = Notification(
            user_id=user_id,
            message=f"You earned the '{badge.name}' badge! {badge.description}",
            channel="email",
        )
        notif_repo.save(notif)

    response = {
        "id": saved.id,
        "session_date": saved.session_date.isoformat(),
        "total_duration_minutes": saved.total_duration(),
        "exercise_count": saved.exercise_count(),
    }
    if awarded:
        response["badges_awarded"] = awarded

    return jsonify(response), 201


@workouts_bp.get("/<int:user_id>")
@jwt_required()
def get_workouts(user_id: int):
    caller_id = int(get_jwt_identity())
    if caller_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    start_str = request.args.get("start", "2000-01-01")
    end_str = request.args.get("end", date.today().isoformat())

    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400

    repo, _badge_repo, _user_repo, _notif_repo = _get_repos()
    sessions = repo.get_by_user(user_id, start, end)

    return jsonify([s.to_summary() for s in sessions]), 200
