"""Telegram notification sender."""

import os

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_alert(message: str) -> None:
    """Send a Telegram message to the configured chat."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()


def format_pair_alert(pair_label: str, cheap_flights: list[dict], windows: list[dict]) -> str:
    """Format a consolidated alert for a route pair (e.g. CPH ↔ AGP).

    cheap_flights: list of flight dicts with matching_windows already attached.
    """
    lines = [
        f"<b>✈️ {pair_label}</b>",
        "",
    ]

    # Sort: outbound (XXX→AGP) first, then return (AGP→XXX), by date
    for flight in sorted(cheap_flights, key=lambda f: (f["route_from"] == "AGP", f["departure_date"])):
        lines.append(
            f"<b>{flight['route_from']}→{flight['route_to']}</b>  "
            f"💰 {flight['price']:.0f} {flight['currency']}  "
            f"📅 {flight['departure_date']}  "
            f"✈️ {flight['airline']}"
        )
        lines.append(f"  🔗 <a href=\"{flight['booking_link']}\">Book</a>")

    lines.append("")
    lines.append("<b>🏠 Available apartments:</b>")
    seen = set()
    for w in windows:
        start = w["window_start"].isoformat() if hasattr(w["window_start"], "isoformat") else w["window_start"]
        end = w["window_end"].isoformat() if hasattr(w["window_end"], "isoformat") else w["window_end"]
        key = (w["apartment_name"], start, end)
        if key not in seen:
            seen.add(key)
            lines.append(f"  {w['apartment_name']}: {start} → {end}")

    return "\n".join(lines)
