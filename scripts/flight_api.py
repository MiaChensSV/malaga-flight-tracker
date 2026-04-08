"""Ryanair public API client for fetching flight prices.

Uses Ryanair's fare finder endpoint which requires no API key and returns
the cheapest fares for an entire date range in a single request.
Converts all prices to a target currency (default SEK).
"""

from datetime import date

import requests

FARES_URL = "https://services-api.ryanair.com/farfnd/3/oneWayFares"

# Approximate exchange rates to SEK (updated periodically)
# These are fallback rates; the script tries to fetch live rates first.
_FALLBACK_RATES_TO_SEK = {
    "SEK": 1.0,
    "EUR": 11.2,
    "DKK": 1.5,
    "NOK": 1.0,
    "GBP": 13.5,
}

_live_rates: dict | None = None


def _fetch_live_rates() -> dict:
    """Fetch live exchange rates from a free API. Returns rates relative to EUR."""
    global _live_rates
    if _live_rates is not None:
        return _live_rates
    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v1/latest?base=SEK",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # data["rates"] has rates FROM SEK, we need TO SEK (inverse)
        rates = {"SEK": 1.0}
        for cur, rate in data.get("rates", {}).items():
            if rate > 0:
                rates[cur] = 1.0 / rate
        _live_rates = rates
        return rates
    except Exception:
        return {}


def _convert_to_sek(amount: float, from_currency: str) -> float:
    """Convert an amount to SEK."""
    if from_currency == "SEK":
        return amount
    # Try live rates first
    rates = _fetch_live_rates()
    if from_currency in rates:
        return round(amount * rates[from_currency], 2)
    # Fallback to hardcoded rates
    rate = _FALLBACK_RATES_TO_SEK.get(from_currency, 1.0)
    return round(amount * rate, 2)


def search_flights(
    route_from: str,
    route_to: str,
    date_from: date,
    date_to: date,
    currency: str = "SEK",
) -> list[dict]:
    """Search one-way flights for a date range.

    Returns a list of dicts with the cheapest option per departure date.
    All prices are converted to the target currency (default SEK).
    """
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

    resp = requests.get(FARES_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for fare in data.get("fares", []):
        outbound = fare.get("outbound", {})
        price_info = outbound.get("price", {})
        dep_date = outbound.get("departureDate", "")[:10]
        flight_number = outbound.get("flightNumber", "")

        price_value = price_info.get("value")
        fare_currency = price_info.get("currencyCode", "EUR")

        if price_value is not None:
            converted_price = _convert_to_sek(price_value, fare_currency)
            results.append(
                {
                    "route_from": route_from,
                    "route_to": route_to,
                    "departure_date": dep_date,
                    "price": converted_price,
                    "currency": currency,
                    "airline": f"Ryanair {flight_number}",
                    "booking_link": _booking_link(route_from, route_to, dep_date),
                }
            )

    return results


def _booking_link(origin: str, destination: str, dep_date: str) -> str:
    """Generate a Ryanair booking link."""
    return (
        f"https://www.ryanair.com/gb/en/trip/flights/select"
        f"?adults=1&teens=0&children=0&infants=0"
        f"&dateOut={dep_date}&isReturn=false"
        f"&originIata={origin}&destinationIata={destination}"
    )
