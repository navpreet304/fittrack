"""
Unit Tests — FitTrack
=====================
Test 1: CalorieCalculator.calculate_daily_intake()
Test 2: ProgressAnalyser.compare_weight_change()
Test 3: WorkoutSession.total_duration()
"""

import pytest
from datetime import date, datetime, timedelta

from unittest.mock import MagicMock, patch
import smtplib

from domain.entities.meal_entry import MealEntry, FoodItem
from domain.entities.body_measurement import BodyMeasurement
from domain.entities.workout_session import WorkoutSession, Exercise
from domain.entities.fitness_goal import FitnessGoal
from domain.entities.badge_notification import Badge, Notification
from domain.entities.user import User
from domain.services.calorie_calculator import CalorieCalculator
from domain.services.progress_analyser import ProgressAnalyser
from domain.services.badge_checker import BadgeChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meal(user_id: int, calorie_list: list, target_date: date) -> MealEntry:
    """Create a MealEntry with one FoodItem per calorie value, logged on target_date."""
    meal = MealEntry(user_id=user_id, meal_name="test_meal")
    for cal in calorie_list:
        meal.add_food(FoodItem(name="food", calories=cal))
    meal.logged_at = datetime.combine(target_date, datetime.min.time().replace(hour=12))
    return meal


def _make_weight(user_id: int, value: float, recorded_date: date) -> BodyMeasurement:
    """Create a weight_kg BodyMeasurement."""
    return BodyMeasurement(
        user_id=user_id,
        measurement_type="weight_kg",
        value=value,
        unit="kg",
        recorded_date=recorded_date,
    )


def _make_session(durations: list, session_date: date = None) -> WorkoutSession:
    """Create a WorkoutSession with one Exercise per duration value."""
    if session_date is None:
        session_date = date.today()
    s = WorkoutSession(user_id=1, session_date=session_date)
    for d in durations:
        s.add_exercise(Exercise(name="exercise", duration_minutes=d))
    return s


# ---------------------------------------------------------------------------
# Test 1: CalorieCalculator.calculate_daily_intake()
# ---------------------------------------------------------------------------

class TestCalorieCalculatorDailyIntake:
    """
    Purpose: Verify the calculator returns the correct total calories when
    provided with a list of meal entries for a given day.
    """

    @pytest.fixture
    def calc(self):
        return CalorieCalculator()

    def test_1_1_normal_day_three_meals(self, calc):
        """
        Test Case 1.1 — Normal Day:
        Three meals with known calories should sum to their total.
        """
        today = date.today()
        meals = [
            _make_meal(1, [500], today),
            _make_meal(1, [300], today),
            _make_meal(1, [450], today),
        ]
        result = calc.calculate_daily_intake(meals, today)
        assert result == 1250.0

    def test_1_2_empty_meal_list_returns_zero(self, calc):
        """
        Test Case 1.2 — Empty meal list:
        No entries for the day should return 0.0 without error.
        """
        result = calc.calculate_daily_intake([], date.today())
        assert result == 0.0

    def test_1_3_single_meal_entry(self, calc):
        """
        Test Case 1.3 — Single entry:
        A single meal should return exactly its calorie count.
        """
        today = date.today()
        meals = [_make_meal(1, [750], today)]
        result = calc.calculate_daily_intake(meals, today)
        assert result == 750.0

    def test_1_4_decimal_calorie_values(self, calc):
        """
        Test Case 1.4 — Calorie values containing decimals:
        Non-integer calorie values should sum correctly as floats.
        Input: 33.3 + 33.3 + 33.4 = 100.0
        """
        today = date.today()
        meals = [_make_meal(1, [33.3, 33.3, 33.4], today)]
        result = calc.calculate_daily_intake(meals, today)
        assert result == 100.0


# ---------------------------------------------------------------------------
# Test 2: ProgressAnalyser.compare_weight_change()
# ---------------------------------------------------------------------------

