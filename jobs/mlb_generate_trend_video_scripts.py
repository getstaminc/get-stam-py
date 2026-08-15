"""
MLB Trend Video Script Generator

For every MLB game that would appear on the homepage's "Today's Trends"
section (not completed, hasTrends), calls Claude to write two spoken video
scripts covering the game's trends, betting lines, and starting pitching
matchup (when available):

- "script": ~90-130 seconds, talks openly about moneyline/spread/totals.
- "script_tiktok": ~90-130 seconds, same substance but avoids gambling
  terminology (no "moneyline"/"spread"/"over-under") for platforms like
  TikTok that restrict gambling talk — favorite/underdog and high/low
  scoring framing instead, no raw odds numbers.

Writes one JSON file per game to output/scripts/<date>/<game_id>.json.

Usage:
  venv/bin/python jobs/mlb_generate_trend_video_scripts.py [YYYY-MM-DD]

If no date is given, defaults to today in US/Eastern. Starting pitcher data
is only available for today/tomorrow (scraped live from RotoWire), so games
on other dates will generate without a pitching-matchup section.
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
from api.services.historical.mlb_trends_service import MLBTrendsService
from api.services.historical.trend_enrichment import enrich_game_trends
from api.services.historical.trend_scoring import rank_game_trends, get_confidence_score
from shared_utils import convert_roto_team_names
from mlb_pitchers import get_pitcher_data_for_dates

eastern_tz = pytz.timezone("US/Eastern")

MODEL = "claude-sonnet-5"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output" / "scripts"
REQUIRED_SCRIPT_KEYS = ("hook", "script", "primary_trend_type", "secondary_trends_referenced", "estimated_word_count")

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

SYSTEM_PROMPT = """You are a sports broadcast scriptwriter for GetSTAM, a sports betting trends platform. You write conversational, first-person spoken video scripts (90-130 seconds) for social media (TikTok/Reels/Shorts) that break down one upcoming MLB game the way a sharp, confident bettor would talk through their notes out loud — not like an ad, and not like a robotic stat recital.

Voice and structure:
- Open by naming the matchup, then work through both teams' recent form. It's fine — good, even — to note a bit of tension or nuance (e.g. one team's recent streak vs. what happened the last time these two played), the way a real analyst would say "pretty interesting" about a wrinkle in the data.
- Weave the betting lines (moneyline, spread, total) in naturally as you talk, not as a rattled-off list.
- If a starting pitching matchup is provided, spend real time on it — name both pitchers, give their record/ERA, and compare them directly. This is often the most interesting part of the breakdown.
- Use casual, natural spoken phrasing: contractions, short reactions ("Pretty good.", "Interesting."), transitions like "If you look at..." or "But if you go back...". Sentence fragments are fine when they sound like real speech.
- Close with ONE clear, specific betting takeaway, grounded only in the moneyline/spread/total actually given to you — never invent a market or number you weren't given.
- After the takeaway, invite engagement (e.g. ask viewers how they see the game going, in the comments).
- End with a short branded sign-off mentioning getstam.com and inviting a follow for more games — vary the phrasing naturally rather than repeating the exact same sentence every time.

Write the "script" field as one continuous paragraph — no line breaks or newline characters, ever. Never invent stats, records, or odds beyond what's given to you. No bullet points, no headers, no emoji, no hashtags — this is spoken word only."""

TIKTOK_SYSTEM_PROMPT = """You are a sports broadcast scriptwriter for GetSTAM, a sports betting trends platform. You write conversational, first-person spoken video scripts (90-130 seconds) for TikTok that break down one upcoming MLB game the way a sharp, confident fan would talk through their notes out loud — not like an ad, and not like a robotic stat recital.

TikTok restricts gambling content, so this version must stay strictly in plain sports-commentary language:
- Never use the words/phrases: "moneyline", "money line", "spread", "against the spread", "cover"/"covers", "over/under", "over-under", "total" (as a betting term), "bet", "betting", "wager", "odds", "line", "pick", "lean", "sportsbook", "gambling", "handicap".
- Instead: say a team is "favored" or "the underdog" (no odds numbers). Say a team's games have been "high-scoring" or "low-scoring" lately instead of talking about overs/unders. Never state a specific price, spread number, or total number — qualitative only.
- You may freely use pitcher stats (record, ERA) — those are performance stats, not gambling terms.

Voice and structure:
- Open by naming the matchup, then work through both teams' recent form, including a bit of tension or nuance where it exists (e.g. a team is hot right now but has struggled specifically against this opponent).
- If a starting pitching matchup is provided, spend real time on it — name both pitchers, give their record/ERA, and compare them directly.
- Use casual, natural spoken phrasing: contractions, short reactions ("Pretty good.", "Interesting."), transitions like "If you look at..." or "But if you go back...". Sentence fragments are fine when they sound like real speech.
- Close with ONE clear prediction on how the game goes (who wins, and whether you expect a high- or low-scoring game), framed as your read of the matchup — not as betting advice.
- After the prediction, invite engagement (e.g. ask viewers how they see the game going, in the comments).
- End with a short branded sign-off mentioning getstam.com and inviting a follow for more games — vary the phrasing naturally rather than repeating the exact same sentence every time.

Write the "script" field as one continuous paragraph — no line breaks or newline characters, ever. Never invent stats or records beyond what's given to you. No bullet points, no headers, no emoji, no hashtags — this is spoken word only."""

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
    historical-context suffix) contain literal "OVER"/"UNDER" wording — see
    trend_enrichment.py's _enrich_desc and trend_context_service.py's
    get_streak_context. Reconstruct a clean sentence from the structured
    fields instead of trying to scrub the existing prose.
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


