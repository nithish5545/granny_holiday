import os
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB
import pymysql

load_dotenv()

# --- Flask ---
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# --- Database Config ---
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "3rgacs.h.filess.io"),
    "port":     int(os.environ.get("DB_PORT", " 3306")),
    "user":     os.environ.get("DB_USER",     "tour_planner_structure"),
    "password": os.environ.get("DB_PASSWORD", "311dfe5048531cdd1260b94b80c3a2781de2bb62"),
    "database": os.environ.get("DB_NAME",     "tour_planner_structure"),
    "charset":  "utf8mb4",
}

# --- Connection Pool (max 4 to stay under filess.io limit of 5) ---
db_pool = PooledDB(
    creator=pymysql,
    maxconnections=4,
    mincached=1,
    maxcached=4,
    blocking=True,
    **DB_CONFIG,
    cursorclass=pymysql.cursors.DictCursor
)

def get_db():
    return db_pool.connection()

# --- Environment ---
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
