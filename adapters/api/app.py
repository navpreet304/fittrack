from flask import Flask, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config.settings import get_config
from adapters.db.models import init_db
from adapters.api.routes_auth import auth_bp
from adapters.api.routes_workouts import workouts_bp
from adapters.api.routes_meals import meals_bp
from adapters.api.routes_progress import progress_bp
from adapters.api.routes_coach import coach_bp
from adapters.api.routes_top_level import (
    goals_bp, measurements_bp, notifications_bp,
)
import adapters.api.routes_top_level  # registers extra GET handlers on existing bps


def create_app():
    app = Flask(__name__)
    cfg = get_config()

    app.config["JWT_SECRET_KEY"] = cfg.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = cfg.JWT_ACCESS_TOKEN_EXPIRES
    app.config["DATABASE_URL"] = cfg.DATABASE_URL

    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:4173", "http://127.0.0.1:4173"]}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "OPTIONS"],
    )

    JWTManager(app)

    _, session_local = init_db(cfg.DATABASE_URL)
    app.config["SessionLocal"] = session_local

    from flask import g

    @app.teardown_appcontext
    def _close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(workouts_bp, url_prefix="/workouts")
    app.register_blueprint(meals_bp, url_prefix="/meals")
    app.register_blueprint(progress_bp, url_prefix="/users")
    app.register_blueprint(coach_bp, url_prefix="/coach")
    app.register_blueprint(goals_bp, url_prefix="/goals")
    app.register_blueprint(measurements_bp, url_prefix="/measurements")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    @app.get("/")
    def index():
        return Response(
            """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>FitTrack API Hub</title>
        <style>
            :root { color-scheme: light; }
            body {
                margin: 0;
                font-family: "Segoe UI", sans-serif;
                background: linear-gradient(135deg, #f7efe4, #eef4f7);
                color: #152536;
            }
            main {
                max-width: 860px;
                margin: 0 auto;
                padding: 48px 20px 64px;
            }
            .card {
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(21,37,54,0.12);
                border-radius: 20px;
                padding: 24px;
                margin-top: 18px;
            }
            a { color: #0d6f78; }
            code {
                background: rgba(21,37,54,0.08);
                padding: 2px 6px;
                border-radius: 8px;
            }
            ul { line-height: 1.7; }
        </style>
    </head>
    <body>
        <main>
            <p>FitTrack backend is running.</p>
            <h1>FitTrack API Hub</h1>
            <div class="card">
                <h2>Quick links</h2>
                <ul>
                    <li><a href="/health">API health check</a></li>
                    <li><a href="http://localhost:4173">React PWA</a></li>
                </ul>
            </div>
            <div class="card">
                <h2>Compose stack</h2>
                <p>Start API, database, and PWA together with <code>docker compose up -d --build</code>.</p>
            </div>
        </main>
    </body>
</html>
            """.strip(),
            mimetype="text/html",
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
