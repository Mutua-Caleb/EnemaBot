"""Heuristic scoring to surface interesting markets.

The bot does not bet — these scores are inputs to Claude, which produces
the human-readable rationale. The goal here is to filter ~hundreds of raw
markets down to the ~10 most worth thinking about.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import parse_outcomes


def _f(market: dict, key: str, default: float = 0.0) -> float:
    val = market.get(key)
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def days_to_close(market: dict) -> float | None:
    end = market.get("endDate") or market.get("end_date_iso")
    if not end:
        return None
    try:
        # Polymarket dates are ISO 8601 with 'Z'.
        dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    except ValueError:
        return None
    delta = dt - datetime.now(timezone.utc)
    return delta.total_seconds() / 86400.0


def best_outcome(market: dict) -> tuple[str, float] | None:
    """Return the (label, price) of the favored side, or None if unparseable."""
    pairs = parse_outcomes(market)
    if not pairs:
        return None
    return max(pairs, key=lambda p: p[1])


def confidence_edge(price: float) -> float:
    """How far from a coinflip the market is. 0.0 at 50%, 0.5 at 0% or 100%.

    Higher edge = market thinks it knows the answer. We use this as a proxy
    for 'how much signal is in this market' — a 99/1 line is less interesting
    to recommend than a 65/35 line, even if both have the same volume.
    """
    return abs(price - 0.5)


def score_market(market: dict) -> float:
    """Composite score. Higher = more worth a closer look.

    Heuristics:
      - 24h volume (live attention)
      - liquidity (you can actually move size)
      - moderate confidence: not coinflips, not foregone conclusions
      - prefers markets resolving in days-to-weeks, not years
    """
    vol_24h = _f(market, "volume24hr")
    liquidity = _f(market, "liquidity")

    fav = best_outcome(market)
    if fav is None:
        return 0.0
    edge = confidence_edge(fav[1])

    # Sweet spot: 0.55 - 0.85. Penalise both coinflips (no view) and
    # near-certainties (no value left).
    if 0.55 <= fav[1] <= 0.85 or 0.15 <= fav[1] <= 0.45:
        edge_score = 1.0
    elif edge < 0.05:
        edge_score = 0.3
    else:
        edge_score = 0.6

    # Prefer markets that resolve in 1-60 days
    dtc = days_to_close(market)
    if dtc is None or dtc <= 0:
        time_score = 0.5
    elif dtc <= 1:
        time_score = 0.7  # very near-term, but less time for new info
    elif dtc <= 60:
        time_score = 1.0
    elif dtc <= 180:
        time_score = 0.7
    else:
        time_score = 0.4

    # log-ish dampening on volume so a 10x bigger market is ~2x score, not 10x
    vol_score = min(1.0, (vol_24h / 50_000.0) ** 0.5)
    liq_score = min(1.0, (liquidity / 10_000.0) ** 0.5)

    return (
        0.40 * vol_score
        + 0.20 * liq_score
        + 0.25 * edge_score
        + 0.15 * time_score
    )


def rank_markets(markets: list[dict], top_n: int) -> list[dict]:
    scored = [(score_market(m), m) for m in markets]
    scored = [(s, m) for s, m in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_n]]


def summarize_market(market: dict) -> dict[str, Any]:
    """Trim a Polymarket market to the fields we want Claude to reason over.

    Sending the full payload would balloon token count without adding signal.
    """
    fav = best_outcome(market)
    return {
        "question": market.get("question") or market.get("_event_title"),
        "outcomes": parse_outcomes(market),
        "favored": {"label": fav[0], "price": round(fav[1], 3)} if fav else None,
        "volume_24h": round(_f(market, "volume24hr"), 2),
        "liquidity": round(_f(market, "liquidity"), 2),
        "days_to_close": (
            round(days_to_close(market), 1) if days_to_close(market) else None
        ),
        "category": market.get("_event_title"),
        "description": (market.get("description") or "")[:400],
    }
