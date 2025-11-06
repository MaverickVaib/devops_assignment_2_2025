from typing import List
from datetime import datetime
from ..models.workout import Workout

class WorkoutsService:
    def __init__(self):
        self._workouts: List[Workout] = []

    def add(self, workout: str, duration: int) -> Workout:
        if not workout or duration <= 0:
            raise ValueError("Invalid workout or duration")
        w = Workout(workout=workout, duration=duration, timestamp=datetime.now())
        self._workouts.append(w)
        return w

    def list_all(self) -> List[Workout]:
        return self._workouts

    def total_minutes(self) -> int:
        return sum(w.duration for w in self._workouts)

workouts_service = WorkoutsService()
