import argparse
from collections import defaultdict
from tabulate import tabulate
from typing import List, Dict, Optional
from adapters.tequila import TequilaAdapter
# from adapters.ryanair import RyanairAdapter
from adapters.util_types import Offer
from storage import Storage
from utils import safe_div, human_money

def aggregate_offers(providers, origin: str, days: int, nonstop: bool, max_price: Optional[int]) -> List[Offer]:
    results: List[Offer] = []
    for p in providers:
        try:
            results.extend(p.search_offers(origin=origin, days=days, nonstop=nonstop, max_price=max_price))
        except Exception as e:
            print(f"[WARN] Провайдер {p.__class__.__name__} не ответил: {e}")
    return results

def compute_baselines(tequila: TequilaAdapter, offers: List[Offer], storage: Optional[Storage], persist: bool) -> Dict[str, float]:
    baselines: Dict[str, float] = {}
    # Ключ: RIX-XXX
    routes = sorted({(o.origin, o.destination) for o in offers})
    for origin, dest in routes:
        avg = tequila.avg_price_next_year(origin, dest)
        if avg is None and storage:
            # Попробуем локальную историю за 365 дней
            avg = storage.avg_price(origin, dest, days=365)
        if avg is None:
            # Приближение: среднее по текущим найденным предложениям по данному маршруту
            vals = [o.price for o in offers if o.origin==origin and o.destination==dest]
            avg = sum(vals)/len(vals) if vals else None
        if avg is not None:
            baselines[f"{origin}-{dest}"] = avg
    if persist and storage:
        # Запишем наблюдения
        for o in offers:
            try:
                storage.add_observation(o.origin, o.destination, o.date, o.price, o.currency, o.provider)
            except Exception:
                pass
    return baselines

def select_deals(offers: List[Offer], baselines: Dict[str, float], threshold: float, max_price: Optional[int]) -> List[Offer]:
    deals = []
    for o in offers:
        key = f"{o.origin}-{o.destination}"
        base = baselines.get(key)
        if base is None:
            continue
        if o.price <= base * threshold and (max_price is None or o.price <= max_price):
            deals.append(o)
    # Сгруппируем по направлению и оставим самое дешёвое предложение
    best_by_route = {}
    for d in deals:
        k = (d.destination, d.destination_city)
        if k not in best_by_route or d.price < best_by_route[k].price:
            best_by_route[k] = d
    return sorted(best_by_route.values(), key=lambda x: x.price)

def render_table(deals: List[Offer], baselines: Dict[str, float]):
    rows = []
    for d in deals:
        key = f"{d.origin}-{d.destination}"
        base = baselines.get(key, 0)
        discount = (1 - (d.price / base)) * 100 if base else 0
        rows.append([
            d.origin, d.destination, d.destination_city or "", d.country_code or "",
            d.date, human_money(d.price, d.currency),
            human_money(base, d.currency) if base else "—",
            f"{discount:.0f}%",
            d.provider
        ])
    headers = ["Из", "В (IATA)", "Город", "Страна", "Дата вылета", "Цена", "Среднегодовая", "Ниже на", "Источник"]
    print(tabulate(rows, headers=headers, tablefmt="github"))
    return headers, rows

def save_csv(headers, rows, path="deals.csv"):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"\nСохранено в {path}")

def main():
    ap = argparse.ArgumentParser(description="Поиск направлений из RIX по Европе ниже среднегодовой цены")
    ap.add_argument("--origin", default="RIX", help="Код аэропорта отправления (по умолчанию RIX)")
    ap.add_argument("--days", type=int, default=180, help="Горизонт в днях вперёд (1..365)")
    ap.add_argument("--threshold", type=float, default=1.0, help="Порог относительно средней (1.0=ниже среднего; 0.8=ниже на 20%)")
    ap.add_argument("--nonstop", action="store_true", help="Только прямые рейсы")
    ap.add_argument("--max-price", type=int, default=None, help="Максимальная цена в EUR")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--persist", action="store_true", help="Копить локальную историю цен в deals.sqlite")
    args = ap.parse_args()

    tequila = TequilaAdapter(currency=args.currency)
    providers = [tequila]
    # providers.append(RyanairAdapter())  # пример для подключения дополнительных источников

    storage = Storage() if args.persist else None

    offers = aggregate_offers(providers, origin=args.origin, days=args.days, nonstop=args.nonstop, max_price=args.max_price)
    if not offers:
        print("Не найдено предложений. Попробуйте увеличить диапазон дней или убрать фильтры.")
        return

    baselines = compute_baselines(tequila, offers, storage, persist=bool(storage))

    deals = select_deals(offers, baselines, threshold=args.threshold, max_price=args.max_price)

    headers, rows = render_table(deals, baselines)
    save_csv(headers, rows, path="deals.csv")

if __name__ == "__main__":
    main()