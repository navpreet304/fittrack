from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from adapters.db.pg_repositories import PGMealEntryRepository
from adapters.nutrition.nutritionix_adapter import NutritionixAdapter, NutritionServiceUnavailable
from domain.entities.meal_entry import MealEntry, FoodItem
from config.settings import get_config

meals_bp = Blueprint("meals", __name__)


def _get_repo():
    from adapters.api import get_db
    return PGMealEntryRepository(get_db())


@meals_bp.post("")
@jwt_required()
def log_meal():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided"}), 400
    if "meal_name" not in data or "food_items" not in data:
        return jsonify({"error": "meal_name and food_items are required"}), 400

    meal = MealEntry(
        user_id=user_id,
        meal_name=data["meal_name"],
        sync_status=data.get("sync_status", "synced"),
    )

    for item in data["food_items"]:
        if "name" not in item or "calories" not in item:
            return jsonify({"error": "Each food item needs name and calories"}), 400
        meal.add_food(FoodItem(
            name=item["name"],
            calories=float(item["calories"]),
            serving_size_g=item.get("serving_size_g", 100.0),
            protein_g=item.get("protein_g", 0.0),
            carbs_g=item.get("carbs_g", 0.0),
            fat_g=item.get("fat_g", 0.0),
        ))

    repo = _get_repo()
    saved = repo.save(meal)

    return jsonify({
        "id": saved.id,
        "meal_name": saved.meal_name,
        "total_calories": saved.total_calories(),
        "food_item_count": len(saved.food_items),
        "sync_status": saved.sync_status,
    }), 201


@meals_bp.get("/search")
@jwt_required()
def search_food():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    cfg = get_config()
    adapter = NutritionixAdapter(
        api_key=cfg.NUTRITION_API_KEY,
        app_id=getattr(cfg, "NUTRITION_APP_ID", ""),
    )
    try:
        results = adapter.search_food(query)
    except NutritionServiceUnavailable:
        return jsonify({"error": "Nutrition service is currently unavailable"}), 503
    return jsonify(results), 200


@meals_bp.post("/sync")
@jwt_required()
def sync_offline():
    """
    Accepts a batch of offline-queued meal entries and saves them all.
    Each entry in the list should match the same format as POST /meals.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data or "entries" not in data:
        return jsonify({"error": "entries list is required"}), 400

    repo = _get_repo()
    saved_ids = []

    for entry in data["entries"]:
        meal = MealEntry(
            user_id=user_id,
            meal_name=entry.get("meal_name", "meal"),
            sync_status="synced",
        )
        for item in entry.get("food_items", []):
            meal.add_food(FoodItem(
                name=item["name"],
                calories=float(item["calories"]),
                protein_g=item.get("protein_g", 0.0),
                carbs_g=item.get("carbs_g", 0.0),
                fat_g=item.get("fat_g", 0.0),
            ))
        saved = repo.save(meal)
        saved_ids.append(saved.id)

    return jsonify({"synced": len(saved_ids), "ids": saved_ids}), 201
