import sqlite3

def init_db():
    conn = sqlite3.connect("hakivoice.db")
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
    conn = sqlite3.connect("hakivoice.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cases (phone_number, category, county, sensitive) VALUES (?, ?, ?, ?)",
        (phone_number, category, county, sensitive)
    )
    conn.commit()
    conn.close()