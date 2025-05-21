import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def fetch_pitcher_data_from_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the date from the page
    date_div = soup.find("div", class_="page-title__secondary")
    if not date_div or "lineups for" not in date_div.text:
        raise ValueError("Could not extract date from page")

    page_date_str = date_div.text.strip().split("for")[-1].strip()  # e.g., "May 19, 2025"
    page_date = datetime.strptime(page_date_str, "%B %d, %Y").date()

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

        away_pitcher = name_divs[0].get_text(strip=True, separator=' ')
        home_pitcher = name_divs[1].get_text(strip=True, separator=' ')
        away_stats = stats_divs[0].text.strip().replace("\xa0", " ")
        home_stats = stats_divs[1].text.strip().replace("\xa0", " ")

        game_data = {
            "date": page_date.strftime("%Y-%m-%d"),
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_pitcher,
            "away_pitcher_stats": away_stats,
            "home_pitcher": home_pitcher,
            "home_pitcher_stats": home_stats,
        }
        data.append(game_data)

    return page_date, data

def get_starting_pitchers_data(target_date=None):
    if not target_date:
        target_date = datetime.now(pytz.timezone("US/Eastern")).date()

    urls = [
        "https://www.rotowire.com/baseball/daily-lineups.php",
        "https://www.rotowire.com/baseball/daily-lineups.php?date=tomorrow"
    ]

    for url in urls:
        try:
            page_date, data = fetch_pitcher_data_from_url(url)
            if page_date == target_date:
                return data
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")

    print("❌ No matching pitcher data found for", target_date)
    return []

if __name__ == "__main__":
    data = get_starting_pitchers()
    print("\n✅ Scraped Data for Today's MLB Games:\n")
    for game in data:
        print(game)