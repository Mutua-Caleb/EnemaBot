# Polymarket analysis bot

Reads live Polymarket prediction-market data, hands the most active
markets to Claude (Opus 4.7), and prints a Markdown report with:

1. **Top 10 interesting bets to consider today** — ranked one-liners
2. **Politics — pick of the day** — single deep-dive recommendation
3. **Weather — pick of the day** — single deep-dive recommendation

It produces *recommendations only*. It never places trades. You read the
report and decide.

## How it works

1. `polymarket_bot.client` pulls live data from Polymarket's public Gamma
   API (no auth needed). For section reports it filters by tag slug
   (`politics`, `weather`); for the top-N report it pulls the most
   active markets across all categories.
2. `polymarket_bot.scoring` ranks markets by a composite of 24h volume,
   liquidity, time-to-resolution, and how far the price is from a
   coinflip — surfacing the ~10–20 most worth thinking about.
3. `polymarket_bot.analyzer` sends those summaries to Claude with a
   research-analyst system prompt. Adaptive thinking is on; the system
   prompt is cached so repeat runs in the same session are cheaper.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
# Full daily report (top 10 + politics + weather)
python -m polymarket_bot

# Just the politics pick
python -m polymarket_bot politics

# Just the weather pick
python -m polymarket_bot weather

# Top N across all categories
python -m polymarket_bot top --n 10
```

Pipe to a file or paste into a chat — output is plain Markdown.

## Notes

- **Not financial advice.** This is a research tool. Polymarket markets
  have real money on them; the bot's recommendations are starting points
  for your own thinking, not signals to copy.
- The `weather` section depends on Polymarket having a `weather` tag with
  active markets that day. If it's empty, the section will say so and
  skip.
- Costs scale with how many markets you fetch. Default `--fetch 50` keeps
  a single run well under a few cents on Opus 4.7. Lower it if you want
  to batch.
