from datetime import date
from typing import List
from domain.entities.meal_entry import MealEntry
from domain.entities.user import User


# rough daily calorie targets by goal type and fitness level
_BASE_TARGETS = {
    "lose_weight":    {"beginner": 1800, "intermediate": 1700, "advanced": 1600},
    "maintain":       {"beginner": 2200, "intermediate": 2200, "advanced": 2200},
    "gain_muscle":    {"beginner": 2600, "intermediate": 2800, "advanced": 3000},
}


class CalorieCalculator:

    def calculate_daily_intake(self, meals: List[MealEntry], target_date: date) -> float:
        """
        Sum calories across all meal entries for a given date.
        Only counts meals that were actually logged on that date.
        """
        total = 0.0
        for meal in meals:
            if meal.logged_at.date() == target_date:
                total += meal.total_calories()
        return round(total, 1)

    def get_target_calories(self, user: User, goal_type: str = "maintain") -> float:
        """
        Rough daily target based on the user's goal and fitness level.
        Not a substitute for a proper TDEE calc but good enough for this context.
        """
        level = user.fitness_level or "beginner"
        bucket = _BASE_TARGETS.get(goal_type, _BASE_TARGETS["maintain"])
        base = bucket.get(level, 2200)

        # nudge based on age — metabolism slows a bit after 30
        age = user.age()
        if age > 50:
            base -= 200
        elif age > 30:
            base -= 100

        return float(base)

    def compare_intake_to_target(
        self,
        meals: List[MealEntry],
        user: User,
        target_date: date,
        goal_type: str = "maintain",
    ) -> float:
        """
        Positive = ate more than target. Negative = under target.
        """
        intake = self.calculate_daily_intake(meals, target_date)
        target = self.get_target_calories(user, goal_type)
        return round(intake - target, 1)
