import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Vercel's filesystem is read-only except /tmp, so the SQLite file must live there.
_default_db = "/tmp/shaksham.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "instance", "shaksham.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE = os.environ.get("DATABASE_PATH", _default_db)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
