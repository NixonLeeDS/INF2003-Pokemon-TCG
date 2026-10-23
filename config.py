import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    MARIADB_HOST = os.getenv("MARIADB_HOST", "127.0.0.1")
    MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
    MARIADB_USER = os.getenv("MARIADB_USER", "root")
    MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
    MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "inf2003_pokemon")

    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "inf2003_pokemon")
