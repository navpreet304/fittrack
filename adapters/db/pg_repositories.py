import json
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

from adapters.db.models import (
    UserModel, FitnessGoalModel, WorkoutSessionModel,
    MealEntryModel, BodyMeasurementModel, BadgeModel, NotificationModel
)
from domain.entities.user import User
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.workout_session import WorkoutSession, Exercise
from domain.entities.meal_entry import MealEntry, FoodItem
from domain.entities.body_measurement import BodyMeasurement
from domain.entities.badge_notification import Badge, Notification
from ports.repositories import (
    UserRepository, WorkoutSessionRepository, MealEntryRepository,
    BodyMeasurementRepository, FitnessGoalRepository, BadgeRepository,
    NotificationRepository
)


def _user_to_domain(row: UserModel) -> User:
    u = User(
        email=row.email,
        first_name=row.first_name,
        last_name=row.last_name,
        date_of_birth=row.date_of_birth,
        role=row.role,
        id=row.id,
        height_cm=row.height_cm,
        fitness_level=row.fitness_level,
    )
    u.hashed_password = row.hashed_password
    return u


def _session_to_domain(row: WorkoutSessionModel) -> WorkoutSession:
    raw = json.loads(row.exercises_json or "[]")
    exercises = [
        Exercise(
            name=e["name"],
            duration_minutes=e["duration_minutes"],
            sets=e.get("sets", 0),
            reps=e.get("reps", 0),
            notes=e.get("notes", ""),
        )
        for e in raw
    ]
    return WorkoutSession(
        user_id=row.user_id,
        session_date=row.session_date,
        exercises=exercises,
        id=row.id,
        synced=row.synced,
    )


def _meal_to_domain(row: MealEntryModel) -> MealEntry:
    raw = json.loads(row.food_items_json or "[]")
    items = [
        FoodItem(
            name=f["name"],
            calories=f["calories"],
            serving_size_g=f.get("serving_size_g", 100.0),
            protein_g=f.get("protein_g", 0.0),
            carbs_g=f.get("carbs_g", 0.0),
            fat_g=f.get("fat_g", 0.0),
        )
        for f in raw
    ]
    return MealEntry(
        user_id=row.user_id,
        meal_name=row.meal_name,
        food_items=items,
        logged_at=row.logged_at,
        id=row.id,
        sync_status=row.sync_status,
    )


