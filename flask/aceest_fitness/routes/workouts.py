from flask import Blueprint, request, jsonify
from pydantic import BaseModel, Field, ValidationError
from ..services.workouts_service import workouts_service

bp = Blueprint("workouts", __name__)

class WorkoutIn(BaseModel):
    workout: str = Field(min_length=1)
    duration: int = Field(gt=0)

@bp.post("")
def add_workout():
    # mirrors add_workout in Tkinter: require workout + duration, duration must be number :contentReference[oaicite:2]{index=2}
    try:
        data = WorkoutIn.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    w = workouts_service.add(data.workout, data.duration)
    return jsonify({
        "message": "added",
        "workout": {
            "workout": w.workout,
            "duration": w.duration,
            "timestamp": w.timestamp.isoformat()
        }
    }), 201

@bp.get("")
def view_workouts():
    # mirrors "View Workouts" list in the dialog :contentReference[oaicite:3]{index=3}
    arr = workouts_service.list_all()
    return jsonify([{
        "workout": w.workout,
        "duration": w.duration,
        "timestamp": w.timestamp.isoformat()
    } for w in arr])

@bp.get("/summary")
def summary():
    # simple total minutes like the legacy summary text :contentReference[oaicite:4]{index=4}
    return jsonify({"total_minutes": workouts_service.total_minutes()})
