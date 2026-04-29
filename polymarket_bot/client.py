"""Polymarket Gamma API client.

The Gamma API is Polymarket's public read-only data endpoint. No auth required.
Docs: https://docs.polymarket.com/
"""
from __future__ import annotations

import json
from typing import Any

import requests

GAMMA_BASE = "https://gamma-api.polymarket.com"


def _get(path: str, params: dict[str, Any]) -> Any:
    resp = requests.get(f"{GAMMA_BASE}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_events(tag_slug: str, limit: int = 50) -> list[dict]:
    """Fetch active, open events for a tag (e.g. 'politics', 'weather').

    Each event groups one or more related markets (e.g. an election event
    contains a market per candidate). Sorted by 24h volume, descending.
    """
    return _get(
        "/events",
        {
            "tag_slug": tag_slug,
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "order": "volume24hr",
            "ascending": "false",
        },
    )


def fetch_top_markets(limit: int = 50) -> list[dict]:
    """Fetch the day's most active markets across all categories."""
    return _get(
        "/markets",
        {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "order": "volume24hr",
            "ascending": "false",
        },
    )


def flatten_markets(events: list[dict]) -> list[dict]:
    """Pull individual markets out of their parent events, copying useful
    event-level metadata onto each market for downstream scoring."""
    out: list[dict] = []
    for ev in events:
        ev_title = ev.get("title")
        ev_slug = ev.get("slug")
        for m in ev.get("markets", []) or []:
            m = dict(m)
            m["_event_title"] = ev_title
            m["_event_slug"] = ev_slug
            out.append(m)
    return out


def parse_outcomes(market: dict) -> list[tuple[str, float]]:
    """Return [(outcome_label, price), ...] for a market.

    Polymarket returns these as JSON-encoded strings on the market object.
    """
    outcomes_raw = market.get("outcomes") or "[]"
    prices_raw = market.get("outcomePrices") or "[]"
    try:
        outcomes = (
            json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        )
        prices = (
            json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        )
    except json.JSONDecodeError:
        return []
    pairs: list[tuple[str, float]] = []
    for label, price in zip(outcomes, prices):
        try:
            pairs.append((str(label), float(price)))
        except (TypeError, ValueError):
            continue
    return pairs


def market_url(market: dict) -> str:
    slug = market.get("slug") or market.get("_event_slug")
    if not slug:
        return "https://polymarket.com/"
    return f"https://polymarket.com/event/{slug}"
