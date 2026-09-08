"""
NFL Trend Video Script Generator

For every NFL game that would appear on the homepage's "Today's Trends"
section (not completed, hasTrends), calls Claude to write two spoken video
scripts covering the game's trends, betting lines, and team rankings context
(offense/defense total, passing, rushing, scoring — out of 32):

- "script": ~90-130 seconds, talks openly about moneyline/spread/totals.
- "script_tiktok": ~90-130 seconds, same substance but avoids gambling
  terminology (no "moneyline"/"spread"/"over-under") for platforms like
  TikTok that restrict gambling talk — favorite/underdog and high/low
  scoring framing instead, no raw odds numbers.

Writes one JSON file per game to output/scripts/<date>/<game_id>.json —
the same directory MLB writes into, since downstream steps (screenshots,
video assembly, YouTube upload, email) are already sport-agnostic and just
glob everything in that folder for the date.

Usage:
  venv/bin/python jobs/nfl_generate_trend_video_scripts.py [YYYY-MM-DD]

If no date is given, defaults to today in US/Eastern.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

import pytz
import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from api.services.game_service import GameService
from api.services.historical.nfl_trends_service import NFLTrendsService
from api.services.historical.trend_enrichment import enrich_game_trends
from api.services.historical.trend_scoring import rank_game_trends, get_confidence_score
from nfl_rankings import fetch_nfl_rankings

eastern_tz = pytz.timezone("US/Eastern")

MODEL = "claude-sonnet-5"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output" / "scripts"
REQUIRED_SCRIPT_KEYS = ("hook", "script", "primary_trend_type", "secondary_trends_referenced", "estimated_word_count")

# Independent of MLB's own cap — set MAX_VIDEO_GAMES_PER_DAY_NFL to change.
MAX_VIDEO_GAMES_PER_DAY = int(os.getenv("MAX_VIDEO_GAMES_PER_DAY_NFL", "3"))

SCRIPT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string", "description": "The opening 1-2 sentences, standalone (8-20 words). Single line, no newline characters."},
        "script": {"type": "string", "description": "The complete script including the hook (250-320 words), as one continuous paragraph of spoken prose. Do not include any newline or line-break characters — separate ideas with sentences and punctuation only."},
        "primary_trend_type": {"type": "string", "description": "The exact 'type' value of the trend the script is built around, copied verbatim from the given trend list."},
        "secondary_trends_referenced": {"type": "array", "items": {"type": "string"}, "description": "Exact 'type' values mentioned besides the primary, verbatim from the given trend list (empty array if none)."},
        "estimated_word_count": {"type": "integer", "description": "Word count of the 'script' field."},
    },
    "required": ["hook", "script", "primary_trend_type", "secondary_trends_referenced", "estimated_word_count"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a sports broadcast scriptwriter for GetSTAM, a sports betting trends platform. You write conversational, first-person spoken video scripts (90-130 seconds) for social media (TikTok/Reels/Shorts) that break down one upcoming NFL game the way a sharp, confident bettor would talk through their notes out loud — not like an ad, and not like a robotic stat recital.

Voice and structure:
- Open by naming the matchup, then work through both teams' recent form. It's fine — good, even — to note a bit of tension or nuance (e.g. one team's recent streak vs. what happened the last time these two played), the way a real analyst would say "pretty interesting" about a wrinkle in the data.
- Weave the betting lines (moneyline, spread, total) in naturally as you talk, not as a rattled-off list.
- If team rankings are provided (offense/defense — total, passing, rushing, scoring), spend real time on it — call out the specific ranks that matter for this matchup (e.g. a top-5 rushing offense against a bottom-10 run defense) and compare the two teams directly. This is often the most interesting part of the breakdown.
- Use casual, natural spoken phrasing: contractions, short reactions ("Pretty good.", "Interesting."), transitions like "If you look at..." or "But if you go back...". Sentence fragments are fine when they sound like real speech.
- Every trend comes with a confidence score (0-4) showing how often this exact pattern has historically held up — calibrate how sure you sound to match it, not just what you say. A 0-1 score means the historical rate is close to a coin flip (roughly 50-55%): say that plainly, and don't force a confident lean on the trend alone — either point to a different factor that actually tips it (a clear rankings mismatch, a lopsided line move) or be upfront that it's a genuine toss-up. A 2-3 score supports a real but moderate lean ("I'd favor," "I lean towards") — not a lock. A 3-4 score is a strong historical signal — be genuinely assertive there.
- Treat the primary trend as evidence to weigh, not an automatic pick — don't default to "the streak just continues." Sometimes the sharper read is that the trend is misleading given a stronger countervailing factor, and sometimes the honest take really is that it's close to 50/50.
- Close with ONE clear takeaway either way — even "this one's a genuine coin flip, but here's the tiebreaker" counts as a clear takeaway. Ground it only in the moneyline/spread/total actually given to you — never invent a market or number you weren't given. Show a bit of the reasoning rather than just asserting it — e.g. "history gives this about a 51% edge, close to a coin flip, but..." — so the confidence you project actually matches the strength of the signal.
- After the takeaway, invite engagement (e.g. ask viewers how they see the game going, in the comments).
- End with a short branded sign-off mentioning getstam.com and inviting a follow for more games — vary the phrasing naturally rather than repeating the exact same sentence every time.

Write the "script" field as one continuous paragraph — no line breaks or newline characters, ever. Never invent stats, records, ranks, or odds beyond what's given to you. No bullet points, no headers, no emoji, no hashtags — this is spoken word only."""

