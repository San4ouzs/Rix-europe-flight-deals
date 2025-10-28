import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    provider TEXT NOT NULL,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Storage:
    def __init__(self, path="deals.sqlite"):
        self.path = path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.path) as con:
            con.executescript(SCHEMA)

    def add_observation(self, origin, destination, date, price, currency, provider):
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO price_observations(origin,destination,date,price,currency,provider) VALUES(?,?,?,?,?,?)",
                (origin, destination, date, price, currency, provider),
            )

    def avg_price(self, origin, destination, days=None):
        q = "SELECT AVG(price) FROM price_observations WHERE origin=? AND destination=?"
        args = [origin, destination]
        if days:
            q += " AND ts >= datetime('now', ?||' days')"
            args.append(f"-{int(days)}")
        with sqlite3.connect(self.path) as con:
            cur = con.execute(q, args)
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else None