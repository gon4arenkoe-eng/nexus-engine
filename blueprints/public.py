"""Public blueprint."""

from flask import Blueprint, jsonify, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    """Main page."""
    return render_template("index.html")


@public_bp.route("/health")
def health_check():
    """Health check endpoint."""
    return (
        jsonify(
            {
                "status": "healthy",
                "version": "10.0.0",
                "name": "NEXUS Swarm",
            }
        ),
        200,
    )


@public_bp.route("/api/status")
def api_status():
    """API status and version info."""
    return jsonify(
        {
            "name": "NEXUS Swarm API",
            "version": "10.0.0",
            "status": "operational",
            "features": [
                "multi_exchange",
                "agent_architecture",
                "async_trading",
                "websocket_realtime",
            ],
        }
    )