TIKTOK_SYSTEM_PROMPT = """You are a sports broadcast scriptwriter for GetSTAM, a sports betting trends platform. You write conversational, first-person spoken video scripts (90-130 seconds) for TikTok that break down one upcoming NFL game the way a sharp, confident fan would talk through their notes out loud — not like an ad, and not like a robotic stat recital.

TikTok restricts gambling content, so this version must stay strictly in plain sports-commentary language:
- Never use the words/phrases: "moneyline", "money line", "spread", "against the spread", "cover"/"covers", "over/under", "over-under", "total" (as a betting term), "bet", "betting", "wager", "odds", "line", "pick", "lean", "sportsbook", "gambling", "handicap".
- Instead: say a team is "favored" or "the underdog" (no odds numbers). Say a team's games have been "high-scoring" or "low-scoring" lately instead of talking about overs/unders. Never state a specific price, spread number, or total number — qualitative only.
- You may freely use team rankings (offense/defense — total, passing, rushing, scoring) — those are performance stats, not gambling terms.

Voice and structure:
- Open by naming the matchup, then work through both teams' recent form, including a bit of tension or nuance where it exists (e.g. a team is hot right now but has struggled specifically against this opponent).
- If team rankings are provided, spend real time on it — call out specific ranks that matter for this matchup and compare the two teams directly.
- Use casual, natural spoken phrasing: contractions, short reactions ("Pretty good.", "Interesting."), transitions like "If you look at..." or "But if you go back...". Sentence fragments are fine when they sound like real speech.
- Every trend comes with a confidence score (0-4) showing how often this exact pattern has historically held up — calibrate how sure you sound to match it. A 0-1 score means the historical rate is close to a coin flip (roughly 50-55%): say that plainly rather than forcing a confident prediction off a weak trend alone — point to a different factor that actually tips it (a clear rankings mismatch), or be upfront it's a genuine toss-up. A 2-3 score supports a real but moderate favor toward one side — not a lock. A 3-4 score is a strong historical signal — be genuinely assertive there.
- Treat the trend as evidence to weigh, not an automatic prediction — don't default to assuming a streak just continues. Sometimes the sharper read is that the trend is misleading given a stronger countervailing factor, and sometimes the honest take really is that it's close to 50/50.
- Close with ONE clear prediction on how the game goes (who wins, and whether you expect a high- or low-scoring game) either way — even "this one's a genuine toss-up, but here's the tiebreaker" counts as a clear prediction — framed as your read of the matchup, not as betting advice. Show a bit of the reasoning rather than just asserting it, so the confidence you project actually matches the strength of the signal.
- After the prediction, invite engagement (e.g. ask viewers how they see the game going, in the comments).
- End with a short branded sign-off mentioning getstam.com and inviting a follow for more games — vary the phrasing naturally rather than repeating the exact same sentence every time.

Write the "script" field as one continuous paragraph — no line breaks or newline characters, ever. Never invent stats, records, or ranks beyond what's given to you. No bullet points, no headers, no emoji, no hashtags — this is spoken word only."""

