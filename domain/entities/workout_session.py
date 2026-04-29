from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Exercise:
    name: str
    duration_minutes: int
    sets: int = 0
    reps: int = 0
    notes: str = ""


@dataclass
class WorkoutSession:
    user_id: int
    session_date: date
    exercises: List[Exercise] = field(default_factory=list)
    id: Optional[int] = None
    synced: bool = True   # False when queued offline

    def add_exercise(self, ex: Exercise) -> None:
        self.exercises.append(ex)

    def total_duration(self, sessions=None) -> int:
        # Instance use: returns this session's duration.
        # Static-style use (passing a list of sessions): returns the combined duration across them.
        if sessions is None:
            return sum(e.duration_minutes for e in self.exercises)
        return sum(
            sum(ex.duration_minutes for ex in s.exercises)
            for s in sessions
        )

    @staticmethod
    def total_duration_for(sessions: List["WorkoutSession"]) -> int:
        return sum(
            sum(ex.duration_minutes for ex in s.exercises)
            for s in sessions
        )

    def exercise_count(self) -> int:
        return len(self.exercises)

    def to_summary(self) -> dict:
        return {
            "date": self.session_date.isoformat(),
            "exercises": self.exercise_count(),
            "total_minutes": self.total_duration(),
        }
