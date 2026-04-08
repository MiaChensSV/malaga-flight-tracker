"""Ryanair public API client for fetching flight prices.

Uses Ryanair's fare finder endpoint which requires no API key and returns
the cheapest fares for an entire date range in a single request.
"""

from datetime import date

import requests

FARES_URL = "https://services-api.ryanair.com/farfnd/3/oneWayFares"


def search_flights(
    route_from: str,
    route_to: str,
    date_from: date,
    date_to: date,
    currency: str = "EUR",
) -> list[dict]:
    """Search one-way flights for a date range.

    Returns a list of dicts with the cheapest option per departure date:
        {
            "route_from": str,
            "route_to": str,
            "departure_date": str (YYYY-MM-DD),
            "price": float,
            "currency": str,
            "airline": str,
            "booking_link": str,
        }
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
        fare_currency = price_info.get("currencyCode", currency)

        if price_value is not None:
            results.append(
                {
                    "route_from": route_from,
                    "route_to": route_to,
                    "departure_date": dep_date,
                    "price": price_value,
                    "currency": fare_currency,
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
