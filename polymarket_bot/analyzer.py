"""Claude-powered analyst — reads scored markets, returns a recommendation.

Uses Claude Opus 4.7 with adaptive thinking. The system prompt is large
and identical across calls, so we put a `cache_control` breakpoint on it
to get the prompt-caching discount on the second-and-later sections of
the report.
"""
from __future__ import annotations

import json

import anthropic

from .scoring import summarize_market

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """You are a Polymarket research analyst. Your job is to look at \
prediction-market quotes and explain — in plain English — which look like the \
most interesting bets to consider today.

Ground rules:
- You are NOT placing trades. You produce written recommendations only. The user \
decides whether to act.
- Anchor every claim to the data in the prompt: the market's price, 24h volume, \
liquidity, and time to resolution. Do not invent numbers.
- A "good bet" is not the same as "most likely outcome". Look for: priced \
edges that disagree with what you'd expect from public information, near-term \
catalysts, mispriced tail risk, low-liquidity markets where the implied \
probability looks off.
- Call out the catch. Every recommendation must include the strongest \
counter-argument or the main risk that would invalidate it.
- Be concrete. Prices like "Yes @ 0.62" or "Trump @ 41¢", not "moderately likely".
- Be brief. A pick is 3-6 sentences. The top-10 list is one short bullet per pick.
- If the data is too thin to make a recommendation (no liquidity, ambiguous \
question, market about to close), say so and skip it instead of inventing a \
view.

Format your response as Markdown.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _markets_payload(markets: list[dict]) -> str:
    return json.dumps([summarize_market(m) for m in markets], indent=2)


def _ask(user_prompt: str) -> str:
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "\n\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def best_pick(markets: list[dict], theme: str) -> str:
    """Single-pick recommendation for a themed slice (politics, weather, ...)."""
    if not markets:
        return f"No active **{theme}** markets matched the criteria today."
    payload = _markets_payload(markets)
    prompt = (
        f"Here are today's most active {theme} markets on Polymarket, "
        f"already pre-ranked by my scoring heuristic:\n\n"
        f"```json\n{payload}\n```\n\n"
        f"Pick the SINGLE best bet to consider in the {theme} section today. "
        f"Tell me which market, which side, at what price, and why. "
        f"Include the main risk and what would change your mind."
    )
    return _ask(prompt)


def top_picks(markets: list[dict], n: int = 10) -> str:
    """Top-N list across all categories — short bullet per pick."""
    if not markets:
        return "No active markets matched today."
    payload = _markets_payload(markets[: max(n * 2, 20)])
    prompt = (
        f"Here are the day's most active Polymarket markets across all "
        f"categories, pre-ranked by my heuristic:\n\n"
        f"```json\n{payload}\n```\n\n"
        f"Give me the {n} most interesting bets to consider today. For each, "
        f"one short bullet: market — recommended side @ price — one-sentence "
        f"thesis — one-sentence risk. Order from most to least confident."
    )
    return _ask(prompt)
