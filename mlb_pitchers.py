import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

def get_starting_pitchers():
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    games = soup.find_all("div", class_="lineup")

    print(f"\n🛠️ Found {len(games)} games on the page")

    data = []

    for game in games:
        teams = game.find_all("div", class_="lineup__abbr")
        if len(teams) != 2:
            print("❌ Skipping game: Team data is missing")
            continue

        away_team = teams[0].text.strip()
        home_team = teams[1].text.strip()

        print(f"🏟️ Extracted Teams: {away_team} @ {home_team}")

        # Get pitcher name divs
        name_divs = game.find_all("div", class_="lineup__player-highlight-name")
        stats_divs = game.find_all("div", class_="lineup__player-highlight-stats")

        if len(name_divs) < 2 or len(stats_divs) < 2:
            print("❌ Skipping game: Pitcher data is missing")
            continue

        # Extract pitcher names
        away_pitcher = name_divs[0].get_text(strip=True, separator=' ')
        home_pitcher = name_divs[1].get_text(strip=True, separator=' ')

        # Extract pitcher stats
        away_stats = stats_divs[0].text.strip().replace("\xa0", " ")
        home_stats = stats_divs[1].text.strip().replace("\xa0", " ")

        print(f"  ⚾ Away Pitcher: {away_pitcher} ({away_stats})")
        print(f"  ⚾ Home Pitcher: {home_pitcher} ({home_stats})")

        game_data = {
            "date": datetime.today().strftime("%Y-%m-%d"),
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_pitcher,
            "away_pitcher_stats": away_stats,
            "home_pitcher": home_pitcher,
            "home_pitcher_stats": home_stats,
        }

        data.append(game_data)

    

    # Save to JSON
    with open("mlb_starting_pitchers.json", "w") as f:
        json.dump(data, f, indent=4)

    return data

if __name__ == "__main__":
    data = get_starting_pitchers()
    print("\n✅ Scraped Data for Today's MLB Games:\n")
    for game in data:
        print(game)