class PGUserRepository(UserRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, user: User) -> User:
        row = UserModel(
            email=user.email,
            hashed_password=user.hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=user.date_of_birth,
            role=user.role,
            height_cm=user.height_cm,
            fitness_level=user.fitness_level,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        user.id = row.id
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        row = self._db.get(UserModel, user_id)
        return _user_to_domain(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self._db.query(UserModel).filter_by(email=email).first()
        return _user_to_domain(row) if row else None

    def list_clients(self, coach_id: int) -> List[User]:
        # Show all regular users — both assigned and newly registered
        rows = self._db.query(UserModel).filter_by(role="user").all()
        return [_user_to_domain(r) for r in rows]


class PGWorkoutSessionRepository(WorkoutSessionRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, session: WorkoutSession) -> WorkoutSession:
        exercises_data = [
            {
                "name": e.name,
                "duration_minutes": e.duration_minutes,
                "sets": e.sets,
                "reps": e.reps,
                "notes": e.notes,
            }
            for e in session.exercises
        ]
        row = WorkoutSessionModel(
            user_id=session.user_id,
            session_date=session.session_date,
            exercises_json=json.dumps(exercises_data),
            synced=session.synced,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        session.id = row.id
        return session

    def get_by_user(self, user_id: int, start: date, end: date) -> List[WorkoutSession]:
        rows = (
            self._db.query(WorkoutSessionModel)
            .filter(
                WorkoutSessionModel.user_id == user_id,
                WorkoutSessionModel.session_date >= start,
                WorkoutSessionModel.session_date <= end,
            )
            .all()
        )
        return [_session_to_domain(r) for r in rows]

    def get_by_id(self, session_id: int) -> Optional[WorkoutSession]:
        row = self._db.get(WorkoutSessionModel, session_id)
        return _session_to_domain(row) if row else None


class PGMealEntryRepository(MealEntryRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, meal: MealEntry) -> MealEntry:
        items_data = [
            {
                "name": f.name,
                "calories": f.calories,
                "serving_size_g": f.serving_size_g,
                "protein_g": f.protein_g,
                "carbs_g": f.carbs_g,
                "fat_g": f.fat_g,
            }
            for f in meal.food_items
        ]
        row = MealEntryModel(
            user_id=meal.user_id,
            meal_name=meal.meal_name,
            food_items_json=json.dumps(items_data),
            logged_at=meal.logged_at,
            sync_status=meal.sync_status,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        meal.id = row.id
        return meal

    def get_by_user(self, user_id: int, start: date, end: date) -> List[MealEntry]:
        rows = (
            self._db.query(MealEntryModel)
            .filter(
                MealEntryModel.user_id == user_id,
                MealEntryModel.logged_at >= datetime.combine(start, datetime.min.time()),
                MealEntryModel.logged_at <= datetime.combine(end, datetime.max.time()),
            )
            .all()
        )
        return [_meal_to_domain(r) for r in rows]

    def get_pending_sync(self, user_id: int) -> List[MealEntry]:
        rows = (
            self._db.query(MealEntryModel)
            .filter_by(user_id=user_id, sync_status="pending")
            .all()
        )
        return [_meal_to_domain(r) for r in rows]


class PGBodyMeasurementRepository(BodyMeasurementRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, m: BodyMeasurement) -> BodyMeasurement:
        row = BodyMeasurementModel(
            user_id=m.user_id,
            measurement_type=m.measurement_type,
            value=m.value,
            unit=m.unit,
            recorded_date=m.recorded_date,
            notes=m.notes,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        m.id = row.id
        return m

    def get_by_user(self, user_id: int, start: date, end: date) -> List[BodyMeasurement]:
        rows = (
            self._db.query(BodyMeasurementModel)
            .filter(
                BodyMeasurementModel.user_id == user_id,
                BodyMeasurementModel.recorded_date >= start,
                BodyMeasurementModel.recorded_date <= end,
            )
            .all()
        )
        return [
            BodyMeasurement(
                user_id=r.user_id,
                measurement_type=r.measurement_type,
                value=r.value,
                unit=r.unit,
                recorded_date=r.recorded_date,
                notes=r.notes,
                id=r.id,
            )
            for r in rows
        ]


class PGFitnessGoalRepository(FitnessGoalRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, goal: FitnessGoal) -> FitnessGoal:
        row = FitnessGoalModel(
            user_id=goal.user_id,
            description=goal.description,
            target_value=goal.target_value,
            current_value=goal.current_value,
            unit=goal.unit,
            deadline=goal.deadline,
            status=goal.status,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        goal.id = row.id
        return goal

    def get_by_user(self, user_id: int) -> List[FitnessGoal]:
        rows = self._db.query(FitnessGoalModel).filter_by(user_id=user_id).all()
        return [
            FitnessGoal(
                user_id=r.user_id,
                description=r.description,
                target_value=r.target_value,
                current_value=r.current_value,
                unit=r.unit,
                deadline=r.deadline,
                status=r.status,
                id=r.id,
            )
            for r in rows
        ]

    def update(self, goal: FitnessGoal) -> FitnessGoal:
        row = self._db.get(FitnessGoalModel, goal.id)
        if not row:
            raise ValueError(f"Goal {goal.id} not found")
        row.status = goal.status
        row.current_value = goal.current_value
        self._db.commit()
        return goal


class PGBadgeRepository(BadgeRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, badge: Badge) -> Badge:
        row = BadgeModel(
            user_id=badge.user_id,
            name=badge.name,
            description=badge.description,
            condition=badge.condition,
            date_awarded=badge.date_awarded,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        badge.id = row.id
        return badge

    def get_by_user(self, user_id: int) -> List[Badge]:
        rows = self._db.query(BadgeModel).filter_by(user_id=user_id).all()
        return [
            Badge(
                user_id=r.user_id,
                name=r.name,
                description=r.description,
                condition=r.condition,
                date_awarded=r.date_awarded,
                id=r.id,
            )
            for r in rows
        ]


class PGNotificationRepository(NotificationRepository):

    def __init__(self, db: DBSession):
        self._db = db

    def save(self, notif: Notification) -> Notification:
        row = NotificationModel(
            user_id=notif.user_id,
            message=notif.message,
            channel=notif.channel,
            status=notif.status,
            scheduled_at=notif.scheduled_at,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        notif.id = row.id
        return notif

    def get_pending(self) -> List[Notification]:
        rows = self._db.query(NotificationModel).filter_by(status="pending").all()
        return [
            Notification(
                user_id=r.user_id,
                message=r.message,
                channel=r.channel,
                status=r.status,
                scheduled_at=r.scheduled_at,
                id=r.id,
            )
            for r in rows
        ]

    def update(self, notif: Notification) -> Notification:
        row = self._db.get(NotificationModel, notif.id)
        if not row:
            raise ValueError(f"Notification {notif.id} not found")
        row.status = notif.status
        row.sent_at = notif.sent_at
        self._db.commit()
        return notif
