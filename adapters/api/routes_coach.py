import csv
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import io

from adapters.db.pg_repositories import (
    PGUserRepository, PGWorkoutSessionRepository, PGMealEntryRepository,
    PGBodyMeasurementRepository, PGFitnessGoalRepository
)
from adapters.api.report_generator import ReportGenerator
from domain.services.progress_analyser import ProgressAnalyser


def _build_csv(client, sessions, meals, measurements, goals, start, end) -> bytes:
    """Build a detailed CSV with individual workout sessions, meals, and a summary."""
    buf = io.StringIO()
    writer = csv.writer(buf)

    # ---- Workouts ----
    writer.writerow(["=== WORKOUT SESSIONS ==="])
    writer.writerow(["Date", "Exercise", "Duration (min)", "Sets", "Reps", "Notes"])
    sessions_sorted = sorted(sessions, key=lambda s: s.session_date)
    for s in sessions_sorted:
        for e in s.exercises:
            writer.writerow([
                s.session_date.isoformat(),
                e.name,
                e.duration_minutes,
                e.sets if e.sets else "",
                e.reps if e.reps else "",
                e.notes or "",
            ])
    if not sessions_sorted:
        writer.writerow(["No workout sessions in this period."])

    writer.writerow([])

    # ---- Meals ----
    writer.writerow(["=== MEAL LOG ==="])
    writer.writerow(["Date", "Meal", "Food Item", "Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)"])
    meals_sorted = sorted(meals, key=lambda m: m.logged_at)
    for m in meals_sorted:
        for f in m.food_items:
            writer.writerow([
                m.logged_at.date().isoformat(),
                m.meal_name,
                f.name,
                f.calories,
                f.protein_g,
                f.carbs_g,
                f.fat_g,
            ])
    if not meals_sorted:
        writer.writerow(["No meal entries in this period."])

    writer.writerow([])

    # ---- Measurements ----
    writer.writerow(["=== BODY MEASUREMENTS ==="])
    writer.writerow(["Date", "Type", "Value", "Unit"])
    for m in sorted(measurements, key=lambda m: m.recorded_date):
        writer.writerow([m.recorded_date.isoformat(), m.measurement_type, m.value, m.unit])
    if not measurements:
        writer.writerow(["No measurements in this period."])

    writer.writerow([])

    # ---- Goals ----
    writer.writerow(["=== GOALS ==="])
    writer.writerow(["Description", "Target", "Current", "Unit", "Deadline", "Status"])
    for g in goals:
        writer.writerow([g.description, g.target_value, g.current_value, g.unit, g.deadline.isoformat(), g.status])
    if not goals:
        writer.writerow(["No goals found."])

    writer.writerow([])

    # ---- Summary ----
    writer.writerow(["=== SUMMARY ==="])
    writer.writerow(["Client", f"{client.full_name()} ({client.email})"])
    writer.writerow(["Period", f"{start.isoformat()} to {end.isoformat()}"])
    writer.writerow(["Total Workout Sessions", len(sessions)])
    total_duration = sum(sum(e.duration_minutes for e in s.exercises) for s in sessions)
    writer.writerow(["Total Duration (min)", total_duration])
    weight_readings = sorted(
        [m for m in measurements if m.measurement_type == "weight_kg"],
        key=lambda m: m.recorded_date,
    )
    if len(weight_readings) >= 2:
        change = round(weight_readings[-1].value - weight_readings[0].value, 2)
        writer.writerow(["Weight Change (kg)", f"{change:+.2f}"])
    else:
        writer.writerow(["Weight Change (kg)", "insufficient data"])

    return buf.getvalue().encode("utf-8")

coach_bp = Blueprint("coach", __name__)


def _require_coach():
    claims = get_jwt()
    if claims.get("role") != "coach":
        return False
    return True


@coach_bp.get("/dashboard")
@jwt_required()
def dashboard():
    if not _require_coach():
        return jsonify({"error": "Coach access only"}), 403

    coach_id = int(get_jwt_identity())
    from adapters.api import get_db
    user_repo = PGUserRepository(get_db())

    clients = user_repo.list_clients(coach_id)

    search = request.args.get("search", "").lower()
    if search:
        clients = [
            c for c in clients
            if search in c.full_name().lower() or search in c.email.lower()
        ]

    return jsonify([
        {
            "id": c.id,
            "name": c.full_name(),
            "email": c.email,
            "fitness_level": c.fitness_level,
        }
        for c in clients
    ]), 200


@coach_bp.get("/clients/<int:client_id>/progress")
@jwt_required()
def client_progress(client_id: int):
    if not _require_coach():
        return jsonify({"error": "Coach access only"}), 403

    end = date.today()
    start = end - timedelta(days=28)
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    try:
        if start_str:
            start = date.fromisoformat(start_str)
        if end_str:
            end = date.fromisoformat(end_str)
    except ValueError:
        return jsonify({"error": "start and end must be YYYY-MM-DD"}), 400

    from adapters.api import get_db
    db = get_db()

    user_repo = PGUserRepository(db)
    client = user_repo.get_by_id(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    sessions = PGWorkoutSessionRepository(db).get_by_user(client_id, start, end)
    meals = PGMealEntryRepository(db).get_by_user(client_id, start, end)
    measurements = PGBodyMeasurementRepository(db).get_by_user(client_id, start, end)
    goals = PGFitnessGoalRepository(db).get_by_user(client_id)

    analyser = ProgressAnalyser()
    report = analyser.generate_weekly_summary(
        user_id=client_id,
        measurements=measurements,
        sessions=sessions,
        meals=meals,
        goals=goals,
        start=start,
        end=end,
    )

    fmt = request.args.get("format", "json").lower()

    if fmt == "csv":
        csv_bytes = _build_csv(client, sessions, meals, measurements, goals, start, end)
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"progress_{client.full_name().replace(' ', '_')}_{start}_{end}.csv",
        )

    if fmt == "pdf":
        gen = ReportGenerator()
        pdf_bytes = gen.export_pdf(report, user_name=client.full_name())
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"progress_{client_id}_{start}_{end}.pdf",
        )

    # default JSON response
    return jsonify({
        "client": {"id": client.id, "name": client.full_name()},
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "weight_change_kg": report.weight_change_kg,
        "workout_frequency": report.workout_frequency,
        "goal_completion_rate": report.goal_completion_rate,
        "summary": report.summary_line(),
    }), 200