# Words/phrases that must never appear in the TikTok script, checked after generation
# as a safety net (the prompt already omits odds numbers and forbids this vocabulary,
# but the model could still slip since these are common English words in other senses).
_TIKTOK_BANNED_PATTERN = re.compile(
    r"\b(money\s*line|against the spread|spread|cover|covers|covering|over[\s/-]under|"
    r"bet|betting|bettor|wager|odds|sportsbook|gambling|handicap|pick'?em)\b",
    re.IGNORECASE,
)


def sanitize_trend_for_tiktok(trend):
    """Return a copy of trend with an over/under-free description.

    over_streak/under_streak descriptions (both the base text and the enriched
    historical-context suffix) contain literal "OVER"/"UNDER" wording. Reconstruct
    a clean sentence from the structured fields instead of scrubbing the prose.
    """
    if trend["type"] not in ("over_streak", "under_streak"):
        return trend

    sanitized = dict(trend)
    direction = "high-scoring" if trend["type"] == "over_streak" else "low-scoring"
    desc = f"This team's games have been {direction} lately — {trend['count']} straight"
    rate = trend.get("continuation_rate")
    if rate is not None:
        desc += f", and that pattern has continued about {round(rate * 100)}% of the time historically"
    sanitized["description"] = desc
    return sanitized


def _rankings_lines(team_name, rankings_for_team):
    if not rankings_for_team:
        return f"- {team_name}: no rankings data available"
    off = rankings_for_team.get("offense", {})
    dff = rankings_for_team.get("defense", {})

    def fmt(stats, prefix):
        parts = []
        for stat in ("Total", "Passing", "Rushing", "Scoring"):
            val = stats.get(stat)
            rank = stats.get(f"{stat} Rank")
            if val is not None and rank is not None:
                parts.append(f"{stat} {val} (#{rank})")
        return f"{prefix}: " + ", ".join(parts) if parts else f"{prefix}: no data"

    return f"- {team_name} {fmt(off, 'offense')}\n- {team_name} {fmt(dff, 'defense')}"


def build_rankings_section(game, rankings):
    home_name = game["home"]["team"]
    away_name = game["away"]["team"]
    home_r = rankings.get(home_name)
    away_r = rankings.get(away_name)
    if not home_r and not away_r:
        return "\nNo team rankings data available for this game — do not mention rankings.\n"
    return f"""
Team rankings context (out of 32 teams, higher rank number = worse):
{_rankings_lines(home_name, home_r)}
{_rankings_lines(away_name, away_r)}
"""


def build_user_prompt(game, ranked_trends, rankings):
    home = game["home"]
    away = game["away"]
    totals = game.get("totals") or {}

    trend_lines = "\n".join(
        f"{i}. [type: {t['type']}] [score {t['_score']}] {t['description']}"
        for i, t in enumerate(ranked_trends, start=1)
    )
    rankings_section = build_rankings_section(game, rankings)

    return f"""Upcoming NFL game: {away['team']} at {home['team']}, {game.get('commence_time')} ET.

Betting lines:
- Moneyline: {away['team']} {away['odds'].get('h2h')}, {home['team']} {home['odds'].get('h2h')}
- Spread: {home['team']} {home['odds'].get('spread_point')} ({home['odds'].get('spread_price')})
- Total: {totals.get('over_point')} (over {totals.get('over_price')} / under {totals.get('under_price')})
{rankings_section}
Ranked trends for this game (most significant first; confidence score 0-4, higher = stronger signal):
{trend_lines}

Write a 90-130 second spoken video script (target 250-320 words) that works through both teams' form, the rankings context (if given), and the betting lines, built primarily around trend #1 but free to reference others that add to the story. End with one clear betting takeaway grounded in the lines above, an invitation to comment, and a branded sign-off.

For "primary_trend_type" and "secondary_trends_referenced", copy the exact "type:" values verbatim from the trend list above — do not paraphrase them."""


def _favorite_underdog_line(game):
    home = game["home"]
    away = game["away"]
    home_ml = (home.get("odds") or {}).get("h2h")
    away_ml = (away.get("odds") or {}).get("h2h")
    if home_ml is None or away_ml is None:
        return "No favorite/underdog information available."
    favorite, underdog = (home["team"], away["team"]) if home_ml < away_ml else (away["team"], home["team"])
    return f"{favorite} is favored tonight; {underdog} is the underdog. Do not state odds numbers or prices."


