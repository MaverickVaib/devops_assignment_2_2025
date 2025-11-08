from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from aceest_fitness.models.workout import WorkoutIn
from aceest_fitness.services import workouts_service as svc

bp = Blueprint("workouts", __name__, url_prefix="/api/workouts")

@bp.route("", methods=["POST"])
def add_workout():
    try:
        payload = request.get_json(force=True, silent=False) or {}
        w = WorkoutIn(**payload)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    added = svc.add_workout(w)
    return jsonify({"message": "added", "workout": added.model_dump()}), 201

@bp.route("", methods=["GET"])
def view_workouts():
    return jsonify(svc.list_workouts()), 200

@bp.route("/summary", methods=["GET"])
def summary():
    minutes_by_cat, total, msg = svc.summary()
    return jsonify({"minutes": minutes_by_cat, "total_minutes": total, "message": msg}), 200
