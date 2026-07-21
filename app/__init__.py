"""
V10 NEXUS Swarm — Flask Application Factory
===========================================
Чистая фабрика приложения. Нет глобальных объектов.
Все расширения инициализируются здесь и передаются в сервисы.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

# Extensions (инициализируются в фабрике)
db = SQLAlchemy()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()


def create_app(config_name: str = "production") -> Flask:
    """Фабрика приложения — создаёт Flask app с нуля."""

    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # === Configuration ===
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set in environment variables")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # === Initialize Extensions ===
    db.init_app(app)
    socketio.init_app(app, async_mode="eventlet", cors_allowed_origins="*")
    limiter.init_app(app)
    migrate.init_app(app, db)

    # === Register Blueprints ===
    from blueprints.public import public_bp
    from blueprints.auth import auth_bp
    from blueprints.exchanges import exchanges_bp
    from blueprints.trading import trading_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(exchanges_bp, url_prefix="/api/exchanges")
    app.register_blueprint(trading_bp, url_prefix="/api/trading")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # === Error Handlers ===
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500

    # === Create Tables (dev only) ===
    with app.app_context():
        db.create_all()

    return app
