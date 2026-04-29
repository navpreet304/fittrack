from datetime import date
from typing import List

from domain.entities.workout_session import WorkoutSession
from domain.entities.meal_entry import MealEntry
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.badge_notification import Badge, BADGE_CATALOGUE


class BadgeChecker:
    """
    Checks whether a user has earned any badges they don't already have.
    Returns a list of newly earned Badge objects.
    """

    def check_all(
        self,
        user_id: int,
        sessions: List[WorkoutSession],
        meals: List[MealEntry],
        goals: List[FitnessGoal],
        existing_badges: List[Badge],
    ) -> List[Badge]:
        already_earned = {b.condition for b in existing_badges}
        new_badges = []

        checks = [
            ("7_day_streak", self._has_7_day_streak(sessions)),
            ("first_goal", self._completed_first_goal(goals)),
            ("first_workout", len(sessions) >= 1),
            ("10_workouts", len(sessions) >= 10),
            ("first_meal_log", len(meals) >= 1),
        ]

        for condition, earned in checks:
            if earned and condition not in already_earned:
                meta = BADGE_CATALOGUE[condition]
                new_badges.append(
                    Badge(
                        user_id=user_id,
                        name=meta["name"],
                        description=meta["description"],
                        condition=condition,
                        date_awarded=date.today(),
                    )
                )

        return new_badges

    def _has_7_day_streak(self, sessions: List[WorkoutSession]) -> bool:
        if not sessions:
            return False
        session_dates = sorted({s.session_date for s in sessions}, reverse=True)
        streak = 1
        for i in range(1, len(session_dates)):
            if (session_dates[i - 1] - session_dates[i]).days == 1:
                streak += 1
                if streak >= 7:
                    return True
            else:
                streak = 1
        return False

    def _completed_first_goal(self, goals: List[FitnessGoal]) -> bool:
        return any(g.status == "achieved" for g in goals)
