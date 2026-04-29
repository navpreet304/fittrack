from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class FoodItem:
    name: str
    calories: float
    serving_size_g: float = 100.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0


@dataclass
class MealEntry:
    user_id: int
    meal_name: str          # breakfast / lunch / dinner / snack
    food_items: List[FoodItem] = field(default_factory=list)
    logged_at: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
    sync_status: str = "synced"   # "synced" or "pending"

    def add_food(self, item: FoodItem) -> None:
        self.food_items.append(item)

    def total_calories(self) -> float:
        return round(sum(f.calories for f in self.food_items), 1)

    def total_protein(self) -> float:
        return round(sum(f.protein_g for f in self.food_items), 1)

    def queue_offline(self) -> None:
        self.sync_status = "pending"

    def mark_synced(self) -> None:
        self.sync_status = "synced"
