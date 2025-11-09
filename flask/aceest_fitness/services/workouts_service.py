from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from aceest_fitness.models.workout import WorkoutIn, WorkoutOut, VALID_CATEGORIES

# in-memory store grouped by category
_store: Dict[str, List[WorkoutOut]] = defaultdict(list)
for c in VALID_CATEGORIES:
    _store[c] = []

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")

def _estimate_calories(duration_min: int) -> float:
    # very rough placeholder; tweak if you like
    return round(duration_min * 7.35, 1)

def add_workout(data: WorkoutIn) -> WorkoutOut:
    entry = WorkoutOut(
        category=data.category,
        exercise=data.exercise.strip(),
        duration=data.duration,
        timestamp=_now_iso(),
        calories=_estimate_calories(data.duration),
    )
    _store[data.category].append(entry)
    return entry

def list_workouts() -> Dict[str, List[WorkoutOut]]:
    # return a simple serializable structure
    return {cat: [e.model_dump() for e in entries] for cat, entries in _store.items()}

def summary() -> Tuple[Dict[str, int], int, str]:
    minutes_by_cat: Dict[str, int] = {}
    total = 0
    for cat in VALID_CATEGORIES:
        mins = sum(e.duration for e in _store[cat])
        minutes_by_cat[cat] = mins
        total += mins

    # Motivational message like the Tkinter V1.1 app
    if total < 30:
        msg = "Good start! Aim for 30+ minutes for better stamina."
    elif total < 60:
        msg = "Nice work! You’re building consistency."
    else:
        msg = "Excellent session! Keep up the momentum."

    return minutes_by_cat, total, msg

def list_workouts_flat() -> list[dict]:
    items = []
    for cat, entries in _store.items():
        for e in entries:
            d = e.model_dump()
            # legacy field name for compatibility with tests
            d["workout"] = d.pop("exercise")
            items.append(d)
    return items

def reset_all() -> None:
    for c in VALID_CATEGORIES:
        _store[c].clear()
