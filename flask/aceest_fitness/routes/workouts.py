from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from aceest_fitness.models.workout import WorkoutIn
from aceest_fitness.services import workouts_service as svc

bp = Blueprint("workouts", __name__, url_prefix="/api/workouts")

@bp.route("", methods=["POST"])
def add_workout():
    try:
        payload = request.get_json(force=True, silent=False) or {}

        # Back-compat: tests send "workout" instead of "exercise"
        if "exercise" not in payload and "workout" in payload:
            payload["exercise"] = payload.pop("workout")

        w = WorkoutIn(**payload)
    except ValidationError as e:
        # Flatten pydantic errors into a simple, JSON-safe shape
        errors = [
            {
                "loc": ".".join(str(p) for p in err.get("loc", [])),
                "msg": err.get("msg", "invalid"),
                "type": err.get("type", "error"),
            }
            for err in e.errors()
        ]
        return jsonify({"errors": errors}), 400
    except Exception:
        return jsonify({"errors": [{"msg": "invalid json"}]}), 400

    added = svc.add_workout(w)
    return jsonify({"message": "added", "workout": added.model_dump()}), 201

@bp.route("", methods=["GET"])
def view_workouts():
    return jsonify(svc.list_workouts()), 200

@bp.route("/summary", methods=["GET"])
def summary():
    minutes_by_cat, total, msg = svc.summary()
    return jsonify({"minutes": minutes_by_cat, "total_minutes": total, "message": msg}), 200
