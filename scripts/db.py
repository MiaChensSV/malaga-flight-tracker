"""Supabase database client for reading settings and writing price data."""

import os
from datetime import datetime, timezone

from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def get_settings(client: Client) -> list[dict]:
    """Fetch all active route settings."""
    resp = client.table("settings").select("*").execute()
    return resp.data


def get_apartments(client: Client) -> list[dict]:
    """Fetch all apartment configurations."""
    resp = client.table("apartments").select("*").execute()
    return resp.data


def upsert_prices(client: Client, prices: list[dict]) -> None:
    """Insert or update current prices. Upsert on (route_from, route_to, departure_date)."""
    if not prices:
        return
    now = datetime.now(timezone.utc).isoformat()
    # Deduplicate: keep cheapest price per (route_from, route_to, departure_date)
    best = {}
    for p in prices:
        key = (p["route_from"], p["route_to"], p["departure_date"])
        if key not in best or (p["price"] is not None and p["price"] < best[key].get("price", float("inf"))):
            best[key] = p
    deduped = list(best.values())
    for p in deduped:
        p["checked_at"] = now
    client.table("prices").upsert(
        deduped, on_conflict="route_from,route_to,departure_date"
    ).execute()


def insert_price_history(client: Client, prices: list[dict]) -> None:
    """Append price snapshots to the history table."""
    if not prices:
        return
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "route_from": p["route_from"],
            "route_to": p["route_to"],
            "departure_date": p["departure_date"],
            "price": p["price"],
            "currency": p["currency"],
            "checked_at": now,
        }
        for p in prices
    ]
    client.table("price_history").insert(rows).execute()
