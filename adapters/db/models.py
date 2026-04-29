from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    Boolean, ForeignKey, Text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    role = Column(String(20), default="user")
    height_cm = Column(Float, nullable=True)
    fitness_level = Column(String(20), nullable=True)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    goals = relationship("FitnessGoalModel", back_populates="user", cascade="all, delete")
    sessions = relationship("WorkoutSessionModel", back_populates="user", cascade="all, delete")
    meals = relationship("MealEntryModel", back_populates="user", cascade="all, delete")
    measurements = relationship("BodyMeasurementModel", back_populates="user", cascade="all, delete")
    badges = relationship("BadgeModel", back_populates="user", cascade="all, delete")
    notifications = relationship("NotificationModel", back_populates="user", cascade="all, delete")


class FitnessGoalModel(Base):
    __tablename__ = "fitness_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String(500), nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    unit = Column(String(50), nullable=False)
    deadline = Column(Date, nullable=False)
    status = Column(String(20), default="active")

    user = relationship("UserModel", back_populates="goals")


class WorkoutSessionModel(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    exercises_json = Column(Text, nullable=False, default="[]")
    synced = Column(Boolean, default=True)

    user = relationship("UserModel", back_populates="sessions")


class MealEntryModel(Base):
    __tablename__ = "meal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meal_name = Column(String(100), nullable=False)
    food_items_json = Column(Text, nullable=False, default="[]")
    logged_at = Column(DateTime, default=datetime.now)
    sync_status = Column(String(20), default="synced")

    user = relationship("UserModel", back_populates="meals")


class BodyMeasurementModel(Base):
    __tablename__ = "body_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    recorded_date = Column(Date, nullable=False)
    notes = Column(String(500), default="")

    user = relationship("UserModel", back_populates="measurements")


class BadgeModel(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    condition = Column(String(100), nullable=False)
    date_awarded = Column(Date, nullable=False)

    user = relationship("UserModel", back_populates="badges")


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), default="email")
    status = Column(String(20), default="pending")
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", back_populates="notifications")


def init_db(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    kwargs = {} if is_sqlite else {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    engine = create_engine(database_url, **kwargs)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
