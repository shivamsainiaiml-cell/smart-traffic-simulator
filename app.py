"""Flask application: serves the dashboard and a small JSON API."""
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from simulation import DEFAULTS, DENSITY_PRESETS, LIMITS, run_comparison, run_simulation
from simulation.config import STRATEGIES, parse_config
from live_api import live_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(live_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/config")
    def get_config():
        return jsonify({"defaults": DEFAULTS, "limits": LIMITS,
                        "density_presets_per_second": DENSITY_PRESETS,
                        "strategies": list(STRATEGIES)})

    def _body():
        raw = request.get_data(cache=True)
        if not raw.strip():
            return {}
        data = request.get_json(silent=True)
        if data is None:
            raise ValueError("Request body must be valid JSON.")
        return data

    @app.post("/api/simulate")
    def simulate():
        data = _body()
        strategy = str(data.get("strategy", "adaptive")).lower() if isinstance(data, dict) else ""
        if strategy not in STRATEGIES:
            raise ValueError("'strategy' must be 'fixed' or 'adaptive'.")
        return jsonify(run_simulation(parse_config(data), strategy))

    @app.post("/api/compare")
    def compare():
        return jsonify(run_comparison(parse_config(_body())))

    @app.errorhandler(ValueError)
    def bad_request(err):
        return jsonify({"error": str(err)}), 400

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def not_allowed(_err):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(Exception)
    def unexpected(err):
        if isinstance(err, HTTPException):
            return jsonify({"error": err.description}), err.code
        app.logger.exception("Unexpected error: %s", err)
        return jsonify({"error": "Unexpected server error."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
