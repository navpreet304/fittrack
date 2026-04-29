from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Badge:
    user_id: int
    name: str
    description: str
    condition: str       # machine-readable key e.g. "7_day_streak"
    date_awarded: Optional[date] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.date_awarded is None:
            self.date_awarded = date.today()


# badge definitions the system knows about
BADGE_CATALOGUE = {
    "7_day_streak": {
        "name": "Consistency Star",
        "description": "Logged a workout every day for 7 days straight.",
    },
    "first_goal": {
        "name": "Goal Crusher",
        "description": "Completed your first fitness goal.",
    },
    "first_workout": {
        "name": "Early Bird",
        "description": "Logged your first workout session.",
    },
    "10_workouts": {
        "name": "Century Club",
        "description": "Logged 10 workout sessions total.",
    },
    "first_meal_log": {
        "name": "Calorie Tracker",
        "description": "Logged your first meal entry.",
    },
}


@dataclass
class Notification:
    user_id: int
    message: str
    channel: str = "email"     # email only for now, extensible later
    status: str = "pending"    # pending / sent / failed
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    id: Optional[int] = None

    def mark_sent(self) -> None:
        self.status = "sent"
        self.sent_at = datetime.now()

    def mark_failed(self) -> None:
        self.status = "failed"
