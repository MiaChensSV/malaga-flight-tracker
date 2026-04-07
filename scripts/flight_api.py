"""Kiwi Tequila API client for fetching flight prices."""

import os
from datetime import date

import requests

BASE_URL = "https://tequila-api.kiwi.com/v2/search"


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
    api_key = os.environ["KIWI_API_KEY"]

    params = {
        "fly_from": route_from,
        "fly_to": route_to,
        "date_from": date_from.strftime("%d/%m/%Y"),
        "date_to": date_to.strftime("%d/%m/%Y"),
        "one_for_city": 0,
        "one_per_date": 1,
        "flight_type": "oneway",
        "curr": currency,
        "limit": 1000,
    }
    headers = {"apikey": api_key}

    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for flight in data.get("data", []):
        dep_date = flight.get("local_departure", "")[:10]
        airlines = ", ".join(flight.get("airlines", []))
        results.append(
            {
                "route_from": route_from,
                "route_to": route_to,
                "departure_date": dep_date,
                "price": flight.get("price"),
                "currency": currency,
                "airline": airlines,
                "booking_link": flight.get("deep_link", ""),
            }
        )

    return results
