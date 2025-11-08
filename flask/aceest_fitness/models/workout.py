from datetime import datetime
from pydantic import BaseModel, Field, field_validator

VALID_CATEGORIES = {"Warm-up", "Workout", "Cool-down"}

class WorkoutIn(BaseModel):
    category: str = Field(default="Workout")
    exercise: str
    duration: int  # minutes

    @field_validator("exercise")
    @classmethod
    def exercise_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("exercise must be non-empty")
        return v.strip()

    @field_validator("duration")
    @classmethod
    def duration_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("duration must be > 0")
        return v

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        v = v.strip()
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}")
        return v
    
    @bp.route("", methods=["GET"])
    def view_workouts():
        # return legacy-compatible flat array
        return jsonify(svc.list_workouts_flat()), 200


class WorkoutOut(BaseModel):
    category: str
    exercise: str
    duration: int
    timestamp: str  
    calories: float | None = None  
