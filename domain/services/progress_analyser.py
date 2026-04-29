from datetime import date, timedelta
from typing import List
import statistics

from domain.entities.body_measurement import BodyMeasurement
from domain.entities.workout_session import WorkoutSession
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.meal_entry import MealEntry
from domain.entities.progress_report import ProgressReport, WeeklyStat
from domain.services.calorie_calculator import CalorieCalculator


class ProgressAnalyser:

    def __init__(self):
        self._calc = CalorieCalculator()

    def compare_weight_change(
        self,
        measurements: List[BodyMeasurement],
        start: date,
        end: date,
    ) -> dict:
        """
        Returns a dict with:
          - 'delta': weight change in kg (negative=loss, positive=gain, 0.0=no change)
          - 'direction': 'decrease', 'increase', or 'unchanged'
        Raises ValueError if two measurements share the same recorded date.
        """
        weights = [
            m for m in measurements
            if m.measurement_type == "weight_kg"
            and start <= m.recorded_date <= end
        ]

        if len(weights) < 2:
            return {"delta": 0.0, "direction": "unchanged"}

        dates = [m.recorded_date for m in weights]
        if len(dates) != len(set(dates)):
            raise ValueError(
                "Duplicate measurement dates found — cannot compare weight change."
            )

        weights.sort(key=lambda m: m.recorded_date)
        delta = round(weights[-1].value - weights[0].value, 2)

        if delta < 0:
            direction = "decrease"
        elif delta > 0:
            direction = "increase"
        else:
            direction = "unchanged"

        return {"delta": delta, "direction": direction}

    def calculate_workout_frequency(
        self,
        sessions: List[WorkoutSession],
        start: date,
        end: date,
    ) -> int:
        """How many workout sessions happened in the period."""
        return sum(1 for s in sessions if start <= s.session_date <= end)

    def calculate_goal_completion_rate(self, goals: List[FitnessGoal]) -> float:
        """
        Percentage of non-active goals that were achieved rather than missed.
        Returns 0.0 if there are no completed goals yet.
        """
        completed = [g for g in goals if g.status in ("achieved", "missed")]
        if not completed:
            return 0.0
        achieved = sum(1 for g in completed if g.status == "achieved")
        return round((achieved / len(completed)) * 100, 1)

    def generate_weekly_summary(
        self,
        user_id: int,
        measurements: List[BodyMeasurement],
        sessions: List[WorkoutSession],
        meals: List[MealEntry],
        goals: List[FitnessGoal],
        start: date,
        end: date,
    ) -> ProgressReport:
        """
        Builds a ProgressReport covering the given date range.
        Breaks it down week by week for the weekly_stats list.
        """
        try:
            weight_result = self.compare_weight_change(measurements, start, end)
            weight_change = weight_result["delta"]
        except ValueError:
            weight_change = 0.0
        freq = self.calculate_workout_frequency(sessions, start, end)
        goal_rate = self.calculate_goal_completion_rate(goals)

        weekly_stats = []
        cursor = start
        while cursor <= end:
            week_end = min(cursor + timedelta(days=6), end)

            week_sessions = [
                s for s in sessions if cursor <= s.session_date <= week_end
            ]
            week_meals = [
                m for m in meals if cursor <= m.logged_at.date() <= week_end
            ]

            # average daily calories for this week
            days_in_week = (week_end - cursor).days + 1
            total_cal = sum(
                self._calc.calculate_daily_intake(week_meals, cursor + timedelta(days=d))
                for d in range(days_in_week)
            )
            avg_cal = round(total_cal / days_in_week, 1) if days_in_week else 0.0

            weight_readings = [
                m.value for m in measurements
                if m.measurement_type == "weight_kg"
                and cursor <= m.recorded_date <= week_end
            ]
            week_weight = statistics.mean(weight_readings) if weight_readings else None

            weekly_stats.append(
                WeeklyStat(
                    week_start=cursor,
                    workouts=len(week_sessions),
                    avg_calories=avg_cal,
                    weight_kg=week_weight,
                )
            )
            cursor += timedelta(days=7)

        return ProgressReport(
            user_id=user_id,
            period_start=start,
            period_end=end,
            weight_change_kg=weight_change,
            workout_frequency=freq,
            goal_completion_rate=goal_rate,
            weekly_stats=weekly_stats,
        )