class TestProgressAnalyserCompareWeightChange:
    """
    Purpose: Verify the analyser correctly calculates the difference between
    two body weight measurements and categorises the direction of change.
    """

    @pytest.fixture
    def analyser(self):
        return ProgressAnalyser()

    def test_2_1_weight_loss(self, analyser):
        """
        Test Case 2.1 — Weight loss:
        90.0 kg → 87.5 kg should give delta = -2.5, direction = 'decrease'.
        """
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        measurements = [
            _make_weight(1, 90.0, date(2024, 1, 1)),
            _make_weight(1, 87.5, date(2024, 1, 31)),
        ]
        result = analyser.compare_weight_change(measurements, start, end)
        assert result["delta"] == -2.5
        assert result["direction"] == "decrease"

    def test_2_2_weight_gain(self, analyser):
        """
        Test Case 2.2 — Weight gain:
        75.0 kg → 76.2 kg should give delta = +1.2, direction = 'increase'.
        """
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        measurements = [
            _make_weight(1, 75.0, date(2024, 1, 1)),
            _make_weight(1, 76.2, date(2024, 1, 31)),
        ]
        result = analyser.compare_weight_change(measurements, start, end)
        assert result["delta"] == 1.2
        assert result["direction"] == "increase"

    def test_2_3_no_change(self, analyser):
        """
        Test Case 2.3 — No change:
        Identical measurements should give delta = 0.0, direction = 'unchanged'.
        """
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        measurements = [
            _make_weight(1, 80.0, date(2024, 1, 1)),
            _make_weight(1, 80.0, date(2024, 1, 31)),
        ]
        result = analyser.compare_weight_change(measurements, start, end)
        assert result["delta"] == 0.0
        assert result["direction"] == "unchanged"

    def test_2_4_same_date_raises_value_error(self, analyser):
        """
        Test Case 2.4 — Same date entries:
        Two measurements on the same date should raise a ValueError.
        """
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        measurements = [
            _make_weight(1, 80.0, date(2024, 1, 15)),
            _make_weight(1, 82.0, date(2024, 1, 15)),
        ]
        with pytest.raises(ValueError):
            analyser.compare_weight_change(measurements, start, end)


# ---------------------------------------------------------------------------
# Test 3: WorkoutSession.total_duration()
# ---------------------------------------------------------------------------

class TestWorkoutSessionTotalDuration:
    """
    Purpose: Verify the method returns the correct total duration (minutes)
    across sessions within a specified date range.
    """

    def test_3_1_multiple_sessions(self):
        """
        Test Case 3.1 — Multiple sessions:
        Three sessions of 30, 45, and 60 minutes should total 135 minutes.
        """
        sessions = [
            _make_session([30]),
            _make_session([45]),
            _make_session([60]),
        ]
        ws = WorkoutSession(user_id=1, session_date=date.today())
        assert ws.total_duration(sessions=sessions) == 135

    def test_3_2_no_sessions_in_range_returns_zero(self):
        """
        Test Case 3.2 — No sessions in range:
        An empty session list (no records in the date range) should return 0.
        """
        sessions_in_range = []   # simulates date-filtered query with no results
        ws = WorkoutSession(user_id=1, session_date=date.today())
        assert ws.total_duration(sessions=sessions_in_range) == 0

    def test_3_3_single_session_returns_its_duration(self):
        """
        Test Case 3.3 — Single session:
        A single 45-minute session should return exactly 45.
        """
        sessions = [_make_session([45])]
        ws = WorkoutSession(user_id=1, session_date=date.today())
        assert ws.total_duration(sessions=sessions) == 45


# ---------------------------------------------------------------------------
# Test 4: FitnessGoal entity
# ---------------------------------------------------------------------------

