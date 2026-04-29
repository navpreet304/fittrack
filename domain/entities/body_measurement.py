from dataclasses import dataclass
from datetime import date
from typing import Optional


MEASUREMENT_TYPES = (
    "weight_kg",
    "body_fat_pct",
    "waist_cm",
    "chest_cm",
    "hips_cm",
    "bicep_cm",
)


@dataclass
class BodyMeasurement:
    user_id: int
    measurement_type: str
    value: float
    unit: str
    recorded_date: date
    id: Optional[int] = None
    notes: str = ""

    def __post_init__(self):
        if self.measurement_type not in MEASUREMENT_TYPES:
            raise ValueError(
                f"Unknown measurement type '{self.measurement_type}'. "
                f"Valid options: {MEASUREMENT_TYPES}"
            )
        if self.value < 0:
            raise ValueError("Measurement value can't be negative.")
