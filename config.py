import os
from dotenv import load_dotenv

# Load .env file if it exists (local development)
load_dotenv()

# --- Flask ---
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# --- Database ---
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "3rgacs.h.filess.io"),
    "port":     int(os.environ.get("DB_PORT", "61001")),
    "user":     os.environ.get("DB_USER",     "tour_planner_structure"),
    "password": os.environ.get("DB_PASSWORD", "311dfe5048531cdd1260b94b80c3a2781de2bb62"),
    "database": os.environ.get("DB_NAME",     "tour_planner_structure"),
    "charset":  "utf8mb4",
}

# --- Environment ---
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
