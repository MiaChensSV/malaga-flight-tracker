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


def format_alert(flight: dict, matching_windows: list[dict]) -> str:
    """Format a cheap-flight alert message."""
    lines = [
        "<b>✈️ CHEAP FLIGHT + APARTMENT FREE!</b>",
        "",
        f"<b>{flight['route_from']} → {flight['route_to']}</b>",
        f"💰 {flight['price']} {flight['currency']} (one-way)",
        f"📅 {flight['departure_date']}",
        f"✈️ {flight['airline']}",
        f"🔗 <a href=\"{flight['booking_link']}\">Book now</a>",
        "",
    ]
    for w in matching_windows:
        start = w["window_start"].isoformat() if hasattr(w["window_start"], "isoformat") else w["window_start"]
        end = w["window_end"].isoformat() if hasattr(w["window_end"], "isoformat") else w["window_end"]
        lines.append(f"🏠 {w['apartment_name']}: free {start} → {end}")

    return "\n".join(lines)
