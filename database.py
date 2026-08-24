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
            sensitive INTEGER DEFAULT 0,
            escalated INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_case(phone_number, category, county, sensitive, escalated=0):
    hashed = _hash_phone(phone_number)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cases (phone_number, category, county, sensitive, escalated) VALUES (?, ?, ?, ?, ?)",
        (hashed, category, county, sensitive, escalated)
    )
    conn.commit()
    conn.close()

def severity_index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category,
               COUNT(*) as total,
               SUM(CASE WHEN escalated = 1 THEN 1 ELSE 0 END) as escalations
        FROM cases
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        pct = round(100 * r["escalations"] / r["total"], 1) if r["total"] else 0.0
        result.append({
            "category": r["category"],
            "total": r["total"],
            "escalations": r["escalations"],
            "escalation_rate_pct": pct,
        })
    return result

def weekly_crisis_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%W', timestamp) as wk, COUNT(*) as n
        FROM cases
        WHERE sensitive = 1
        GROUP BY wk
        ORDER BY wk ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"week": wk, "dispatches": n} for wk, n in rows]