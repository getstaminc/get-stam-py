import { convertTeamNameBySport } from './teamNameConverter';

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
  americanfootball_ncaaf: "ncaaf",
  basketball_ncaab: "ncaab",
  soccer_epl: "epl",
  americanfootball_nfl_preseason: "nfl",
};

// Fetch team history
const fetchTeamHistory = async (sportKey: string, teamName: string, limit: number = 5) => {
  const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
  const convertedTeamName = convertTeamNameBySport(sportKey, teamName);
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
  const convertedHomeTeam = convertTeamNameBySport(sportKey, homeTeam);
  const convertedAwayTeam = convertTeamNameBySport(sportKey, awayTeam);
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
const getTeamData = (game: any, teamName: string, sportKey: string) => {
  // Convert the search team name to the short form for comparison
  const convertedTeamName = convertTeamNameBySport(sportKey, teamName);
  
  const isTeamHome = game.home_team_name === teamName || game.home_team_name === convertedTeamName;
  const isTeamAway = game.away_team_name === teamName || game.away_team_name === convertedTeamName;
  
  console.log(`getTeamData debug:`, {
    searchingFor: teamName,
    convertedTeamName: convertedTeamName,
    homeTeamName: game.home_team_name,
    awayTeamName: game.away_team_name,
    isTeamHome,
    isTeamAway,
    teamSide: game.team_side
  });
  
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
    console.log(`Using fallback team_side logic for ${teamName}`);
    return {
      teamPoints: game.team_side === 'home' ? game.home_points : game.away_points,
      teamLine: game.team_side === 'home' ? game.home_line : game.away_line,
      opponentPoints: game.team_side === 'home' ? game.away_points : game.home_points,
      opponentLine: game.team_side === 'home' ? game.away_line : game.home_line
    };
  }
};

// Analyze team trends from historical games
const analyzeTeamTrends = (games: any[], teamName: string, sportKey: string, minTrendLength: number = 3): TrendResult[] => {
  if (!games || games.length < minTrendLength) return [];
  
  const trends: TrendResult[] = [];
  
  // Sort games by date (most recent first)
  const sortedGames = games.sort((a, b) => new Date(b.game_date).getTime() - new Date(a.game_date).getTime());
  
  // Calculate streaks from most recent game backwards
  const calculateCurrentStreak = (results: boolean[]): number => {
    let streak = 0;
    for (const result of results) {
      if (result) {
        streak++;
      } else {
        break;
      }
    }
    return streak;
  };
  
  // Collect all results (most recent first)
  const winResults: boolean[] = [];
  const lossResults: boolean[] = [];
  const coverResults: boolean[] = [];
  const noCoverResults: boolean[] = [];
  const overResults: boolean[] = [];
  const underResults: boolean[] = [];
  
  for (const game of sortedGames) {
    const teamData = getTeamData(game, teamName, sportKey);
    
    // Debug logging
    console.log(`Game ${game.game_date}: ${teamName}`, {
      teamPoints: teamData.teamPoints,
      teamLine: teamData.teamLine,
      opponentPoints: teamData.opponentPoints,
      lineResult: teamData.teamLine !== null ? (teamData.teamPoints + teamData.teamLine) > teamData.opponentPoints : null
    });
    
    // Win/Loss analysis
    if (teamData.teamPoints > teamData.opponentPoints) {
      winResults.push(true);
      lossResults.push(false);
    } else if (teamData.teamPoints < teamData.opponentPoints) {
      winResults.push(false);
      lossResults.push(true);
    } else {
      // Tie breaks both streaks
      winResults.push(false);
      lossResults.push(false);
    }
    
    // Spread analysis
    if (teamData.teamLine !== null && teamData.teamPoints !== null && teamData.opponentPoints !== null) {
      const lineResult = (teamData.teamPoints + teamData.teamLine) > teamData.opponentPoints;
      if (lineResult) {
        coverResults.push(true);
        noCoverResults.push(false);
      } else if ((teamData.teamPoints + teamData.teamLine) < teamData.opponentPoints) {
        coverResults.push(false);
        noCoverResults.push(true);
      } else {
        // Push breaks both streaks
        coverResults.push(false);
        noCoverResults.push(false);
      }
    }
    
    // Total analysis
    if (game.total_points !== null && game.total !== null) {
      if (game.total_points > game.total) {
        overResults.push(true);
        underResults.push(false);
      } else if (game.total_points < game.total) {
        overResults.push(false);
        underResults.push(true);
      } else {
        // Push breaks both streaks
        overResults.push(false);
        underResults.push(false);
      }
    }
  }
  
  // Calculate current streaks
  const currentWinStreak = calculateCurrentStreak(winResults);
  const currentLossStreak = calculateCurrentStreak(lossResults);
  const currentCoverStreak = calculateCurrentStreak(coverResults);
  const currentNoCoverStreak = calculateCurrentStreak(noCoverResults);
  const currentOverStreak = calculateCurrentStreak(overResults);
  const currentUnderStreak = calculateCurrentStreak(underResults);
  
  console.log(`Final streaks for ${teamName}:`, {
    wins: currentWinStreak,
    losses: currentLossStreak,
    covers: currentCoverStreak,
    noCovers: currentNoCoverStreak,
    overs: currentOverStreak,
    unders: currentUnderStreak
  });
  
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
    const homeTeamTrends = analyzeTeamTrends(homeHistory.games || [], homeTeam, sportKey, minTrendLength);
    const awayTeamTrends = analyzeTeamTrends(awayHistory.games || [], awayTeam, sportKey, minTrendLength);
    
    // Debug head-to-head data
    console.log('H2H History games:', h2hHistory.games);
    console.log('Analyzing H2H for homeTeam:', homeTeam);
    
    const headToHeadTrends = analyzeTeamTrends(h2hHistory.games || [], homeTeam, sportKey, minTrendLength);
    
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
