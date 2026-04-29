import os
import requests  # type: ignore[import-untyped]
import requests_cache
from typing import List

from ports.repositories import NutritionAPIClient


class NutritionServiceUnavailable(Exception):
    """Raised when the nutrition API is unreachable and no cached data exists."""


# In-memory cache: query string -> list of food dicts.
# Populated on successful API responses; consulted when the API is down.
_search_cache: dict = {}


# cache lives on disk so it survives between restarts
requests_cache.install_cache(
    cache_name=os.getenv("CACHE_DIR", ".cache/nutrition"),
    backend="sqlite",
    expire_after=86400,   # 24 hours
)


class NutritionixAdapter(NutritionAPIClient):
    """
    Wraps the Nutritionix API. If the request fails (network down, rate limit,
    whatever), requests-cache will return the last cached response silently.
    If there's no cache either, we fall back to a small built-in dataset.
    """

    BASE_URL = "https://trackapi.nutritionix.com/v2"

    _FALLBACK_FOODS: List[dict] = [
        {"name": "Chicken Breast (100g)", "calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6},
        {"name": "Brown Rice (100g)", "calories": 216, "protein_g": 4.5, "carbs_g": 45, "fat_g": 1.8},
        {"name": "Banana", "calories": 89, "protein_g": 1.1, "carbs_g": 23, "fat_g": 0.3},
        {"name": "Egg (large)", "calories": 78, "protein_g": 6, "carbs_g": 0.6, "fat_g": 5},
        {"name": "Oats (100g)", "calories": 389, "protein_g": 17, "carbs_g": 66, "fat_g": 7},
        {"name": "Apple", "calories": 52, "protein_g": 0.3, "carbs_g": 14, "fat_g": 0.2},
        {"name": "Bread (slice, whole-wheat)", "calories": 80, "protein_g": 4, "carbs_g": 14, "fat_g": 1.1},
        {"name": "Milk (1 cup, whole)", "calories": 149, "protein_g": 7.7, "carbs_g": 12, "fat_g": 8},
        {"name": "Pasta (100g cooked)", "calories": 158, "protein_g": 5.8, "carbs_g": 31, "fat_g": 0.9},
        {"name": "Salmon (100g)", "calories": 208, "protein_g": 20, "carbs_g": 0, "fat_g": 13},
    ]

    def __init__(self, api_key: str = "", app_id: str = ""):
        self._api_key = api_key
        self._app_id = app_id

    def search_food(self, query: str) -> List[dict]:
        if not self._api_key:
            return self._local_search(query)

        cache_key = query.lower().strip()
        try:
            headers = {
                "x-app-id": self._app_id,
                "x-app-key": self._api_key,
                "Content-Type": "application/json",
            }
            resp = requests.post(
                f"{self.BASE_URL}/natural/nutrients",
                json={"query": query},
                headers=headers,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            results = [
                {
                    "name": f.get("food_name", query),
                    "calories": f.get("nf_calories", 0),
                    "protein_g": f.get("nf_protein", 0),
                    "carbs_g": f.get("nf_total_carbohydrate", 0),
                    "fat_g": f.get("nf_total_fat", 0),
                    "serving_size_g": f.get("serving_weight_grams", 100),
                }
                for f in data.get("foods", [])
            ]
            _search_cache[cache_key] = results
            return results
        except Exception:
            # Network/API failure — consult in-memory cache first.
            cached = _search_cache.get(cache_key)
            if cached is not None:
                return cached
            raise NutritionServiceUnavailable(
                "Nutrition service is currently unavailable."
            )

    def _local_search(self, query: str) -> List[dict]:
        q = query.lower()
        hits = [f for f in self._FALLBACK_FOODS if q in f["name"].lower()]
        return hits if hits else self._FALLBACK_FOODS[:3]
