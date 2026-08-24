import sqlite3
import hashlib
import hmac
import os

DB_PATH = "hakivoice.db"

SALT = os.environ.get("HAKIVOICE_HASH_SALT")


def _hash_phone(phone_number: str) -> str:
    if not SALT:
        raise RuntimeError(
            "HAKIVOICE_HASH_SALT is not set. Refusing to log a case without it."
        )
    return hmac.new(SALT.encode(), phone_number.encode(), hashlib.sha256).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            category TEXT,
            county TEXT,
            sensitive INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_case(phone_number, category, county, sensitive):
    hashed = _hash_phone(phone_number)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cases (phone_number, category, county, sensitive) VALUES (?, ?, ?, ?)",
        (hashed, category, county, sensitive)
    )
    conn.commit()
    conn.close()