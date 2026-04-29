from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List


@dataclass
class WeeklyStat:
    week_start: date
    workouts: int
    avg_calories: float
    weight_kg: Optional[float]


@dataclass
class ProgressReport:
    user_id: int
    period_start: date
    period_end: date
    weight_change_kg: float = 0.0
    workout_frequency: int = 0       # sessions in period
    goal_completion_rate: float = 0.0
    weekly_stats: List[WeeklyStat] = field(default_factory=list)
    export_format: str = "csv"       # csv or pdf
    id: Optional[int] = None

    def summary_line(self) -> str:
        direction = "lost" if self.weight_change_kg < 0 else "gained"
        kg = abs(self.weight_change_kg)
        return (
            f"{self.period_start} to {self.period_end}: "
            f"{direction} {kg:.1f} kg, "
            f"{self.workout_frequency} workouts, "
            f"{self.goal_completion_rate:.0f}% goals hit"
        )
