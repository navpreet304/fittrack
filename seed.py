#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from adapters.db.models import (  # noqa: E402
    BadgeModel,
    BodyMeasurementModel,
    FitnessGoalModel,
    MealEntryModel,
    NotificationModel,
    UserModel,
    WorkoutSessionModel,
    init_db,
)
from adapters.db.pg_repositories import (  # noqa: E402
    PGBodyMeasurementRepository,
    PGFitnessGoalRepository,
    PGMealEntryRepository,
    PGUserRepository,
    PGWorkoutSessionRepository,
)
from config.settings import get_config  # noqa: E402
from domain.entities.body_measurement import BodyMeasurement  # noqa: E402
from domain.entities.fitness_goal import FitnessGoal  # noqa: E402
from domain.entities.meal_entry import FoodItem, MealEntry  # noqa: E402
from domain.entities.user import User  # noqa: E402
from domain.entities.workout_session import Exercise, WorkoutSession  # noqa: E402


EXERCISE_POOL = [
    ("Push-ups", 15, 3, 20),
    ("Running", 30, 0, 0),
    ("Squats", 20, 4, 15),
    ("Plank", 10, 3, 0),
    ("Cycling", 45, 0, 0),
    ("Deadlift", 25, 3, 8),
    ("Pull-ups", 12, 3, 10),
]

MEALS_DATA = [
    ("breakfast", [("Oats 100g", 389, 17, 66, 7), ("Banana", 89, 1.1, 23, 0.3)]),
    ("lunch", [("Chicken Breast 150g", 248, 46, 0, 5.4), ("Brown Rice 100g", 216, 4.5, 45, 1.8)]),
    ("dinner", [("Salmon 150g", 312, 30, 0, 19.5), ("Broccoli 100g", 34, 2.8, 7, 0.4)]),
    ("snack", [("Greek Yogurt 150g", 89, 15, 5.4, 0.6), ("Almonds 30g", 164, 6, 6, 14)]),
]

WEIGHT_SERIES = [87.5, 87.1, 86.8, 86.5, 86.2, 86.0, 85.7]
DEMO_COACH_SECRET = os.getenv("FITTRACK_DEMO_COACH_PASSWORD", "coach123")
DEMO_USER_SECRET = os.getenv("FITTRACK_DEMO_USER_PASSWORD", "user123")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed FitTrack demo data, or only the exercise and food datasets.",
    )
    parser.add_argument(
        "--dataset",
        choices=["all", "exercises", "foods"],
        default="all",
        help="Choose which dataset to seed. Default seeds the full demo.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many days of exercise or food history to create for focused dataset runs.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing demo data before seeding.",
    )
    return parser


def _clear_existing_data(db) -> None:
    for model in (
        NotificationModel,
        BadgeModel,
        BodyMeasurementModel,
        MealEntryModel,
        WorkoutSessionModel,
        FitnessGoalModel,
        UserModel,
    ):
        db.query(model).delete()
    db.commit()


def _get_or_create_demo_user(user_repo: PGUserRepository, *, role: str) -> User:
    email = "coach@fittrack.com" if role == "coach" else "user@fittrack.com"
    existing = user_repo.get_by_email(email)
    if existing:
        return existing

    if role == "coach":
        person = User(
            email=email,
            first_name="Sarah",
            last_name="Mitchell",
            date_of_birth=date(1985, 3, 12),
            role="coach",
            fitness_level="advanced",
        )
        secret = DEMO_COACH_SECRET
    else:
        person = User(
            email=email,
            first_name="James",
            last_name="Walker",
            date_of_birth=date(1993, 7, 22),
            role="user",
            height_cm=178.0,
            fitness_level="intermediate",
        )
        secret = DEMO_USER_SECRET

    person.set_password(secret)
    return user_repo.save(person)


def _seed_goals(goal_repo: PGFitnessGoalRepository, user: User) -> int:
    goal = FitnessGoal(
        user_id=user.id,
        description="Lose 5kg in 3 months",
        target_value=5.0,
        unit="kg",
        deadline=date.today() + timedelta(days=90),
        current_value=1.5,
    )
    goal_repo.save(goal)
    return 1