class TestFitnessGoalEntity:
    """
    Purpose: Verify FitnessGoal domain entity methods behave correctly.
    """

    def _make_goal(self, **kwargs):
        defaults = dict(
            user_id=1,
            description="Run 5km",
            target_value=5.0,
            unit="km",
            deadline=date.today() + timedelta(days=30),
        )
        defaults.update(kwargs)
        return FitnessGoal(**defaults)

    def test_4_1_invalid_status_raises_value_error(self):
        """Invalid status in constructor must raise ValueError."""
        with pytest.raises(ValueError):
            self._make_goal(status="invalid_status")

    def test_4_2_progress_pct_partial(self):
        """50% current value of target should return 50.0."""
        g = self._make_goal(current_value=2.5, target_value=5.0)
        assert g.progress_pct() == 50.0

    def test_4_3_progress_pct_zero_target(self):
        """Zero target value returns 0.0 to avoid division by zero."""
        g = self._make_goal(current_value=0.0, target_value=0.0)
        assert g.progress_pct() == 0.0

    def test_4_4_is_achieved_true(self):
        """current_value == target_value means goal is achieved."""
        g = self._make_goal(current_value=5.0, target_value=5.0)
        assert g.is_achieved() is True

    def test_4_5_is_achieved_false(self):
        """current_value below target means goal is not yet achieved."""
        g = self._make_goal(current_value=3.0, target_value=5.0)
        assert g.is_achieved() is False

    def test_4_6_update_status_sets_achieved(self):
        """update_status should set status to 'achieved' when goal is met."""
        g = self._make_goal(current_value=5.0, target_value=5.0)
        g.update_status()
        assert g.status == "achieved"

    def test_4_7_update_status_sets_missed_past_deadline(self):
        """update_status should set status to 'missed' when past deadline without achieving."""
        g = self._make_goal(current_value=1.0, target_value=5.0, deadline=date(2000, 1, 1))
        g.update_status()
        assert g.status == "missed"

    def test_4_8_days_remaining_future(self):
        """Goal 10 days away should return 10."""
        g = self._make_goal(deadline=date.today() + timedelta(days=10))
        assert g.days_remaining() == 10

    def test_4_9_days_remaining_past_returns_zero(self):
        """Overdue goal should return 0 (not negative)."""
        g = self._make_goal(deadline=date(2000, 1, 1))
        assert g.days_remaining() == 0

    def test_4_10_complete_sets_achieved_and_fills_value(self):
        """complete() should set status='achieved' and current_value=target_value."""
        g = self._make_goal(current_value=2.0, target_value=5.0)
        g.complete()
        assert g.status == "achieved"
        assert g.current_value == 5.0


# ---------------------------------------------------------------------------
# Test 5: CalorieCalculator — get_target_calories / compare_intake_to_target
# ---------------------------------------------------------------------------

class TestCalorieCalculatorTargets:
    """
    Purpose: Verify calorie target lookups and intake comparison.
    """

    @pytest.fixture
    def calc(self):
        return CalorieCalculator()

    def _make_user(self, dob: date, level: str = "beginner") -> User:
        return User(
            email="t@t.com",
            first_name="Test",
            last_name="User",
            date_of_birth=dob,
            fitness_level=level,
        )

    def test_5_1_target_calories_beginner_maintain_under_30(self, calc):
        """Young beginner on maintain goal gets 2200 kcal base."""
        user = self._make_user(date(2000, 1, 1))   # ~24 years old
        assert calc.get_target_calories(user, "maintain") == 2200.0

    def test_5_2_target_calories_beginner_maintain_over_30(self, calc):
        """Beginner aged 31-50 gets 100 kcal deducted from base."""
        user = self._make_user(date(1990, 1, 1))   # ~34 years old
        assert calc.get_target_calories(user, "maintain") == 2100.0

    def test_5_3_target_calories_beginner_maintain_over_50(self, calc):
        """Beginner aged 51+ gets 200 kcal deducted from base."""
        user = self._make_user(date(1970, 1, 1))   # ~54 years old
        assert calc.get_target_calories(user, "maintain") == 2000.0

    def test_5_4_target_calories_advanced_gain_muscle(self, calc):
        """Advanced user on gain_muscle gets 3000 kcal base."""
        user = self._make_user(date(2000, 1, 1), level="advanced")
        assert calc.get_target_calories(user, "gain_muscle") == 3000.0

    def test_5_5_target_calories_unknown_level_uses_fallback(self, calc):
        """Unknown fitness level falls back to 2200 kcal."""
        user = self._make_user(date(2000, 1, 1), level="elite")
        assert calc.get_target_calories(user, "maintain") == 2200.0

    def test_5_6_compare_intake_over_target(self, calc):
        """Eating 500 kcal over the 2200 target returns +500."""
        today = date.today()
        user = self._make_user(date(2000, 1, 1), level="beginner")
        meals = [_make_meal(1, [2700], today)]
        diff = calc.compare_intake_to_target(meals, user, today, "maintain")
        assert diff == 500.0

    def test_5_7_compare_intake_under_target(self, calc):
        """Eating 700 kcal under the 2200 target returns -700."""
        today = date.today()
        user = self._make_user(date(2000, 1, 1), level="beginner")
        meals = [_make_meal(1, [1500], today)]
        diff = calc.compare_intake_to_target(meals, user, today, "maintain")
        assert diff == -700.0


