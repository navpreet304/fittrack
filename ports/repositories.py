from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from domain.entities.user import User
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.workout_session import WorkoutSession
from domain.entities.meal_entry import MealEntry
from domain.entities.body_measurement import BodyMeasurement
from domain.entities.badge_notification import Badge, Notification


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def list_clients(self, coach_id: int) -> List[User]: ...


class WorkoutSessionRepository(ABC):
    @abstractmethod
    def save(self, session: WorkoutSession) -> WorkoutSession: ...

    @abstractmethod
    def get_by_user(self, user_id: int, start: date, end: date) -> List[WorkoutSession]: ...

    @abstractmethod
    def get_by_id(self, session_id: int) -> Optional[WorkoutSession]: ...


class MealEntryRepository(ABC):
    @abstractmethod
    def save(self, meal: MealEntry) -> MealEntry: ...

    @abstractmethod
    def get_by_user(self, user_id: int, start: date, end: date) -> List[MealEntry]: ...

    @abstractmethod
    def get_pending_sync(self, user_id: int) -> List[MealEntry]: ...


class BodyMeasurementRepository(ABC):
    @abstractmethod
    def save(self, measurement: BodyMeasurement) -> BodyMeasurement: ...

    @abstractmethod
    def get_by_user(self, user_id: int, start: date, end: date) -> List[BodyMeasurement]: ...


class FitnessGoalRepository(ABC):
    @abstractmethod
    def save(self, goal: FitnessGoal) -> FitnessGoal: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> List[FitnessGoal]: ...

    @abstractmethod
    def update(self, goal: FitnessGoal) -> FitnessGoal: ...


class BadgeRepository(ABC):
    @abstractmethod
    def save(self, badge: Badge) -> Badge: ...

    @abstractmethod
    def get_by_user(self, user_id: int) -> List[Badge]: ...


class NotificationRepository(ABC):
    @abstractmethod
    def save(self, notif: Notification) -> Notification: ...

    @abstractmethod
    def get_pending(self) -> List[Notification]: ...

    @abstractmethod
    def update(self, notif: Notification) -> Notification: ...


class NutritionAPIClient(ABC):
    @abstractmethod
    def search_food(self, query: str) -> List[dict]: ...


class NotificationService(ABC):
    @abstractmethod
    def send(self, notif: Notification, recipient_email: str) -> bool: ...
