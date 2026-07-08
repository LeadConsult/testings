import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-this-in-production")
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'bi_baseline.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Shared team password (single login for the whole team, per requirements)
    TEAM_PASSWORD = os.environ.get("TEAM_PASSWORD", "1")
