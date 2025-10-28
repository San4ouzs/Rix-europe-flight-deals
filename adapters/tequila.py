import requests
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from .util_types import Offer
from ..utils import env, is_europe_country

BASE = "https://tequila-api.kiwi.com"

class TequilaAdapter:
    def __init__(self, api_key: Optional[str] = None, currency="EUR", market="lv"):
        self.api_key = api_key or env("TEQUILA_API_KEY")
        self.currency = currency
        self.market = market
        if not self.api_key:
            raise RuntimeError("TEQUILA_API_KEY не найден. Укажите его в .env")

    def _headers(self):
        return {"apikey": self.api_key}

    def search_offers(
        self,
        origin="RIX",
        days=180,
        nonstop=False,
        max_price=None
    ) -> List[Offer]:
        # Диапазон дат: завтра ... +days
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=days)

        params = {
            "fly_from": origin,
            "date_from": start.strftime("%d/%m/%Y"),
            "date_to": end.strftime("%d/%m/%Y"),
            "curr": self.currency,
            "max_stopovers": 0 if nonstop else 2,
            "one_for_city": 1,               # один лучший вариант на город
            "partner_market": self.market,
            "limit": 1000,
            "sort": "price",
            "asc": 1,
            "to": "anywhere"
        }
        if max_price:
            params["price_to"] = int(max_price)

        r = requests.get(f"{BASE}/v2/search", headers=self._headers(), params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        out: List[Offer] = []
        for it in data.get("data", []):
            country_to = (it.get("countryTo", {}) or {}).get("code")
            if not is_europe_country(country_to):
                continue
            city_to = (it.get("cityTo") or it.get("city_to")) or (it.get("cityTo") or {})
            city_to_name = it.get("cityTo") if isinstance(it.get("cityTo"), str) else it.get("cityTo", {}).get("name", "")
            dest_code = it.get("flyTo")
            price = it.get("price")
            d_str = it.get("local_departure", "")[:10] or it.get("utc_departure","")[:10]
            out.append(Offer(
                origin=origin,
                destination=dest_code,
                destination_city=it.get("cityTo", {}).get("name") if isinstance(it.get("cityTo"), dict) else city_to_name,
                country_code=country_to,
                date=d_str,
                price=price,
                currency=self.currency,
                provider="tequila"
            ))
        return out

    def avg_price_next_year(self, origin: str, destination: str) -> Optional[float]:
        # Попытка получить «календарь цен» на год вперёд. Если эндпойнт недоступен — вернём None.
        # Документация Tequila может отличаться; используем резервную стратегию в вызывающем коде.
        try:
            params = {
                "fly_from": origin,
                "fly_to": destination,
                "date_from": (date.today() + timedelta(days=1)).strftime("%d/%m/%Y"),
                "date_to": (date.today() + timedelta(days=365)).strftime("%d/%m/%Y"),
                "curr": self.currency,
                "limit": 1,
                "one_for_city": 0,
                "partner_market": self.market,
                "sort": "price"
            }
            r = requests.get(f"{BASE}/v2/search", headers=self._headers(), params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            prices = [it.get("price") for it in data.get("data", []) if it.get("price") is not None]
            if not prices:
                return None
            # Усредняем по найденным значениям (это приближение; при желании можно выполнить батч‑перебор по месяцам)
            return sum(prices)/len(prices)
        except Exception:
            return None