def build_tiktok_user_prompt(game, ranked_trends, rankings):
    sanitized_trends = [sanitize_trend_for_tiktok(t) for t in ranked_trends]
    trend_lines = "\n".join(
        f"{i}. [type: {t['type']}] [score {t['_score']}] {t['description']}"
        for i, t in enumerate(sanitized_trends, start=1)
    )
    rankings_section = build_rankings_section(game, rankings)

    return f"""Upcoming NFL game: {game['away']['team']} at {game['home']['team']}, {game.get('commence_time')} ET.

{_favorite_underdog_line(game)}
{rankings_section}
Ranked trends for this game (most significant first; confidence score 0-4, higher = stronger signal):
{trend_lines}

Write a 90-130 second spoken video script (target 250-320 words) that works through both teams' form and the rankings context (if given), built primarily around trend #1 but free to reference others that add to the story. End with one clear prediction (who wins, high- or low-scoring), an invitation to comment, and a branded sign-off. Remember: no gambling terminology, no odds numbers.

For "primary_trend_type" and "secondary_trends_referenced", copy the exact "type:" values verbatim from the trend list above — do not paraphrase them."""


def _generate_script(system_prompt, prompt, valid_types, banned_pattern=None):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            thinking={"type": "disabled"},
            output_config={"format": {"type": "json_schema", "schema": SCRIPT_JSON_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        return None, str(e)

    text_block = next((b for b in message.content if b.type == "text"), None)
    if text_block is None:
        return None, "Claude response contained no text block"
    text = text_block.text

    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None, "Claude response was not valid JSON"
        try:
            data = json.loads(match.group(0), strict=False)
        except json.JSONDecodeError as e:
            return None, f"Claude response was not valid JSON: {e}"

    for key in ("hook", "script"):
        if isinstance(data.get(key), str):
            data[key] = re.sub(r"\s*[\r\n]+\s*", " ", data[key]).strip()

    missing = [k for k in REQUIRED_SCRIPT_KEYS if k not in data]
    if missing:
        return None, f"Claude response missing required key(s): {missing}"

    if data["primary_trend_type"] not in valid_types:
        return None, f"primary_trend_type {data['primary_trend_type']!r} did not match any given trend type {valid_types}"

    if banned_pattern is not None:
        hit = banned_pattern.search(data["script"]) or banned_pattern.search(data["hook"])
        if hit:
            return None, f"Script contained banned gambling term: {hit.group(0)!r}"

    return data, None


def call_claude(game, ranked_trends, rankings):
    prompt = build_user_prompt(game, ranked_trends, rankings)
    valid_types = {t["type"] for t in ranked_trends}
    return _generate_script(SYSTEM_PROMPT, prompt, valid_types)


def call_claude_tiktok(game, ranked_trends, rankings):
    prompt = build_tiktok_user_prompt(game, ranked_trends, rankings)
    valid_types = {t["type"] for t in ranked_trends}
    return _generate_script(TIKTOK_SYSTEM_PROMPT, prompt, valid_types, banned_pattern=_TIKTOK_BANNED_PATTERN)


def write_output_file(date_str, game_id, payload):
    out_dir = OUTPUT_ROOT / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{game_id}.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return out_path


def run(date_str=None):
    if not date_str:
        date_str = datetime.now(eastern_tz).strftime("%Y-%m-%d")

    print(f"Fetching NFL games for {date_str}...")
    result, err = GameService.get_games_for_date("americanfootball_nfl", date_str)
    if err:
        print(f"Error fetching games: {err}")
        return
    games = (result or {}).get("games", [])
    print(f"Found {len(games)} games.")
    if not games:
        return

    trend_results, err = NFLTrendsService.analyze_multiple_games_trends(games, limit=20, min_trend_length=3)
    if err:
        print(f"Error analyzing trends: {err}")
        return
    trend_results = enrich_game_trends(trend_results, "nfl")

    todays_trend_games = [r for r in trend_results if not r["game"]["completed"] and r["hasTrends"]]
    print(f"{len(todays_trend_games)} game(s) have active trends for Today's Trends.")
    if not todays_trend_games:
        return

    for entry in todays_trend_games:
        ranked = rank_game_trends(entry)
        entry["_top_trend_score"] = get_confidence_score(ranked[0]) if ranked else 0
    todays_trend_games.sort(key=lambda e: e["_top_trend_score"], reverse=True)
    if len(todays_trend_games) > MAX_VIDEO_GAMES_PER_DAY:
        print(
            f"Limiting to the top {MAX_VIDEO_GAMES_PER_DAY} game(s) by trend strength "
            f"(of {len(todays_trend_games)}) — set MAX_VIDEO_GAMES_PER_DAY_NFL to change this."
        )
        todays_trend_games = todays_trend_games[:MAX_VIDEO_GAMES_PER_DAY]

    try:
        rankings = fetch_nfl_rankings()
        # fetch_nfl_rankings() returns raw ESPN stat keys like "Total (Yds/G)"
        # / "Total (Yds/G) Rank" — strip the units suffix so they match what
        # _rankings_lines() looks up ("Total" / "Total Rank"), same cleanup
        # api/external_requests/espn.py does for the site's own API response.
        def _clean_stats(stats):
            return {
                key.replace(" (Yds/G)", "").replace(" (Pts/G)", ""): value
                for key, value in stats.items()
            }

        # Reshape to {team_name: {"offense": {...}, "defense": {...}}}, matching
        # what build_rankings_section expects (fetch_nfl_rankings returns two
        # separate top-level dicts keyed by team name/abbreviation).
        offense = rankings.get("offense", {})
        defense = rankings.get("defense", {})
        rankings_by_team = {
            name: {"offense": _clean_stats(offense.get(name, {})), "defense": _clean_stats(defense.get(name, {}))}
            for name in offense.keys()
        }
    except Exception as e:
        print(f"Warning: could not fetch NFL rankings ({e}); continuing without them.")
        rankings_by_team = {}

    games_processed = 0
    scripts_generated = 0
    scripts_failed = 0
    tiktok_generated = 0
    tiktok_failed = 0

    for entry in todays_trend_games:
        game = entry["game"]
        game_id = game["game_id"]
        games_processed += 1

        try:
            ranked = rank_game_trends(entry)
            top_trends = ranked[:5]
            for t in top_trends:
                t["_score"] = round(get_confidence_score(t), 1)

            script_data, gen_err = call_claude(game, top_trends, rankings_by_team)
            tiktok_data, tiktok_err = call_claude_tiktok(game, top_trends, rankings_by_team)

            payload = {
                "job": "nfl_generate_trend_video_scripts",
                "generated_at": datetime.now(eastern_tz).isoformat(),
                "sport": "nfl",
                "date": date_str,
                "game_id": game_id,
                "matchup": {
                    "away_team": game["away"]["team"],
                    "home_team": game["home"]["team"],
                    "commence_time": game.get("commence_time"),
                },
                "odds": {"home": game["home"]["odds"], "away": game["away"]["odds"], "totals": game.get("totals")},
                "trends_considered": top_trends,
                "primary_trend": top_trends[0] if top_trends else None,
                "rankings": {
                    "home": rankings_by_team.get(game["home"]["team"]),
                    "away": rankings_by_team.get(game["away"]["team"]),
                },
                "model": MODEL,
                "script": script_data,
                "generation_error": gen_err,
                "script_tiktok": tiktok_data,
                "generation_error_tiktok": tiktok_err,
            }

            out_path = write_output_file(date_str, game_id, payload)

            label = f"{game['away']['team']} @ {game['home']['team']}"
            if gen_err:
                scripts_failed += 1
                print(f"  [FAILED] {label}: {gen_err} -> {out_path}")
            else:
                scripts_generated += 1
                print(f"  [OK] {label} -> {out_path}")

            if tiktok_err:
                tiktok_failed += 1
                print(f"  [TIKTOK FAILED] {label}: {tiktok_err}")
            else:
                tiktok_generated += 1
                print(f"  [TIKTOK OK] {label}")

        except Exception as e:
            scripts_failed += 1
            tiktok_failed += 1
            print(f"  [ERROR] game_id={game_id}: {e}")
            try:
                write_output_file(date_str, game_id, {
                    "job": "nfl_generate_trend_video_scripts",
                    "generated_at": datetime.now(eastern_tz).isoformat(),
                    "sport": "nfl",
                    "date": date_str,
                    "game_id": game_id,
                    "script": None,
                    "generation_error": str(e),
                    "script_tiktok": None,
                    "generation_error_tiktok": str(e),
                })
            except Exception:
                pass
            continue

    print(
        f"\nDone. games_processed={games_processed} "
        f"scripts_generated={scripts_generated} scripts_failed={scripts_failed} "
        f"tiktok_generated={tiktok_generated} tiktok_failed={tiktok_failed}"
    )


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
