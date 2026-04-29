from dataclasses import dataclass
from datetime import date
from typing import Optional


VALID_STATUSES = ("active", "achieved", "missed", "paused")


@dataclass
class FitnessGoal:
    user_id: int
    description: str
    target_value: float
    unit: str            # e.g. "kg", "km", "reps"
    deadline: date
    status: str = "active"
    current_value: float = 0.0
    id: Optional[int] = None

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")

    def progress_pct(self) -> float:
        if self.target_value == 0:
            return 0.0
        return round((self.current_value / self.target_value) * 100, 1)

    def is_achieved(self) -> bool:
        return self.current_value >= self.target_value

    def update_status(self) -> None:
        if self.is_achieved():
            self.status = "achieved"
        elif date.today() > self.deadline and not self.is_achieved():
            self.status = "missed"

    def days_remaining(self) -> int:
        delta = self.deadline - date.today()
        return max(delta.days, 0)

    def complete(self) -> None:
        self.status = "achieved"
        if self.current_value < self.target_value:
            self.current_value = self.target_value
