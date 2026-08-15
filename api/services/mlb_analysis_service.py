"""MLB Analysis Service — AI-written "GET STAM Analysis" for a single matchup, built from team-level trends."""

import os
import re
import json
import logging
from datetime import datetime, timezone

import anthropic

from .game_data_service import fetch_game_data

logger = logging.getLogger(__name__)


def _team_side(game, team_name):
    """Best-effort determination of whether team_name was home or away in a game row."""
    home = (game.get('home_team_name') or '').lower()
    away = (game.get('away_team_name') or '').lower()
    team = (team_name or '').lower()
    if team in home or home in team:
        return 'home'
    if team in away or away in team:
        return 'away'
    return None


def _summarize_record(games, team_name):
    """Summarize a list of game rows into a W-L record string and recent results line."""
    if not games:
        return "no recent games on file", []

    wins = 0
    losses = 0
    results = []
    for g in games:
        side = _team_side(g, team_name)
        if side is None:
            continue
        team_runs = g.get('home_runs') if side == 'home' else g.get('away_runs')
        opp_runs = g.get('away_runs') if side == 'home' else g.get('home_runs')
        if team_runs is None or opp_runs is None:
            continue
        if team_runs > opp_runs:
            wins += 1
            results.append(f"W {team_runs}-{opp_runs}")
        elif team_runs < opp_runs:
            losses += 1
            results.append(f"L {team_runs}-{opp_runs}")
        else:
            results.append(f"T {team_runs}-{opp_runs}")

    return f"{wins}-{losses}", results


def _summarize_trends(trends):
    """Flatten the trends dict (as returned by MLBTrendsService) into a list of description strings."""
    if not trends:
        return []

    lines = []
    sections = [
        ('homeTeamTrends', 'Home team'),
        ('awayTeamTrends', 'Away team'),
        ('homeTeamHomeTrends', 'Home team (at home)'),
        ('awayTeamAwayTrends', 'Away team (on the road)'),
        ('headToHeadTrends', 'Head-to-head'),
        ('homeAtHomeH2HTrends', 'Head-to-head (home team hosting)'),
    ]
    for key, label in sections:
        for trend in trends.get(key) or []:
            desc = trend.get('description')
            if desc:
                lines.append(f"{label}: {desc}")

    return lines


def _build_prompt(home_team, away_team, game_date_used, game_data):
    home_record, home_results = _summarize_record(game_data.get('home_last_5'), home_team)
    away_record, away_results = _summarize_record(game_data.get('away_last_5'), away_team)
    home_home_record, _ = _summarize_record(game_data.get('home_home_last_5'), home_team)
    away_away_record, _ = _summarize_record(game_data.get('away_away_last_5'), away_team)
    h2h_record, h2h_results = _summarize_record(game_data.get('h2h_last_5'), home_team)
    trend_lines = _summarize_trends(game_data.get('trends'))

    trends_section = "\n".join(f"- {line}" for line in trend_lines) or "- No active streak trends on file."

    return f"""You are writing a "GET STAM Analysis" for GetSTAM.com — a short, sharp written breakdown of an upcoming MLB game for bettors, based ONLY on the team-level historical data below. Do not invent stats, injuries, pitchers, or anything not given here.

## Matchup
{away_team} @ {home_team} — {game_date_used}

## Recent Form
- {home_team} last 5 games overall: {home_record} ({', '.join(home_results) or 'no data'})
- {away_team} last 5 games overall: {away_record} ({', '.join(away_results) or 'no data'})
- {home_team} last 5 at home: {home_home_record}
- {away_team} last 5 on the road: {away_away_record}

## Head-to-Head (last 5 meetings, from {home_team}'s perspective)
- Record: {h2h_record} ({', '.join(h2h_results) or 'no data'})

## Active Trends
{trends_section}

## Instructions
Write a 2-4 paragraph analysis in GetSTAM's voice — direct, bettor-focused, no fluff — covering recent form, any notable streaks, and head-to-head tendencies. End with a one-sentence plain-language lean (e.g. which side the data leans toward, or "no clear edge" if the data doesn't support one). Do not fabricate a pick with false confidence if the data is thin.

Return ONLY valid JSON (no markdown code fences) with these exact keys:
- "analysis": the full written analysis as plain Markdown (paragraphs only, no headers)
- "lean": the one-sentence lean, as plain text
"""


def _call_claude(prompt):
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                return None, "Claude response was not valid JSON"
            result = json.loads(match.group(0))

        return result, None
    except Exception as e:
        logger.error("_call_claude error: %s", e)
        return None, str(e)


class MLBAnalysisService:
    @staticmethod
    def generate_analysis(home_team, away_team, game_date=None):
        """Generate a GET STAM analysis for an MLB matchup. Returns (result_dict, error)."""
        game_data, odds_event_id, game_date_used, err = fetch_game_data(
            "mlb", "baseball_mlb", home_team, away_team, game_date
        )
        if err:
            return None, err

        prompt = _build_prompt(home_team, away_team, game_date_used, game_data)
        claude_output, err = _call_claude(prompt)
        if err:
            return None, err

        return {
            "home_team": home_team,
            "away_team": away_team,
            "game_date": game_date_used,
            "odds_event_id": odds_event_id,
            "analysis": claude_output.get("analysis"),
            "lean": claude_output.get("lean"),
            "game_data": game_data,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, None