# ---------------------------------------------------------------------------
# Test 6: Notification entity — mark_sent / mark_failed
# ---------------------------------------------------------------------------

class TestNotificationEntity:
    """
    Purpose: Verify Notification domain entity state transitions.
    """

    def test_6_1_mark_sent_sets_status_and_timestamp(self):
        """mark_sent() sets status='sent' and records sent_at."""
        n = Notification(user_id=1, message="Reminder")
        n.mark_sent()
        assert n.status == "sent"
        assert n.sent_at is not None

    def test_6_2_mark_failed_sets_status(self):
        """mark_failed() sets status='failed'."""
        n = Notification(user_id=1, message="Reminder")
        n.mark_failed()
        assert n.status == "failed"

    def test_6_3_badge_post_init_sets_today_when_no_date(self):
        """Badge.__post_init__ defaults date_awarded to today."""
        b = Badge(user_id=1, name="Test", description="Desc", condition="first_workout")
        assert b.date_awarded == date.today()

    def test_6_4_badge_explicit_date_preserved(self):
        """Badge.__post_init__ does not override an explicit date_awarded."""
        explicit = date(2020, 6, 15)
        b = Badge(user_id=1, name="Test", description="Desc", condition="first_workout",
                  date_awarded=explicit)
        assert b.date_awarded == explicit


# ---------------------------------------------------------------------------
# Test 7: User entity
# ---------------------------------------------------------------------------

class TestUserEntity:
    """
    Purpose: Verify User entity helper methods.
    """

    def _make_user(self, dob: date = date(1990, 1, 1), role: str = "user") -> User:
        return User(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            date_of_birth=dob,
            role=role,
        )

    def test_7_1_set_and_check_password_correct(self):
        """set_password hashes password; check_password verifies it."""
        u = self._make_user()
        u.set_password("mysecret")
        assert u.check_password("mysecret") is True

    def test_7_2_check_password_wrong_returns_false(self):
        """check_password returns False for wrong password."""
        u = self._make_user()
        u.set_password("mysecret")
        assert u.check_password("wrongpass") is False

    def test_7_3_check_password_no_hash_returns_false(self):
        """check_password returns False when no password hash set."""
        u = self._make_user()
        assert u.check_password("anything") is False

    def test_7_4_full_name(self):
        """full_name returns concatenated first + last."""
        u = self._make_user()
        assert u.full_name() == "John Doe"

    def test_7_5_is_coach_false_for_user(self):
        """Regular user is not a coach."""
        u = self._make_user()
        assert u.is_coach() is False

    def test_7_6_is_coach_true_for_coach(self):
        """Coach role returns True from is_coach()."""
        u = self._make_user(role="coach")
        assert u.is_coach() is True

    def test_7_7_age_calculation(self):
        """age() returns correct integer age."""
        dob = date.today().replace(year=date.today().year - 30)
        u = User(email="a@a.com", first_name="A", last_name="B", date_of_birth=dob)
        assert u.age() == 30


