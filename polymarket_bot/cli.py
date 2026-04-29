"""CLI entry point.

Usage:
    python -m polymarket_bot                      # full daily report
    python -m polymarket_bot politics             # politics pick only
    python -m polymarket_bot weather              # weather pick only
    python -m polymarket_bot top --n 10           # top-N daily picks
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from . import analyzer, client, scoring


def _politics_markets(limit: int) -> list[dict]:
    events = client.fetch_events("politics", limit=limit)
    return scoring.rank_markets(client.flatten_markets(events), top_n=15)


def _weather_markets(limit: int) -> list[dict]:
    events = client.fetch_events("weather", limit=limit)
    return scoring.rank_markets(client.flatten_markets(events), top_n=10)


def _top_markets(limit: int, n: int) -> list[dict]:
    return scoring.rank_markets(client.fetch_top_markets(limit=limit), top_n=n * 2)


def cmd_politics(args: argparse.Namespace) -> int:
    markets = _politics_markets(args.fetch)
    print("# Politics — pick of the day\n")
    print(analyzer.best_pick(markets, "politics"))
    return 0


def cmd_weather(args: argparse.Namespace) -> int:
    markets = _weather_markets(args.fetch)
    print("# Weather — pick of the day\n")
    print(analyzer.best_pick(markets, "weather"))
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    markets = _top_markets(args.fetch, args.n)
    print(f"# Top {args.n} bets to consider today\n")
    print(analyzer.top_picks(markets, n=args.n))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"# Polymarket daily report — {today}\n")

    print("## Top 10 bets to consider today\n")
    print(analyzer.top_picks(_top_markets(args.fetch, 10), n=10))
    print()

    print("## Politics — pick of the day\n")
    print(analyzer.best_pick(_politics_markets(args.fetch), "politics"))
    print()

    print("## Weather — pick of the day\n")
    print(analyzer.best_pick(_weather_markets(args.fetch), "weather"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="polymarket-bot",
        description=(
            "Polymarket research bot. Reads live markets, recommends bets — "
            "does NOT place them."
        ),
    )
    parser.add_argument(
        "--fetch",
        type=int,
        default=50,
        help="How many raw markets/events to pull before ranking (default 50).",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("politics", help="Best politics pick today").set_defaults(
        func=cmd_politics
    )
    sub.add_parser("weather", help="Best weather pick today").set_defaults(
        func=cmd_weather
    )
    p_top = sub.add_parser("top", help="Top N bets today across all categories")
    p_top.add_argument("--n", type=int, default=10)
    p_top.set_defaults(func=cmd_top)

    args = parser.parse_args(argv)
    func = getattr(args, "func", cmd_report)
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
