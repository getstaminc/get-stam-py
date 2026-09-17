# nfl_rankings.py

import requests
import pandas as pd

def fetch_nfl_rankings():
    offense_url = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/statistics/byteam"
    defense_url = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/statistics/byteam"

    offense_params = {
        "region": "us", "lang": "en", "contentorigin": "espn",
        "sort": "team.passing.netYardsPerGame:desc", "limit": 32
    }

    defense_params = {
        "region": "us", "lang": "en", "contentorigin": "espn",
        "sort": "opponent.passing.netYardsPerGame:asc", "limit": 32
    }

    # Offense stat config
    OFFENSE_CONFIG = {
        "Total (Yds/G)": {"section": "passing", "total_index": 12, "rank_index": 12},
        "Passing (Yds/G)": {"section": "passing", "total_index": 3, "rank_index": 3},
        "Rushing (Yds/G)": {"section": "rushing", "total_index": 1, "rank_index": 1},
        "Scoring (Pts/G)": {"section": "passing", "total_index": 5, "rank_index": 5},
    }

    # Defense stat config. No rank_index here: ESPN's "ranks" array for the
    # opponent split ranks the raw number the same way it would for an offensive
    # stat (higher = rank 1), which is backwards for yards/points *allowed* --
    # fewer allowed should be rank 1. We compute our own ascending rank instead
    # (see parse_defense).
    DEFENSE_CONFIG = {
        "Total (Yds/G)": {"section": "passing", "total_index": 12},
        "Passing (Yds/G)": {"section": "passing", "total_index": 3},
        "Rushing (Yds/G)": {"section": "rushing", "total_index": 1},
        "Scoring (Pts/G)": {"section": "passing", "total_index": 5},
    }

    def parse_offense(data):
        team_stats = {}
        for team in data.get("teams", []):
            name = team["team"]["displayName"]
            abbr = team["team"]["abbreviation"]
            row = {}
            categories = {
                c["name"]: c
                for c in team.get("categories", [])
                if c.get("splitId") == "0"
            }
            for label, cfg in OFFENSE_CONFIG.items():
                cat = categories.get(cfg["section"])
                if cat:
                    row[label] = cat.get("totals", [None]*20)[cfg["total_index"]]
                    row[f"{label} Rank"] = cat.get("ranks", [None]*20)[cfg["rank_index"]]
            team_stats[name] = row
            team_stats[abbr] = row
        return team_stats

    def parse_defense(data):
        # Pull each team's raw "allowed" totals from the opponent split (900) --
        # this is the team's own defensive performance, e.g. passing yards
        # allowed rather than passing yards gained.
        rows = []
        for team in data.get("teams", []):
            name = team["team"]["displayName"]
            abbr = team["team"]["abbreviation"]
            categories = {
                c["name"]: c
                for c in team.get("categories", [])
                if c.get("splitId") == "900"
            }
            row = {"__name": name, "__abbr": abbr}
            for label, cfg in DEFENSE_CONFIG.items():
                section = categories.get(cfg["section"])
                totals = section.get("totals", []) if section else []
                value = totals[cfg["total_index"]] if len(totals) > cfg["total_index"] else None
                row[label] = float(value) if value is not None else None
            rows.append(row)

        df = pd.DataFrame(rows)

        # Fewer yards/points allowed is better, so rank ascending. Ties share the
        # lower rank (matches ESPN's own competition-ranking convention).
        for label in DEFENSE_CONFIG:
            df[f"{label} Rank"] = df[label].rank(method="min", ascending=True)

        team_stats = {}
        for _, r in df.iterrows():
            row = {}
            for label in DEFENSE_CONFIG:
                row[label] = r[label]
                rank = r[f"{label} Rank"]
                row[f"{label} Rank"] = int(rank) if pd.notna(rank) else None
            team_stats[r["__name"]] = row
            team_stats[r["__abbr"]] = row
        return team_stats

    # Fetch both datasets
    offense_data = requests.get(offense_url, params=offense_params).json()
    defense_data = requests.get(defense_url, params=defense_params).json()

    return {
        "offense": parse_offense(offense_data),
        "defense": parse_defense(defense_data),
    }