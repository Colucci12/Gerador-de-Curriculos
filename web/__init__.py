"""Aplicação Flask — Resume Tailor MVP."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from . import auth, db
from .routes import bp

ROOT = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    load_dotenv(ROOT / ".env")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("SECRET_KEY não definida no .env.")
    app.config["SECRET_KEY"] = secret
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    db.init_db()

    @app.before_request
    def _load_user():
        auth.load_current_user()

    app.register_blueprint(bp)
    return app
