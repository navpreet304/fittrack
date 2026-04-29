"""
Integration Tests — FitTrack
=============================
Test 4: POST /workouts
Test 5: GET /users/{id}/progress
Test 6: Nutrition API Fallback Cache
"""

import os
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from adapters.api.app import create_app
from adapters.db.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import adapters.nutrition.nutritionix_adapter as nutrition_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    application = create_app()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    application.config["SessionLocal"] = TestSession

    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Register and log in a regular test user; return (headers, user_id)."""
    client.post("/auth/register", json={
        "email": "integration_user@test.com",
        "password": "testpass123",
        "first_name": "Integration",
        "last_name": "User",
        "date_of_birth": "1990-05-15",
        "fitness_level": "intermediate",
    })
    resp = client.post("/auth/login", json={
        "email": "integration_user@test.com",
        "password": "testpass123",
    })
    token = resp.get_json()["access_token"]
    user_id = resp.get_json()["user_id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def coach_headers(client):
    """Register and log in a coach user; return (headers, coach_id)."""
    client.post("/auth/register", json={
        "email": "integration_coach@test.com",
        "password": "coachpass123",
        "first_name": "Integration",
        "last_name": "Coach",
        "date_of_birth": "1980-01-01",
        "role": "coach",
        "fitness_level": "advanced",
    })
    resp = client.post("/auth/login", json={
        "email": "integration_coach@test.com",
        "password": "coachpass123",
    })
    token = resp.get_json()["access_token"]
    coach_id = resp.get_json()["user_id"]
    return {"Authorization": f"Bearer {token}"}, coach_id


# ---------------------------------------------------------------------------
# Test 4: POST /workouts
# ---------------------------------------------------------------------------

class TestPostWorkouts:
    """
    Purpose: Verify the POST /workouts endpoint correctly handles workout
    submissions from authenticated users.
    """

    def test_4_1_valid_workout_returns_201_with_id_and_date(self, client, auth_headers):
        """
        Test Case 4.1 — Valid:
        An authorised user submits a full workout JSON.
        Expected: HTTP 201; response contains a session ID and session_date.
        """
        headers, _ = auth_headers
        resp = client.post("/workouts", headers=headers, json={
            "session_date": date.today().isoformat(),
            "exercises": [
                {"name": "Push-ups", "duration_minutes": 20, "sets": 3, "reps": 15},
                {"name": "Running",  "duration_minutes": 30},
            ],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert "session_date" in data
        assert data["total_duration_minutes"] == 50

    def test_4_2_missing_exercise_field_returns_400(self, client, auth_headers):
        """
        Test Case 4.2 — Missing field:
        Payload is missing the exercise name (type).
        Expected: HTTP 400 Bad Request.
        """
        headers, _ = auth_headers
        resp = client.post("/workouts", headers=headers, json={
            "session_date": date.today().isoformat(),
            "exercises": [
                {"duration_minutes": 30},   # 'name' is absent
            ],
        })
        assert resp.status_code == 400

    def test_4_3_unauthenticated_request_returns_401(self, client):
        """
        Test Case 4.3 — Unauthenticated:
        No JWT provided in the header.
        Expected: HTTP 401 Unauthorized.
        """
        resp = client.post("/workouts", json={
            "session_date": date.today().isoformat(),
            "exercises": [{"name": "Cycling", "duration_minutes": 40}],
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 5: GET /users/{id}/progress
# ---------------------------------------------------------------------------

class TestGetUserProgress:
    """
    Purpose: Verify the GET /users/{id}/progress endpoint returns the correct
    data for authorised callers and enforces access control.
    """

    def test_5_1_coach_can_view_client_progress(self, client, coach_headers, auth_headers):
        """
        Test Case 5.1 — Coach and Own Client:
        A valid coach token accessing an existing client ID.
        Expected: HTTP 200; response includes workout count, calories, and
        weight trend fields.
        """
        coach_hdrs, _ = coach_headers
        _, client_id = auth_headers
        resp = client.get(f"/users/{client_id}/progress", headers=coach_hdrs)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "workout_frequency" in data     # number of workouts
        assert "weight_change_kg" in data      # weight trend
        assert "weekly_stats" in data          # contains avg_calories per week

    def test_5_2_nonexistent_client_returns_404(self, client, coach_headers):
        """
        Test Case 5.2 — Non-existent client:
        Valid coach token but an unknown user ID.
        Expected: HTTP 404 Not Found.
        """
        coach_hdrs, _ = coach_headers
        resp = client.get("/users/999999/progress", headers=coach_hdrs)
        assert resp.status_code == 404

    def test_5_3_regular_user_cannot_view_another_users_progress(self, client, auth_headers, coach_headers):
        """
        Test Case 5.3 — Forbidden access:
        A standard user token attempting to view a different user's progress.
        Expected: HTTP 403 Forbidden.
        """
        headers, user_id = auth_headers
        _, coach_id = coach_headers
        # User tries to access the coach's progress page
        resp = client.get(f"/users/{coach_id}/progress", headers=headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 6: Nutrition API Fallback Cache
# ---------------------------------------------------------------------------

class TestNutritionFallbackCache:
    """
    Purpose: Verify that the nutrition search endpoint correctly handles API
    availability and falls back to an in-memory cache when the API is down.
    """

    def setup_method(self):
        """Clear the module-level nutrition cache before each test."""
        nutrition_module._search_cache.clear()

    def test_6_1_api_available_returns_correct_calories_and_populates_cache(
        self, client, auth_headers
    ):
        """
        Test Case 6.1 — API available:
        Mock nutrition API returns calorie data.
        Expected: 200 with correct calories; a cache entry is saved.
        """
        headers, _ = auth_headers

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "foods": [
                {
                    "food_name": "banana",
                    "nf_calories": 89.0,
                    "nf_protein": 1.1,
                    "nf_total_carbohydrate": 23.0,
                    "nf_total_fat": 0.3,
                    "serving_weight_grams": 100,
                }
            ]
        }

        mock_config = MagicMock()
        mock_config.NUTRITION_API_KEY = "test-api-key"
        mock_config.NUTRITION_APP_ID = "test-app-id"

        with patch("adapters.api.routes_meals.get_config", return_value=mock_config):
            with patch(
                "adapters.nutrition.nutritionix_adapter.requests.post",
                return_value=mock_resp,
            ):
                resp = client.get("/meals/search?q=banana", headers=headers)

        assert resp.status_code == 200
        results = resp.get_json()
        assert len(results) >= 1
        assert results[0]["calories"] == 89.0
        # cache entry must have been saved
        assert "banana" in nutrition_module._search_cache

    def test_6_2_api_unavailable_cache_hit_returns_cached_data(
        self, client, auth_headers
    ):
        """
        Test Case 6.2 — API unavailable, cache hit:
        API mock raises a connection error; cache contains a prior result.
        Expected: 200 returned using the cached calorie value; no error raised.
        """
        headers, _ = auth_headers

        # Pre-populate the cache as if a prior successful call had stored it
        nutrition_module._search_cache["chicken"] = [
            {
                "name": "Chicken Breast",
                "calories": 165,
                "protein_g": 31,
                "carbs_g": 0,
                "fat_g": 3.6,
            }
        ]

        mock_config = MagicMock()
        mock_config.NUTRITION_API_KEY = "test-api-key"
        mock_config.NUTRITION_APP_ID = "test-app-id"

        with patch("adapters.api.routes_meals.get_config", return_value=mock_config):
            with patch(
                "adapters.nutrition.nutritionix_adapter.requests.post",
                side_effect=ConnectionError("API is down"),
            ):
                resp = client.get("/meals/search?q=chicken", headers=headers)

        assert resp.status_code == 200
        results = resp.get_json()
        assert results[0]["calories"] == 165

    def test_6_3_api_unavailable_no_cache_returns_503(self, client, auth_headers):
        """
        Test Case 6.3 — API unavailable, no cache:
        API mock throws a connection error; no entry exists in the cache.
        Expected: HTTP 503; body contains a message about the service being
        unavailable.
        """
        headers, _ = auth_headers
        # cache is cleared in setup_method — no cached data for this query

        mock_config = MagicMock()
        mock_config.NUTRITION_API_KEY = "test-api-key"
        mock_config.NUTRITION_APP_ID = "test-app-id"

        with patch("adapters.api.routes_meals.get_config", return_value=mock_config):
            with patch(
                "adapters.nutrition.nutritionix_adapter.requests.post",
                side_effect=ConnectionError("API is down"),
            ):
                resp = client.get("/meals/search?q=unknownfood99999", headers=headers)

        assert resp.status_code == 503
        data = resp.get_json()
        assert "unavailable" in data["error"].lower()


# ---------------------------------------------------------------------------
# Test 7: Auth + root routes
# ---------------------------------------------------------------------------

class TestAuthAndRootRoutes:
    """
    Purpose: Verify auth registration/login endpoints and the root API hub page.
    """

    def test_7_1_register_creates_user(self, client):
        resp = client.post("/auth/register", json={
            "email": "newreg@example.com",
            "password": "pass123",
            "first_name": "New",
            "last_name": "Reg",
            "date_of_birth": "1995-06-01",
        })
        assert resp.status_code == 201
        assert "id" in resp.get_json()

    def test_7_2_duplicate_email_returns_409(self, client):
        payload = {
            "email": "dup7@example.com",
            "password": "pass",
            "first_name": "A",
            "last_name": "B",
            "date_of_birth": "1990-01-01",
        }
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409

    def test_7_3_login_returns_access_token(self, client):
        client.post("/auth/register", json={
            "email": "login7@example.com",
            "password": "pw",
            "first_name": "L",
            "last_name": "U",
            "date_of_birth": "1990-01-01",
        })
        resp = client.post("/auth/login", json={
            "email": "login7@example.com",
            "password": "pw",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_7_4_wrong_password_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "email": "login7@example.com",
            "password": "badpassword",
        })
        assert resp.status_code == 401

    def test_7_5_root_returns_api_hub_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"FitTrack" in resp.data

    def test_7_6_unauthenticated_workout_post_returns_401(self, client):
        resp = client.post("/workouts", json={
            "session_date": "2024-01-01",
            "exercises": [{"name": "run", "duration_minutes": 20}],
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 8: GET /workouts, POST /workouts validation
# ---------------------------------------------------------------------------

class TestWorkoutRoutes:
    """
    Purpose: Verify additional workout route edge cases.
    """

    def test_8_1_post_workout_invalid_date_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/workouts", headers=headers, json={
            "session_date": "not-a-date",
            "exercises": [{"name": "run", "duration_minutes": 20}],
        })
        assert resp.status_code == 400

    def test_8_2_post_workout_missing_exercises_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/workouts", headers=headers, json={
            "session_date": "2024-01-01",
        })
        assert resp.status_code == 400

    def test_8_3_get_workouts_returns_list(self, client, auth_headers):
        headers, _ = auth_headers
        # Post one workout first
        client.post("/workouts", headers=headers, json={
            "session_date": date.today().isoformat(),
            "exercises": [{"name": "Cycling", "duration_minutes": 25}],
        })
        resp = client.get("/workouts", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)
        assert len(resp.get_json()) >= 1


# ---------------------------------------------------------------------------
# Test 9: GET /goals, POST /goals, PATCH /goals/<id>/complete
# ---------------------------------------------------------------------------

class TestGoalsTopLevelRoutes:
    """
    Purpose: Verify /goals top-level endpoints.
    """

    def test_9_1_get_goals_returns_list(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/goals", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_9_2_post_goal_valid_returns_201(self, client, auth_headers):
        headers, _ = auth_headers
        from datetime import timedelta
        future = (date.today() + timedelta(days=30)).isoformat()
        resp = client.post("/goals", headers=headers, json={
            "description": "Run 5km",
            "target_value": 5.0,
            "unit": "km",
            "deadline": future,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["status"] == "active"
        assert data["description"] == "Run 5km"

    def test_9_3_post_goal_missing_fields_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/goals", headers=headers, json={
            "description": "Partial",
            "target_value": 5.0,
        })
        assert resp.status_code == 400

    def test_9_4_post_goal_invalid_deadline_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/goals", headers=headers, json={
            "description": "Run",
            "target_value": 5.0,
            "unit": "km",
            "deadline": "not-a-date",
        })
        assert resp.status_code == 400

    def test_9_5_patch_goal_complete_returns_200_achieved(self, client, auth_headers):
        headers, _ = auth_headers
        from datetime import timedelta
        future = (date.today() + timedelta(days=30)).isoformat()
        create_resp = client.post("/goals", headers=headers, json={
            "description": "Complete me",
            "target_value": 10.0,
            "unit": "reps",
            "deadline": future,
        })
        goal_id = create_resp.get_json()["id"]
        resp = client.patch(f"/goals/{goal_id}/complete", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "achieved"

    def test_9_6_patch_goal_not_found_returns_404(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.patch("/goals/999999/complete", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 10: GET /measurements, POST /measurements, GET /measurements/latest
# ---------------------------------------------------------------------------

class TestMeasurementTopLevelRoutes:
    """
    Purpose: Verify /measurements top-level endpoints.
    """

    def test_10_1_get_measurements_returns_list(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/measurements", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_10_2_post_measurement_valid_returns_201(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/measurements", headers=headers, json={
            "measurement_type": "weight_kg",
            "value": 75.0,
            "unit": "kg",
            "recorded_date": date.today().isoformat(),
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["value"] == 75.0
        assert data["measurement_type"] == "weight_kg"

    def test_10_3_post_measurement_missing_field_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/measurements", headers=headers, json={
            "measurement_type": "weight_kg",
            "value": 75.0,
            # missing unit and recorded_date
        })
        assert resp.status_code == 400

    def test_10_4_get_measurements_latest_returns_200(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/measurements/latest", headers=headers)
        assert resp.status_code == 200

    def test_10_5_post_measurement_invalid_date_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/measurements", headers=headers, json={
            "measurement_type": "weight_kg",
            "value": 75.0,
            "unit": "kg",
            "recorded_date": "bad-date",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 11: POST /notifications, GET /notifications, GET /notifications/due,
#          PATCH /notifications/<id>/deliver
# ---------------------------------------------------------------------------

class TestNotificationTopLevelRoutes:
    """
    Purpose: Verify /notifications top-level endpoints.
    """

    def test_11_1_post_notification_valid_returns_201(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/notifications", headers=headers, json={
            "message": "Workout reminder",
            "channel": "email",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "pending"
        assert data["message"] == "Workout reminder"
        assert "id" in data

    def test_11_2_post_notification_missing_message_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/notifications", headers=headers, json={"channel": "email"})
        assert resp.status_code == 400

    def test_11_3_post_notification_invalid_scheduled_at_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/notifications", headers=headers, json={
            "message": "Test",
            "scheduled_at": "not-a-datetime",
        })
        assert resp.status_code == 400

    def test_11_4_post_notification_with_valid_scheduled_at(self, client, auth_headers):
        from datetime import datetime, timedelta
        headers, _ = auth_headers
        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        resp = client.post("/notifications", headers=headers, json={
            "message": "Future reminder",
            "scheduled_at": future,
        })
        assert resp.status_code == 201
        assert resp.get_json()["scheduled_at"] is not None

    def test_11_5_get_notifications_list_returns_200(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/notifications", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_11_6_get_due_notifications_returns_list(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/notifications/due", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_11_7_due_notification_appears_in_due_list(self, client, auth_headers):
        """A past-due notification should appear in /notifications/due."""
        from datetime import datetime, timedelta
        headers, _ = auth_headers
        past = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        create_resp = client.post("/notifications", headers=headers, json={
            "message": "Overdue reminder",
            "scheduled_at": past,
        })
        assert create_resp.status_code == 201
        due_resp = client.get("/notifications/due", headers=headers)
        due_ids = [n["id"] for n in due_resp.get_json()]
        assert create_resp.get_json()["id"] in due_ids

    def test_11_8_deliver_notification_returns_delivered(self, client, auth_headers):
        from datetime import datetime, timedelta
        headers, _ = auth_headers
        past = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
        create_resp = client.post("/notifications", headers=headers, json={
            "message": "Deliver me",
            "scheduled_at": past,
        })
        notif_id = create_resp.get_json()["id"]
        resp = client.patch(f"/notifications/{notif_id}/deliver", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "delivered"

    def test_11_9_deliver_nonexistent_returns_404(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.patch("/notifications/999999/deliver", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 12: POST /users/<id>/measurements, GET /users/<id>/badges,
#          POST /users/<id>/goals  (progress blueprint sub-routes)
# ---------------------------------------------------------------------------

class TestProgressSubRoutes:
    """
    Purpose: Verify user-scoped sub-routes on the /users blueprint.
    """

    def test_12_1_add_measurement_own_user_returns_201(self, client, auth_headers):
        headers, user_id = auth_headers
        resp = client.post(f"/users/{user_id}/measurements", headers=headers, json={
            "measurement_type": "weight_kg",
            "value": 80.0,
            "unit": "kg",
            "recorded_date": date.today().isoformat(),
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["value"] == 80.0

    def test_12_2_add_measurement_forbidden_for_other_user(self, client, auth_headers, coach_headers):
        user_hdrs, _ = auth_headers
        _, coach_id = coach_headers
        resp = client.post(f"/users/{coach_id}/measurements", headers=user_hdrs, json={
            "measurement_type": "weight_kg",
            "value": 80.0,
            "unit": "kg",
            "recorded_date": date.today().isoformat(),
        })
        assert resp.status_code == 403

    def test_12_3_get_badges_own_user_returns_200(self, client, auth_headers):
        headers, user_id = auth_headers
        resp = client.get(f"/users/{user_id}/badges", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_12_4_get_badges_forbidden_for_other_user(self, client, auth_headers, coach_headers):
        user_hdrs, _ = auth_headers
        _, coach_id = coach_headers
        resp = client.get(f"/users/{coach_id}/badges", headers=user_hdrs)
        assert resp.status_code == 403

    def test_12_5_add_goal_via_progress_route_returns_201(self, client, auth_headers):
        from datetime import timedelta
        headers, user_id = auth_headers
        resp = client.post(f"/users/{user_id}/goals", headers=headers, json={
            "description": "Lose weight",
            "target_value": 70.0,
            "unit": "kg",
            "deadline": (date.today() + timedelta(days=60)).isoformat(),
        })
        assert resp.status_code == 201
        assert "id" in resp.get_json()

    def test_12_6_add_goal_forbidden_for_other_user(self, client, auth_headers, coach_headers):
        from datetime import timedelta
        user_hdrs, _ = auth_headers
        _, coach_id = coach_headers
        resp = client.post(f"/users/{coach_id}/goals", headers=user_hdrs, json={
            "description": "Hack",
            "target_value": 1.0,
            "unit": "kg",
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
        })
        assert resp.status_code == 403

    def test_12_7_get_progress_with_date_params_returns_200(self, client, auth_headers, coach_headers):
        from datetime import timedelta
        coach_hdrs, _ = coach_headers
        _, client_id = auth_headers
        start = (date.today() - timedelta(days=7)).isoformat()
        end = date.today().isoformat()
        resp = client.get(
            f"/users/{client_id}/progress?start={start}&end={end}",
            headers=coach_hdrs,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 13: POST /meals, POST /meals/sync
# ---------------------------------------------------------------------------

class TestMealRoutes:
    """
    Purpose: Verify meal logging and offline sync endpoints.
    """

    def test_13_1_log_meal_valid_returns_201(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/meals", headers=headers, json={
            "meal_name": "Breakfast",
            "food_items": [
                {"name": "Oats", "calories": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5},
            ],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["total_calories"] == 300.0
        assert data["food_item_count"] == 1

    def test_13_2_log_meal_missing_food_items_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/meals", headers=headers, json={"meal_name": "Breakfast"})
        assert resp.status_code == 400

    def test_13_3_log_meal_food_item_missing_name_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/meals", headers=headers, json={
            "meal_name": "Lunch",
            "food_items": [{"calories": 200}],
        })
        assert resp.status_code == 400

    def test_13_4_sync_offline_meals_returns_201_with_count(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/meals/sync", headers=headers, json={
            "entries": [
                {
                    "meal_name": "Offline breakfast",
                    "food_items": [{"name": "Apple", "calories": 80}],
                },
                {
                    "meal_name": "Offline snack",
                    "food_items": [{"name": "Banana", "calories": 89}],
                },
            ]
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["synced"] == 2
        assert len(data["ids"]) == 2

    def test_13_5_sync_meals_no_entries_returns_400(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/meals/sync", headers=headers, json={})
        assert resp.status_code == 400

    def test_13_6_get_meals_list_returns_200(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/meals", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)