def build_user_prompt(game, ranked_trends, pitcher_matchup):
    home = game["home"]
    away = game["away"]
    totals = game.get("totals") or {}

    trend_lines = "\n".join(
        f"{i}. [type: {t['type']}] [score {t['_score']}] {t['description']}"
        for i, t in enumerate(ranked_trends, start=1)
    )

    if pitcher_matchup:
        pitching_section = f"""
Starting pitching matchup:
- {away['team']}: {pitcher_matchup['away_pitcher']} ({pitcher_matchup['away_pitcher_stats']})
- {home['team']}: {pitcher_matchup['home_pitcher']} ({pitcher_matchup['home_pitcher_stats']})
"""
    else:
        pitching_section = "\nNo starting pitching data available for this game — do not mention pitchers.\n"

    return f"""Upcoming MLB game: {away['team']} at {home['team']}, {game.get('commence_time')} ET.

Betting lines:
- Moneyline: {away['team']} {away['odds'].get('h2h')}, {home['team']} {home['odds'].get('h2h')}
- Spread: {home['team']} {home['odds'].get('spread_point')} ({home['odds'].get('spread_price')})
- Total: {totals.get('over_point')} (over {totals.get('over_price')} / under {totals.get('under_price')})
{pitching_section}
Ranked trends for this game (most significant first; confidence score 0-4, higher = stronger signal):
{trend_lines}

Write a 90-130 second spoken video script (target 250-320 words) that works through both teams' form, the pitching matchup (if given), and the betting lines, built primarily around trend #1 but free to reference others that add to the story. End with one clear betting takeaway grounded in the lines above, an invitation to comment, and a branded sign-off.

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


def build_tiktok_user_prompt(game, ranked_trends, pitcher_matchup):
    home = game["home"]
    away = game["away"]

    sanitized_trends = [sanitize_trend_for_tiktok(t) for t in ranked_trends]
    trend_lines = "\n".join(
        f"{i}. [type: {t['type']}] [score {t['_score']}] {t['description']}"
        for i, t in enumerate(sanitized_trends, start=1)
    )

    if pitcher_matchup:
        pitching_section = f"""
