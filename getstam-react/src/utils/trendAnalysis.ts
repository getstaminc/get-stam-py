import { convertTeamName } from './teamNameConverter';

// Types for trend analysis
export type TrendType = 'win_streak' | 'loss_streak' | 'cover_streak' | 'no_cover_streak' | 'over_streak' | 'under_streak';

export interface TrendResult {
  type: TrendType;
  count: number;
  description: string;
}

export interface GameWithTrends {
  game: any;
  homeTeamTrends: TrendResult[];
  awayTeamTrends: TrendResult[];
  headToHeadTrends: TrendResult[];
  hasTrends: boolean;
}

// Map URL sport to database sport
const API_SPORT_TO_DB_SPORT: { [key: string]: string } = {
  americanfootball_nfl: "nfl",
  baseball_mlb: "mlb", 
  basketball_nba: "nba",
  icehockey_nhl: "nhl",
  americanfootball_ncaaf: "ncaafb",
  basketball_ncaab: "ncaabb",
  soccer_epl: "epl",
  americanfootball_nfl_preseason: "nfl",
};

// Fetch team history
const fetchTeamHistory = async (sportKey: string, teamName: string, limit: number = 5) => {
  const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
  const convertedTeamName = convertTeamName(teamName);
  const response = await fetch(`https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedTeamName)}?limit=${limit}`, {
    headers: {
      "X-API-KEY": process.env.REACT_APP_API_KEY || "",
    },
  });
  if (!response.ok) throw new Error("Failed to fetch team history");
  return response.json();
};

