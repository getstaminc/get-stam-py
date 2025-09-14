from flask import Blueprint, jsonify
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from cache import cache

mlb_pitchers_bp = Blueprint('mlb_pitchers', __name__)

@mlb_pitchers_bp.route('/api/mlb/pitchers', methods=['GET'])
@cache.cached(timeout=3600)
def get_pitcher_data_for_dates():
    print("🚨 CACHE MISS: Fetching pitcher data from rotowire.com")
    urls = {
        "today": "https://www.rotowire.com/baseball/daily-lineups.php",
        "tomorrow": "https://www.rotowire.com/baseball/daily-lineups.php?date=tomorrow"
    }

    results = {}

    for label, url in urls.items():
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        # Get the actual date from the page
        date_div = soup.find("div", class_="page-title__secondary")
        if not date_div or "lineups for" not in date_div.text.lower():
            continue
        page_date_str = date_div.text.strip().split("for")[-1].strip()
        page_date = datetime.strptime(page_date_str, "%B %d, %Y").strftime("%Y-%m-%d")

        games = soup.find_all("div", class_="lineup")
        data = []

        for game in games:
            teams = game.find_all("div", class_="lineup__abbr")
            if len(teams) != 2:
                continue

            away_team = teams[0].text.strip()
            home_team = teams[1].text.strip()

            name_divs = game.find_all("div", class_="lineup__player-highlight-name")
            stats_divs = game.find_all("div", class_="lineup__player-highlight-stats")

            if len(name_divs) < 2 or len(stats_divs) < 2:
                continue

            data.append({
                "away_team": away_team,
                "home_team": home_team,
                "away_pitcher": name_divs[0].get_text(strip=True, separator=" "),
                "home_pitcher": name_divs[1].get_text(strip=True, separator=" "),
                "away_pitcher_stats": stats_divs[0].text.strip().replace("\xa0", " "),
                "home_pitcher_stats": stats_divs[1].text.strip().replace("\xa0", " "),
            })

        results[page_date] = data

    return jsonify(results)
