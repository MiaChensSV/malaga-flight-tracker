"""Main orchestrator: calendar check → flight search → alert."""

import sys
from datetime import date

from db import get_client, get_settings, get_apartments, upsert_prices, insert_price_history
from calendar_api import get_available_windows
from flight_api import search_flights
from notify import send_alert, format_pair_alert


def _date_in_any_window(dep_date: date, windows: list[dict]) -> list[dict]:
    """Return which apartment windows contain the given departure date."""
    matching = []
    for w in windows:
        if w["window_start"] <= dep_date <= w["window_end"]:
            matching.append(w)
    return matching


def _route_pair_key(route_from: str, route_to: str) -> str:
    """Return a consistent key for a route pair, Scandinavian airport first (e.g. 'CPH ↔ AGP')."""
    if route_from == "AGP":
        return f"{route_to} ↔ {route_from}"
    return f"{route_from} ↔ {route_to}"


def main():
    print("Starting flight price check...")
    client = get_client()

    # 1. Read settings and apartments
    settings = get_settings(client)
    apartments = get_apartments(client)

    if not settings:
        print("No route settings found. Exiting.")
        return
    if not apartments:
        print("No apartments configured. Exiting.")
        return

    # Use the maximum look_ahead_days across all settings
    max_look_ahead = max(s.get("look_ahead_days", 60) for s in settings)

    # 2. Check Google Calendar for available windows
    print(f"Checking apartment calendars ({len(apartments)} apartments)...")
    windows = get_available_windows(apartments, max_look_ahead)

    if not windows:
        print("No 5+ day available windows found on any apartment. Done.")
        return

    print(f"Found {len(windows)} available window(s):")
    for w in windows:
        print(f"  {w['apartment_name']}: {w['window_start']} → {w['window_end']}")

    # 3. Search flights and collect cheap ones grouped by route pair
    today = date.today()
    all_prices = []
    # Group cheap flights by route pair: {'CPH ↔ AGP': [flight, ...]}
    cheap_by_pair: dict[str, list[dict]] = {}
    seen_flights: set = set()  # Dedup: (route_from, route_to, date)

    for setting in settings:
        route_from = setting["route_from"]
        route_to = setting["route_to"]
        currency = setting.get("currency", "EUR")
        threshold = setting.get("price_threshold")
        look_ahead = setting.get("look_ahead_days", 60)

        # Collect and merge all window ranges for this route
        raw_ranges = []
        for w in windows:
            w_start = max(w["window_start"], today)
            w_end = w["window_end"]
            if (w_start - today).days <= look_ahead:
                raw_ranges.append((w_start, w_end))

        if not raw_ranges:
            print(f"  {route_from}→{route_to}: no windows within look-ahead. Skipping.")
            continue

        # Merge overlapping/adjacent ranges to avoid duplicate API calls
        raw_ranges.sort()
        merged = [raw_ranges[0]]
        for start, end in raw_ranges[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # Search each merged range
        for range_start, range_end in merged:
            print(f"  Searching {route_from}→{route_to} for {range_start} to {range_end}...")
            try:
                prices = search_flights(route_from, route_to, range_start, range_end, currency)
            except Exception as e:
                print(f"  Error fetching {route_from}→{route_to}: {e}")
                continue

            all_prices.extend(prices)

            # Collect cheap flights for grouped alerts
            if threshold is None:
                continue
            for flight in prices:
                if flight["price"] is not None and flight["price"] < threshold:
                    flight_key = (flight["route_from"], flight["route_to"], flight["departure_date"])
                    if flight_key in seen_flights:
                        continue
                    dep = date.fromisoformat(flight["departure_date"])
                    matching = _date_in_any_window(dep, windows)
                    if matching:
                        pair = _route_pair_key(route_from, route_to)
                        cheap_by_pair.setdefault(pair, []).append(flight)
                        seen_flights.add(flight_key)

    # 4. Send one consolidated Telegram alert per route pair
    alerts_sent = 0
    for pair_label, flights in cheap_by_pair.items():
        # Collect all relevant apartment windows for these flights
        all_matching = []
        for f in flights:
            dep = date.fromisoformat(f["departure_date"])
            all_matching.extend(_date_in_any_window(dep, windows))

        msg = format_pair_alert(pair_label, flights, all_matching)
        try:
            send_alert(msg)
            alerts_sent += 1
            print(f"  Alert sent for {pair_label}: {len(flights)} cheap flights")
        except Exception as e:
            print(f"  Failed to send alert for {pair_label}: {e}")

    # 5. Save to database
    if all_prices:
        print(f"Saving {len(all_prices)} price records...")
        try:
            upsert_prices(client, all_prices)
            insert_price_history(client, all_prices)
        except Exception as e:
            print(f"Error saving prices: {e}")

    print(f"Done. {len(all_prices)} prices checked, {alerts_sent} alert messages sent.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