Starting pitching matchup:
- {away['team']}: {pitcher_matchup['away_pitcher']} ({pitcher_matchup['away_pitcher_stats']})
- {home['team']}: {pitcher_matchup['home_pitcher']} ({pitcher_matchup['home_pitcher_stats']})
"""
    else:
        pitching_section = "\nNo starting pitching data available for this game — do not mention pitchers.\n"

    return f"""Upcoming MLB game: {away['team']} at {home['team']}, {game.get('commence_time')} ET.

{_favorite_underdog_line(game)}
{pitching_section}
Ranked trends for this game (most significant first; confidence score 0-4, higher = stronger signal):
{trend_lines}

Write a 90-130 second spoken video script (target 250-320 words) that works through both teams' form and the pitching matchup (if given), built primarily around trend #1 but free to reference others that add to the story. End with one clear prediction (who wins, high- or low-scoring), an invitation to comment, and a branded sign-off. Remember: no gambling terminology, no odds numbers.

For "primary_trend_type" and "secondary_trends_referenced", copy the exact "type:" values verbatim from the trend list above — do not paraphrase them."""


def find_pitcher_matchup(game, pitcher_data_for_date):
    if not pitcher_data_for_date:
        return None
    home_abbr = convert_roto_team_names(game["home"]["team"])
    away_abbr = convert_roto_team_names(game["away"]["team"])
    for entry in pitcher_data_for_date:
        if entry.get("home_team") == home_abbr and entry.get("away_team") == away_abbr:
            return entry
    return None


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

    # strict=False: Claude's "script" text often contains literal newlines
    # between spoken "paragraphs", which are control characters that strict
    # JSON parsing rejects inside string values.
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

    # Backstop: structured-output mode has occasionally produced garbled text
    # right at embedded-newline boundaries in long string fields (e.g. a lost
    # backslash leaving a stray "n" or "//" mid-sentence). The prompt now asks
    # for single-paragraph text with no newlines; normalize here in case any
    # slip through anyway.
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


def call_claude(game, ranked_trends, pitcher_matchup):
    prompt = build_user_prompt(game, ranked_trends, pitcher_matchup)
    valid_types = {t["type"] for t in ranked_trends}
    return _generate_script(SYSTEM_PROMPT, prompt, valid_types)


def call_claude_tiktok(game, ranked_trends, pitcher_matchup):
    prompt = build_tiktok_user_prompt(game, ranked_trends, pitcher_matchup)
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

    print(f"Fetching MLB games for {date_str}...")
    result, err = GameService.get_games_for_date("baseball_mlb", date_str)
    if err:
        print(f"Error fetching games: {err}")
        return
    games = (result or {}).get("games", [])
    print(f"Found {len(games)} games.")

    trend_results, err = MLBTrendsService.analyze_multiple_games_trends(games, limit=20, min_trend_length=5)
    if err:
        print(f"Error analyzing trends: {err}")
        return
    trend_results = enrich_game_trends(trend_results, "mlb")

    todays_trend_games = [r for r in trend_results if not r["game"]["completed"] and r["hasTrends"]]
    print(f"{len(todays_trend_games)} game(s) have active trends for Today's Trends.")

    try:
        pitcher_data_by_date = get_pitcher_data_for_dates()
    except Exception as e:
        print(f"Warning: could not fetch pitcher data ({e}); continuing without it.")
        pitcher_data_by_date = {}
    pitcher_data_for_date = pitcher_data_by_date.get(date_str, [])

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

            pitcher_matchup = find_pitcher_matchup(game, pitcher_data_for_date)
            script_data, gen_err = call_claude(game, top_trends, pitcher_matchup)
            tiktok_data, tiktok_err = call_claude_tiktok(game, top_trends, pitcher_matchup)

            payload = {
                "job": "mlb_generate_trend_video_scripts",
                "generated_at": datetime.now(eastern_tz).isoformat(),
                "sport": "mlb",
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
                "pitcher_matchup": pitcher_matchup,
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
                    "job": "mlb_generate_trend_video_scripts",
                    "generated_at": datetime.now(eastern_tz).isoformat(),
                    "sport": "mlb",
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
