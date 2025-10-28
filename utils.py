import os
import re
import math
import pytz
from datetime import datetime
from dotenv import load_dotenv

EUROPE_COUNTRIES = {
    # EU + EEA + UK + CH + Балканы + Вост. Европа + Кавказ (по желанию можно редактировать)
    "AL","AD","AM","AT","AZ","BA","BE","BG","BY","CH","CY","CZ","DE","DK","EE","ES","FI","FO","FR","GB","GE","GI","GR",
    "HR","HU","IE","IS","IT","KZ","LI","LT","LU","LV","MC","MD","ME","MK","MT","NL","NO","PL","PT","RO","RS","RU","SE",
    "SI","SK","SM","TR","UA","VA","XK"
}

def env(key: str, default=None):
    load_dotenv()
    return os.getenv(key, default)

def is_europe_country(code: str) -> bool:
    if not code:
        return False
    return code.upper() in EUROPE_COUNTRIES

def parse_date(d: str):
    # '2025-12-31' or '31/12/2025' → datetime.date
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {d}")

def safe_div(a, b, default=None):
    try:
        return a / b
    except Exception:
        return default

def human_money(v, currency="EUR"):
    try:
        return f"{int(round(v))} {currency}"
    except Exception:
        return f"{v} {currency}"