# ---------------------------------------------------------------------------
# Test 8: BadgeChecker service
# ---------------------------------------------------------------------------

class TestBadgeCheckerService:
    """
    Purpose: Verify badge checker detects streak and goal completion.
    """

    def _make_session(self, session_date: date) -> WorkoutSession:
        s = WorkoutSession(user_id=1, session_date=session_date)
        s.add_exercise(Exercise(name="Run", duration_minutes=30))
        return s

    def test_8_1_seven_day_streak_earns_badge(self):
        """Seven consecutive days of workouts earns the 7_day_streak badge."""
        today = date.today()
        sessions = [self._make_session(today - timedelta(days=i)) for i in range(7)]
        checker = BadgeChecker()
        earned = checker.check_all(
            user_id=1, sessions=sessions, meals=[], goals=[], existing_badges=[]
        )
        conditions = {b.condition for b in earned}
        assert "7_day_streak" in conditions

    def test_8_2_less_than_seven_days_no_streak_badge(self):
        """Six consecutive days should NOT earn the 7_day_streak badge."""
        today = date.today()
        sessions = [self._make_session(today - timedelta(days=i)) for i in range(6)]
        checker = BadgeChecker()
        earned = checker.check_all(
            user_id=1, sessions=sessions, meals=[], goals=[], existing_badges=[]
        )
        conditions = {b.condition for b in earned}
        assert "7_day_streak" not in conditions

    def test_8_3_completed_first_goal_earns_badge(self):
        """An achieved goal earns the first_goal badge."""
        goal = FitnessGoal(
            user_id=1, description="Run", target_value=5.0, unit="km",
            deadline=date.today(), status="achieved", current_value=5.0,
        )
        checker = BadgeChecker()
        earned = checker.check_all(
            user_id=1, sessions=[], meals=[], goals=[goal], existing_badges=[]
        )
        conditions = {b.condition for b in earned}
        assert "first_goal" in conditions

    def test_8_4_existing_badge_not_duplicated(self):
        """Already-earned badges are not returned again."""
        existing = Badge(
            user_id=1, name="Early Bird", description="Desc",
            condition="first_workout",
        )
        session = self._make_session(date.today())
        checker = BadgeChecker()
        earned = checker.check_all(
            user_id=1, sessions=[session], meals=[], goals=[], existing_badges=[existing]
        )
        conditions = {b.condition for b in earned}
        assert "first_workout" not in conditions


# ---------------------------------------------------------------------------
# Test 9: EmailNotificationAdapter
# ---------------------------------------------------------------------------

class TestEmailNotificationAdapter:
    """
    Purpose: Verify the email adapter marks notifications correctly and
    handles SMTP failures gracefully.
    """

    def _make_adapter(self):
        from adapters.notifications.email_adapter import EmailNotificationAdapter
        return EmailNotificationAdapter("smtp.test.com", 587, "user@test.com", "pass")

    def test_9_1_send_success_marks_sent(self):
        """Successful SMTP send marks notification as 'sent'."""
        adapter = self._make_adapter()
        notif = Notification(user_id=1, message="Workout time!")

        mock_server = MagicMock()
        with patch("adapters.notifications.email_adapter.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = adapter.send(notif, "user@example.com")

        assert result is True
        assert notif.status == "sent"
        assert notif.sent_at is not None

    def test_9_2_send_smtp_failure_marks_failed(self):
        """SMTP failure causes notification to be marked 'failed'; returns False."""
        adapter = self._make_adapter()
        notif = Notification(user_id=1, message="Workout time!")

        with patch(
            "adapters.notifications.email_adapter.smtplib.SMTP",
            side_effect=smtplib.SMTPException("Connection refused"),
        ):
            result = adapter.send(notif, "user@example.com")

        assert result is False
        assert notif.status == "failed"
