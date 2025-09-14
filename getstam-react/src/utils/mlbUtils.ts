// MLB team name conversion mapping for pitcher data lookup
export const MLB_TEAM_NAME_CONVERSION: { [key: string]: string } = {
  "Arizona Diamondbacks": "ARI",
  "Atlanta Braves": "ATL", 
  "Baltimore Orioles": "BAL",
  "Boston Red Sox": "BOS",
  "Chicago White Sox": "CWS",
  "Chicago Cubs": "CHC",
  "Cincinnati Reds": "CIN",
  "Cleveland Guardians": "CLE",
  "Colorado Rockies": "COL",
  "Detroit Tigers": "DET",
  "Houston Astros": "HOU",
  "Kansas City Royals": "KC",
  "Los Angeles Angels": "LAA",
  "Los Angeles Dodgers": "LAD",
  "Miami Marlins": "MIA",
  "Milwaukee Brewers": "MIL",
  "Minnesota Twins": "MIN",
  "New York Yankees": "NYY",
  "New York Mets": "NYM",
  "Oakland Athletics": "ATH",
  "Philadelphia Phillies": "PHI",
  "Pittsburgh Pirates": "PIT",
  "San Diego Padres": "SD",
  "San Francisco Giants": "SF",
  "Seattle Mariners": "SEA",
  "St. Louis Cardinals": "STL",
  "Tampa Bay Rays": "TB",
  "Texas Rangers": "TEX",
  "Toronto Blue Jays": "TOR",
  "Washington Nationals": "WSH"
};

// Utility functions for MLB pitcher data
export interface PitcherData {
  home_pitcher?: string;
  away_pitcher?: string;
  home_pitcher_stats?: string;
  away_pitcher_stats?: string;
}

export const fetchPitcherData = async (): Promise<any> => {
  try {
    console.log("🚀 Fetching pitcher data from API...");
    const response = await fetch("https://www.getstam.com/api/mlb/pitchers");
    if (!response.ok) {
      console.error(`Pitcher API failed with ${response.status}: ${response.statusText}`);
      return {};
    }
    const data = await response.json();
    console.log("📊 Received pitcher data:", data);
    return data;
  } catch (error) {
    console.error("Error fetching pitcher data:", error);
    return {};
  }
};

export const getPitcherDataForGame = (
  game: any, 
  pitcherData: any, 
  selectedDate: Date,
  sportKey: string
): PitcherData | undefined => {
  if (sportKey !== "baseball_mlb" || !pitcherData || Object.keys(pitcherData).length === 0) {
    return undefined;
  }

  // Convert team names to abbreviations
  const homeAbbr = MLB_TEAM_NAME_CONVERSION[game.home.team];
  const awayAbbr = MLB_TEAM_NAME_CONVERSION[game.away.team];

  if (!homeAbbr || !awayAbbr) {
    return undefined;
  }

  // Create date key in format YYYY-MM-DD from selectedDate
  const dateKey = selectedDate.toISOString().split('T')[0];
  
  // Look for pitcher data for this date
  const dateData = pitcherData[dateKey];
  if (!dateData || !Array.isArray(dateData)) {
    return undefined;
  }

  // Find the game in the array that matches our teams
  const matchingGame = dateData.find((gameData: any) => 
    (gameData.home_team === homeAbbr && gameData.away_team === awayAbbr) ||
    (gameData.home_team === homeAbbr || gameData.away_team === awayAbbr)
  );

  if (!matchingGame) {
    return undefined;
  }

  return {
    home_pitcher: matchingGame.home_pitcher,
    away_pitcher: matchingGame.away_pitcher,
    home_pitcher_stats: matchingGame.home_pitcher_stats,
    away_pitcher_stats: matchingGame.away_pitcher_stats
  };
};
