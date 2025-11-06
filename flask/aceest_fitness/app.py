from flask import Flask, jsonify

def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # blueprints
    from .routes.health import bp as health_bp
    from .routes.workouts import bp as workouts_bp
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(workouts_bp, url_prefix="/api/workouts")

    @app.get("/")
    def index():
        return jsonify({
            "name": "ACEest Fitness & Gym API",
            "status": "ok",
            "routes": ["/api/health", "/api/workouts"]
        })

    return app
