"""Multi-source flight price search.

1. Google Flights (via fast-flights) — all airlines (easyJet, Norwegian, SAS, Ryanair, etc.)
2. Ryanair fare finder API — Ryanair-only fallback, no API key needed

Keeps the cheapest price per date across all sources. All prices converted to SEK.
"""

import time
from datetime import date, timedelta

import requests

# ---------------------------------------------------------------------------
# Currency conversion
# ---------------------------------------------------------------------------

FARES_URL = "https://services-api.ryanair.com/farfnd/3/oneWayFares"

_FALLBACK_RATES_TO_SEK = {
    "SEK": 1.0,
    "EUR": 11.2,
    "DKK": 1.5,
    "NOK": 1.0,
    "GBP": 13.5,
    "USD": 10.5,
}

_live_rates: dict | None = None


def _fetch_live_rates() -> dict:
    global _live_rates
    if _live_rates is not None:
        return _live_rates
    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v1/latest?base=SEK",
            timeout=10,
        )
        resp.raise_for_status()
        rates = {"SEK": 1.0}
        for cur, rate in resp.json().get("rates", {}).items():
            if rate > 0:
                rates[cur] = 1.0 / rate
        _live_rates = rates
        return rates
    except Exception:
        return {}


def _to_sek(amount: float, from_currency: str) -> float:
    if from_currency == "SEK":
        return round(amount, 2)
    rates = _fetch_live_rates()
    if from_currency in rates:
        return round(amount * rates[from_currency], 2)
    return round(amount * _FALLBACK_RATES_TO_SEK.get(from_currency, 1.0), 2)


# ---------------------------------------------------------------------------
# Google Flights via fast-flights (all airlines)
# ---------------------------------------------------------------------------

def _search_google_flights(
    route_from: str, route_to: str, date_from: date, date_to: date
) -> list[dict]:
    """Search Google Flights for cheapest flight per date. Returns [] on failure."""
    try:
        from fast_flights import get_flights, FlightData, Passengers
    except ImportError:
        print("    fast-flights not installed, skipping Google Flights.")
        return []

    results = []
    current = date_from
    while current <= date_to:
        try:
            result = get_flights(
                flight_data=[
                    FlightData(
                        date=current.isoformat(),
                        from_airport=route_from,
                        to_airport=route_to,
                    )
                ],
                trip="one-way",
                seat="economy",
                passengers=Passengers(adults=1),
            )

            if result.flights:
                best = result.flights[0]  # First result is cheapest
                # Parse price string like "SEK 1,234" or "€123"
                price_sek = _parse_google_price(best.price)
                if price_sek is not None:
                    results.append(
                        {
                            "route_from": route_from,
                            "route_to": route_to,
                            "departure_date": current.isoformat(),
                            "price": price_sek,
                            "currency": "SEK",
                            "airline": best.name or "Unknown",
                            "booking_link": _google_flights_link(
                                route_from, route_to, current.isoformat()
                            ),
                        }
                    )
        except Exception as e:
            print(f"    Google Flights error for {current}: {e}")
            # If we get consent/block errors, stop trying this source
            if "cookie" in str(e).lower() or "consent" in str(e).lower():
                print("    Google Flights blocked (consent). Stopping.")
                break

        current += timedelta(days=1)
        time.sleep(1)  # Be polite to Google

    return results


def _parse_google_price(price_str: str) -> float | None:
    """Parse price strings like 'SEK 1,234', '€123', 'kr1 234', '$99'."""
    if not price_str:
        return None
    # Map currency symbols/prefixes
    currency_map = {
        "€": "EUR", "EUR": "EUR",
        "$": "USD", "USD": "USD",
        "£": "GBP", "GBP": "GBP",
        "kr": "SEK", "SEK": "SEK",
        "DKK": "DKK", "NOK": "NOK",
    }
    detected_currency = "SEK"
    cleaned = price_str.strip()

    for symbol, cur in currency_map.items():
        if symbol in cleaned:
            detected_currency = cur
            cleaned = cleaned.replace(symbol, "")
            break

    # Remove non-numeric characters except dot
    cleaned = cleaned.replace(",", "").replace(" ", "").replace("\xa0", "").strip()
    try:
        amount = float(cleaned)
        return _to_sek(amount, detected_currency)
    except ValueError:
        return None


def _google_flights_link(origin: str, dest: str, dep_date: str) -> str:
    return f"https://www.google.com/travel/flights?q=Flights+from+{origin}+to+{dest}+on+{dep_date}"


# ---------------------------------------------------------------------------
# Ryanair fare finder (Ryanair-only, no API key)
# ---------------------------------------------------------------------------

def _search_ryanair(
    route_from: str, route_to: str, date_from: date, date_to: date
) -> list[dict]:
    """Search Ryanair fares. Returns entire date range in one API call."""
    params = {
        "departureAirportIataCode": route_from,
        "arrivalAirportIataCode": route_to,
        "language": "en",
        "market": "en-gb",
        "outboundDepartureDateFrom": date_from.isoformat(),
        "outboundDepartureDateTo": date_to.isoformat(),
        "limit": 100,
        "offset": 0,
    }
    try:
        resp = requests.get(FARES_URL, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"    Ryanair API error: {e}")
        return []

    results = []
    for fare in resp.json().get("fares", []):
        outbound = fare.get("outbound", {})
        price_info = outbound.get("price", {})
        dep_date = outbound.get("departureDate", "")[:10]
        flight_number = outbound.get("flightNumber", "")
        price_value = price_info.get("value")
        fare_currency = price_info.get("currencyCode", "EUR")

        if price_value is not None:
            results.append(
                {
                    "route_from": route_from,
                    "route_to": route_to,
                    "departure_date": dep_date,
                    "price": _to_sek(price_value, fare_currency),
                    "currency": "SEK",
                    "airline": f"Ryanair {flight_number}",
                    "booking_link": _ryanair_link(route_from, route_to, dep_date),
                }
            )
    return results


def _ryanair_link(origin: str, dest: str, dep_date: str) -> str:
    return (
        f"https://www.ryanair.com/gb/en/trip/flights/select"
        f"?adults=1&teens=0&children=0&infants=0"
        f"&dateOut={dep_date}&isReturn=false"
        f"&originIata={origin}&destinationIata={dest}"
    )


# ---------------------------------------------------------------------------
# Combined search (public API)
# ---------------------------------------------------------------------------

def search_flights(
    route_from: str,
    route_to: str,
    date_from: date,
    date_to: date,
    currency: str = "SEK",
) -> list[dict]:
    """Search all sources and return the cheapest flight per date."""
    all_results = []

    # Source 1: Google Flights (all airlines)
    print(f"    [Google Flights] {route_from}→{route_to}...")
    gf = _search_google_flights(route_from, route_to, date_from, date_to)
    print(f"    [Google Flights] {len(gf)} results")
    all_results.extend(gf)

    # Source 2: Ryanair (fast bulk fetch)
    print(f"    [Ryanair] {route_from}→{route_to}...")
    ry = _search_ryanair(route_from, route_to, date_from, date_to)
    print(f"    [Ryanair] {len(ry)} results")
    all_results.extend(ry)

    # Deduplicate: keep cheapest per date
    best_per_date: dict[str, dict] = {}
    for r in all_results:
        key = r["departure_date"]
        if key not in best_per_date or r["price"] < best_per_date[key]["price"]:
            best_per_date[key] = r

    return list(best_per_date.values())
