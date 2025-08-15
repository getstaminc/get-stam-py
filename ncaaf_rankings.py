# nfl_rankings.py

import requests
import pandas as pd

def fetch_ncaaf_rankings():
    offense_url = "https://site.web.api.espn.com/apis/common/v3/sports/football/college-football/statistics/byteam"
    defense_url = "https://site.web.api.espn.com/apis/common/v3/sports/football/college-football/statistics/byteam"

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
        "Total (Yds/G)": {"section": "passing", "total_index": 16, "rank_index": 16},
        "Passing (Yds/G)": {"section": "passing", "total_index": 17, "rank_index": 17},
        "Rushing (Yds/G)": {"section": "rushing", "total_index": 3, "rank_index": 3},
        "Scoring (Pts/G)": {"section": "passing", "total_index": 5, "rank_index": 5},
    }

    # Defense stat config
    DEFENSE_CONFIG = {
        "Total (Yds/G)": {"section": "passing", "total_index": 16, "rank_index": 16},
        "Passing (Yds/G)": {"section": "passing", "total_index": 3, "rank_index": 3},
        "Rushing (Yds/G)": {"section": "rushing", "total_index": 3, "rank_index": 3},
        "Scoring (Pts/G)": {"section": "passing", "total_index": 5, "rank_index": 5},
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
        team_stats = {}
        for team in data.get("teams", []):
            name = team["team"]["displayName"]
            abbr = team["team"]["abbreviation"]
            row = {}
            categories = {c["name"]: c for c in team.get("categories", [])}
            for label, cfg in DEFENSE_CONFIG.items():
                section = categories.get(cfg["section"])
                if section:
                    totals = section.get("totals", [])
                    ranks = section.get("ranks", [])
                    row[label] = totals[cfg["total_index"]] if len(totals) > cfg["total_index"] else None
                    row[f"{label} Rank"] = ranks[cfg["rank_index"]] if len(ranks) > cfg["rank_index"] else None
            team_stats[name] = row
            team_stats[abbr] = row
        return team_stats

    # Fetch both datasets
    offense_data = requests.get(offense_url, params=offense_params).json()
    defense_data = requests.get(defense_url, params=defense_params).json()

    return {
        "offense": parse_offense(offense_data),
        "defense": parse_defense(defense_data),
    }