def _seed_exercise_history(workout_repo: PGWorkoutSessionRepository, user: User, days: int) -> int:
    for index in range(days):
        session_date = date.today() - timedelta(days=index)
        exercise_name, duration, sets, reps = EXERCISE_POOL[index % len(EXERCISE_POOL)]
        session = WorkoutSession(user_id=user.id, session_date=session_date)
        session.add_exercise(
            Exercise(
                name=exercise_name,
                duration_minutes=duration,
                sets=sets,
                reps=reps,
            )
        )
        workout_repo.save(session)
    return days


def _seed_food_history(meal_repo: PGMealEntryRepository, user: User, days: int) -> int:
    meal_count = 0
    for index in range(days):
        entry_date = date.today() - timedelta(days=index)
        for meal_name, foods in MEALS_DATA:
            meal = MealEntry(user_id=user.id, meal_name=meal_name)
            for food_name, calories, protein, carbs, fat in foods:
                meal.add_food(
                    FoodItem(
                        name=food_name,
                        calories=calories,
                        protein_g=protein,
                        carbs_g=carbs,
                        fat_g=fat,
                    )
                )
            meal.logged_at = datetime.combine(entry_date, datetime.min.time().replace(hour=8))
            meal_repo.save(meal)
            meal_count += 1
    return meal_count


def _seed_measurements(measurement_repo: PGBodyMeasurementRepository, user: User) -> int:
    for index, weight in enumerate(WEIGHT_SERIES):
        measurement_date = date.today() - timedelta(days=(len(WEIGHT_SERIES) - index - 1) * 4)
        measurement_repo.save(
            BodyMeasurement(
                user_id=user.id,
                measurement_type="weight_kg",
                value=weight,
                unit="kg",
                recorded_date=measurement_date,
            )
        )
    return len(WEIGHT_SERIES)


def seed(dataset: str = "all", days: int = 7, reset: bool = False) -> dict[str, int]:
    cfg = get_config()
    _, session_factory = init_db(cfg.DATABASE_URL)
    db = session_factory()

    if reset:
        print("Resetting existing demo data...")
        _clear_existing_data(db)

    user_repo = PGUserRepository(db)
    workout_repo = PGWorkoutSessionRepository(db)
    meal_repo = PGMealEntryRepository(db)
    measurement_repo = PGBodyMeasurementRepository(db)
    goal_repo = PGFitnessGoalRepository(db)

    print("Ensuring demo users exist...")
    coach = _get_or_create_demo_user(user_repo, role="coach")
    user = _get_or_create_demo_user(user_repo, role="user")
    print(f"  Coach: {coach.full_name()} (id={coach.id})")
    print(f"  User:  {user.full_name()} (id={user.id})")
    # assign user to coach so the coach dashboard can see them
    db.query(UserModel).filter_by(id=user.id).update({"coach_id": coach.id})
    db.commit()

    stats = {"goals": 0, "workouts": 0, "meals": 0, "measurements": 0}

    if dataset == "all":
        print("Seeding full demo dataset...")
        stats["goals"] = _seed_goals(goal_repo, user)
        stats["workouts"] = _seed_exercise_history(workout_repo, user, 7)
        stats["meals"] = _seed_food_history(meal_repo, user, 7)
        stats["measurements"] = _seed_measurements(measurement_repo, user)
    elif dataset == "exercises":
        print(f"Seeding {days} days of exercise history...")
        stats["workouts"] = _seed_exercise_history(workout_repo, user, days)
    elif dataset == "foods":
        print(f"Seeding {days} days of food history...")
        stats["meals"] = _seed_food_history(meal_repo, user, days)

    print("\nSeed complete.")
    print(f"  Goals: {stats['goals']}")
    print(f"  Workout sessions: {stats['workouts']}")
    print(f"  Meal entries: {stats['meals']}")
    print(f"  Measurements: {stats['measurements']}")
    print("  Login as coach: coach@fittrack.com / coach123")
    print("  Login as user:  user@fittrack.com / user123")

    db.close()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    seed(dataset=args.dataset, days=args.days, reset=args.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
