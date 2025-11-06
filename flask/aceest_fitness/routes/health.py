from flask import Blueprint, jsonify
bp = Blueprint("health", __name__)

@bp.get("")
def health():
    return jsonify({"status": "healthy"})
