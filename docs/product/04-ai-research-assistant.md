# 04 — AI Betting Research Assistant

**Status:** Proposed · **Priority:** P2 · **Positioning:** Evidence-backed research, not guaranteed picks

## Goal
Let users query GetSTAM's historical games, trends, player props, and current lines in plain English and receive auditable, sourced research.

## Example prompts
- “Find NFL receiving props with at least 7 overs in the last 10 games relative to today's line.”
- “Compare this MLB pitching matchup using recent ERA, innings, and opponent splits.”
- “Show where the historical trends for tonight's matchup disagree.”

## Proposed UX
```text
Ask GetSTAM AI: [Research a game, player, or market...]
Filters: NFL | Player props | Last 10 | Minimum sample: 8
Answer: 3 matching results
[Player / Market] [Current line] [Historical count] [Data freshness]
Why it matched: explicit filters and game-level evidence
Caveats: injuries, missing games, line movement, small samples
[Open evidence] [Save research]
```

## Architecture
1. Parse question into a typed query plan.
2. Use allowlisted tools to fetch current odds, historical stats, and trends.
3. Calculate aggregates deterministically in Python/SQL rather than relying on model arithmetic.
4. Validate tool outputs, timestamps, data completeness, and sample sizes.
5. Compose explanation with direct links to game logs and source data.
6. Log anonymized evaluation traces, latency, errors, and cost; enforce rate limits and entitlements.

## Trust and safety
- Do not claim historical hit rate equals future win probability.
- Avoid “guaranteed,” “lock,” and unsupported expected-value claims.
- Disclose uncertainty, sample overlap, and missing data.
- Separate informational analysis from placing bets; no automated wagering in v1.
- Prevent prompt injection from retrieved text and keep secrets out of model context.
- Provide age-appropriate and jurisdiction-appropriate responsible gambling notices.

## Phased release
- **V1:** Read-only, one sport, limited query templates and cited game evidence.
- **V2:** More markets, follow-up questions, saved searches.
- **V3:** Optional alerts and personalized research workflows with explicit consent.

## Acceptance criteria
- Every numeric claim can be traced to a data query and source.
- Unsupported queries return a clear limitation, not fabricated results.
- Tests cover missing odds, player aliases, ambiguous markets, small samples, and prompt injection.
- Track answer correctness, tool failure rate, cost/query, retention, and conversion.
- Set budget and latency limits before expanding access.

## Dependencies
Reliable [Player Props](02-player-props.md), historical data APIs, auth, [Pro entitlements](03-getstam-pro.md), and data licensing review.
