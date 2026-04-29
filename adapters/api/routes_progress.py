import io
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from adapters.db.pg_repositories import (
    PGWorkoutSessionRepository, PGMealEntryRepository,
    PGBodyMeasurementRepository, PGFitnessGoalRepository, PGUserRepository,
    PGBadgeRepository
)
from adapters.api.report_generator import ReportGenerator
from domain.entities.body_measurement import BodyMeasurement
from domain.entities.fitness_goal import FitnessGoal
from domain.services.progress_analyser import ProgressAnalyser

progress_bp = Blueprint("progress", __name__)


def _get_repos(db):
    return (
        PGWorkoutSessionRepository(db),
        PGMealEntryRepository(db),
        PGBodyMeasurementRepository(db),
        PGFitnessGoalRepository(db),
        PGUserRepository(db),
    )


@progress_bp.get("/<int:user_id>/progress")
@jwt_required()
def get_progress(user_id: int):
    caller_id = int(get_jwt_identity())
    claims = get_jwt()
    is_coach = claims.get("role") == "coach"
    if caller_id != user_id and not is_coach:
        return jsonify({"error": "Forbidden"}), 403

    end = date.today()
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    try:
        start = date.fromisoformat(start_str) if start_str else end - timedelta(days=28)
        end = date.fromisoformat(end_str) if end_str else end
    except ValueError:
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400

    from adapters.api import get_db
    db = get_db()
    workout_repo, meal_repo, measurement_repo, goal_repo, user_repo = _get_repos(db)

    if user_repo.get_by_id(user_id) is None:
        return jsonify({"error": "User not found"}), 404

    sessions = workout_repo.get_by_user(user_id, start, end)
    meals = meal_repo.get_by_user(user_id, start, end)
    measurements = measurement_repo.get_by_user(user_id, start, end)
    goals = goal_repo.get_by_user(user_id)

    analyser = ProgressAnalyser()
    report = analyser.generate_weekly_summary(
        user_id=user_id,
        measurements=measurements,
        sessions=sessions,
        meals=meals,
        goals=goals,
        start=start,
        end=end,
    )

    fmt = request.args.get("format", "json").lower()
    if fmt in ("csv", "pdf"):
        if not is_coach:
            return jsonify({"error": "Coach access only for export formats"}), 403
        gen = ReportGenerator()
        if fmt == "csv":
            return send_file(
                io.BytesIO(gen.export_csv(report)),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"progress_{user_id}_{start}_{end}.csv",
            )
        target_user = user_repo.get_by_id(user_id)
        name = target_user.full_name() if target_user else f"User {user_id}"
        return send_file(
            io.BytesIO(gen.export_pdf(report, user_name=name)),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"progress_{user_id}_{start}_{end}.pdf",
        )

    return jsonify({
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "weight_change_kg": report.weight_change_kg,
        "workout_frequency": report.workout_frequency,
        "goal_completion_rate": report.goal_completion_rate,
        "weekly_stats": [
            {
                "week_start": w.week_start.isoformat(),
                "workouts": w.workouts,
                "avg_calories": w.avg_calories,
                "weight_kg": w.weight_kg,
            }
            for w in report.weekly_stats
        ],
    }), 200


@progress_bp.post("/<int:user_id>/measurements")
@jwt_required()
def add_measurement(user_id: int):
    caller_id = int(get_jwt_identity())
    if caller_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True)
    required = ["measurement_type", "value", "unit", "recorded_date"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400

    try:
        m = BodyMeasurement(
            user_id=user_id,
            measurement_type=data["measurement_type"],
            value=float(data["value"]),
            unit=data["unit"],
            recorded_date=date.fromisoformat(data["recorded_date"]),
            notes=data.get("notes", ""),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    from adapters.api import get_db
    repo = PGBodyMeasurementRepository(get_db())
    saved = repo.save(m)

    return jsonify({
        "id": saved.id,
        "measurement_type": saved.measurement_type,
        "value": saved.value,
        "unit": saved.unit,
        "recorded_date": saved.recorded_date.isoformat(),
    }), 201


@progress_bp.get("/<int:user_id>/badges")
@jwt_required()
def get_badges(user_id: int):
    caller_id = int(get_jwt_identity())
    if caller_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    from adapters.api import get_db
    repo = PGBadgeRepository(get_db())
    badges = repo.get_by_user(user_id)

    return jsonify([
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "condition": b.condition,
            "date_awarded": b.date_awarded.isoformat(),
        }
        for b in badges
    ]), 200


@progress_bp.post("/<int:user_id>/goals")
@jwt_required()
def add_goal(user_id: int):
    caller_id = int(get_jwt_identity())
    if caller_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True)
    required = ["description", "target_value", "unit", "deadline"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400

    try:
        goal = FitnessGoal(
            user_id=user_id,
            description=data["description"],
            target_value=float(data["target_value"]),
            unit=data["unit"],
            deadline=date.fromisoformat(data["deadline"]),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    from adapters.api import get_db
    repo = PGFitnessGoalRepository(get_db())
    saved = repo.save(goal)

    return jsonify({
        "id": saved.id,
        "description": saved.description,
        "target_value": saved.target_value,
        "unit": saved.unit,
        "deadline": saved.deadline.isoformat(),
        "status": saved.status,
    }), 201