// Fetch head-to-head history
const fetchHeadToHead = async (sportKey: string, homeTeam: string, awayTeam: string, limit: number = 5) => {
  const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
  const convertedHomeTeam = convertTeamName(homeTeam);
  const convertedAwayTeam = convertTeamName(awayTeam);
  const response = await fetch(
    `https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedHomeTeam)}/vs/${encodeURIComponent(convertedAwayTeam)}?limit=${limit}`,
    {
      headers: {
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    }
  );
  if (!response.ok) throw new Error("Failed to fetch head-to-head history");
  return response.json();
};

// Helper function to get team-specific data from a game
const getTeamData = (game: any, teamName: string) => {
  const isTeamHome = game.home_team_name === teamName;
  const isTeamAway = game.away_team_name === teamName;
  
  if (isTeamHome) {
    return {
      teamPoints: game.home_points,
      teamLine: game.home_line,
      opponentPoints: game.away_points,
      opponentLine: game.away_line
    };
  } else if (isTeamAway) {
    return {
      teamPoints: game.away_points,
      teamLine: game.away_line,
      opponentPoints: game.home_points,
      opponentLine: game.home_line
    };
  } else {
    // Fallback using team_side
    return {
      teamPoints: game.team_side === 'home' ? game.home_points : game.away_points,
      teamLine: game.team_side === 'home' ? game.home_line : game.away_line,
      opponentPoints: game.team_side === 'home' ? game.away_points : game.home_points,
      opponentLine: game.team_side === 'home' ? game.away_line : game.home_line
    };
  }
};

// Analyze team trends from historical games
const analyzeTeamTrends = (games: any[], teamName: string, minTrendLength: number = 3): TrendResult[] => {
  if (!games || games.length < minTrendLength) return [];
  
  const trends: TrendResult[] = [];
  
  // Sort games by date (most recent first)
  const sortedGames = games.sort((a, b) => new Date(b.game_date).getTime() - new Date(a.game_date).getTime());
  
  // Check for win/loss streaks
  let currentWinStreak = 0;
  let currentLossStreak = 0;
  let currentCoverStreak = 0;
  let currentNoCoverStreak = 0;
  let currentOverStreak = 0;
  let currentUnderStreak = 0;
  
  for (const game of sortedGames) {
    const teamData = getTeamData(game, teamName);
    
    // Win/Loss analysis
    if (teamData.teamPoints > teamData.opponentPoints) {
      currentWinStreak++;
      currentLossStreak = 0;
    } else if (teamData.teamPoints < teamData.opponentPoints) {
      currentLossStreak++;
      currentWinStreak = 0;
    } else {
      // Tie breaks both streaks
      currentWinStreak = 0;
      currentLossStreak = 0;
    }
    
    // Spread analysis
    if (teamData.teamLine !== null && teamData.teamPoints !== null && teamData.opponentPoints !== null) {
      const lineResult = (teamData.teamPoints + teamData.teamLine) > teamData.opponentPoints;
      if (lineResult) {
        currentCoverStreak++;
        currentNoCoverStreak = 0;
      } else if ((teamData.teamPoints + teamData.teamLine) < teamData.opponentPoints) {
        currentNoCoverStreak++;
        currentCoverStreak = 0;
      } else {
        // Push breaks both streaks
        currentCoverStreak = 0;
        currentNoCoverStreak = 0;
      }
    }
    
    // Total analysis
    if (game.total_points !== null && game.total !== null) {
      if (game.total_points > game.total) {
        currentOverStreak++;
        currentUnderStreak = 0;
      } else if (game.total_points < game.total) {
        currentUnderStreak++;
        currentOverStreak = 0;
      } else {
        // Push breaks both streaks
        currentOverStreak = 0;
        currentUnderStreak = 0;
      }
    }
  }
  
  // Add trends that meet minimum length
  if (currentWinStreak >= minTrendLength) {
    trends.push({
      type: 'win_streak',
      count: currentWinStreak,
      description: `Won ${currentWinStreak} straight games`
    });
  }
  
  if (currentLossStreak >= minTrendLength) {
    trends.push({
      type: 'loss_streak',
      count: currentLossStreak,
      description: `Lost ${currentLossStreak} straight games`
    });
  }
  
  if (currentCoverStreak >= minTrendLength) {
    trends.push({
      type: 'cover_streak',
      count: currentCoverStreak,
      description: `Covered ${currentCoverStreak} straight spreads`
    });
  }
  
  if (currentNoCoverStreak >= minTrendLength) {
    trends.push({
      type: 'no_cover_streak',
      count: currentNoCoverStreak,
      description: `Failed to cover ${currentNoCoverStreak} straight spreads`
    });
  }
  
  if (currentOverStreak >= minTrendLength) {
    trends.push({
      type: 'over_streak',
      count: currentOverStreak,
      description: `Total went OVER ${currentOverStreak} straight games`
    });
  }
  
  if (currentUnderStreak >= minTrendLength) {
    trends.push({
      type: 'under_streak',
      count: currentUnderStreak,
      description: `Total went UNDER ${currentUnderStreak} straight games`
    });
  }
  
  return trends;
};

// Main function to analyze trends for a single game
export const analyzeGameTrends = async (
  game: any, 
  sportKey: string, 
  limit: number = 5, 
  minTrendLength: number = 3
): Promise<GameWithTrends> => {
  try {
    const homeTeam = game.home?.team || game.home_team_name;
    const awayTeam = game.away?.team || game.away_team_name;
    
    if (!homeTeam || !awayTeam) {
      return {
        game,
        homeTeamTrends: [],
        awayTeamTrends: [],
        headToHeadTrends: [],
        hasTrends: false
      };
    }
    
    // Fetch historical data for both teams and head-to-head
    const [homeHistory, awayHistory, h2hHistory] = await Promise.all([
      fetchTeamHistory(sportKey, homeTeam, limit),
      fetchTeamHistory(sportKey, awayTeam, limit),
      fetchHeadToHead(sportKey, homeTeam, awayTeam, limit)
    ]);
    
    // Analyze trends
    const homeTeamTrends = analyzeTeamTrends(homeHistory.games || [], homeTeam, minTrendLength);
    const awayTeamTrends = analyzeTeamTrends(awayHistory.games || [], awayTeam, minTrendLength);
    const headToHeadTrends = analyzeTeamTrends(h2hHistory.games || [], homeTeam, minTrendLength);
    
    const hasTrends = homeTeamTrends.length > 0 || awayTeamTrends.length > 0 || headToHeadTrends.length > 0;
    
    return {
      game,
      homeTeamTrends,
      awayTeamTrends,
      headToHeadTrends,
      hasTrends
    };
  } catch (error) {
    console.error('Error analyzing game trends:', error);
    return {
      game,
      homeTeamTrends: [],
      awayTeamTrends: [],
      headToHeadTrends: [],
      hasTrends: false
    };
  }
};

// Function to analyze trends for multiple games
export const analyzeMultipleGamesTrends = async (
  games: any[], 
  sportKey: string, 
  limit: number = 5, 
  minTrendLength: number = 3
): Promise<GameWithTrends[]> => {
  const promises = games.map(game => analyzeGameTrends(game, sportKey, limit, minTrendLength));
  return Promise.all(promises);
};
