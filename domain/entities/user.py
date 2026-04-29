from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import bcrypt


@dataclass
class User:
    email: str
    first_name: str
    last_name: str
    date_of_birth: date
    role: str = "user"   # "user" or "coach"
    id: Optional[int] = None
    hashed_password: Optional[str] = None
    height_cm: Optional[float] = None
    fitness_level: Optional[str] = None  # beginner / intermediate / advanced

    def set_password(self, raw: str) -> None:
        salt = bcrypt.gensalt()
        self.hashed_password = bcrypt.hashpw(raw.encode(), salt).decode()

    def check_password(self, raw: str) -> bool:
        if not self.hashed_password:
            return False
        return bcrypt.checkpw(raw.encode(), self.hashed_password.encode())

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def is_coach(self) -> bool:
        return self.role == "coach"

    def age(self) -> int:
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
