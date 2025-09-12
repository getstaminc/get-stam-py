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

// Map URL sport to database sport and API paths
const SPORT_CONFIG: { [key: string]: { dbSport: string, apiPath: string, isSoccer?: boolean } } = {
  americanfootball_nfl: { dbSport: "nfl", apiPath: "nfl" },
  baseball_mlb: { dbSport: "mlb", apiPath: "mlb" }, 
  basketball_nba: { dbSport: "nba", apiPath: "nba" },
  icehockey_nhl: { dbSport: "nhl", apiPath: "nhl" },
  americanfootball_ncaaf: { dbSport: "ncaaf", apiPath: "ncaaf" },
  basketball_ncaab: { dbSport: "ncaab", apiPath: "ncaab" },
  soccer_epl: { dbSport: "epl", apiPath: "soccer", isSoccer: true },
  americanfootball_nfl_preseason: { dbSport: "nfl", apiPath: "nfl" },
};

// Helper function to check if sport is soccer
const isSoccerSport = (sportKey: string): boolean => {
  return SPORT_CONFIG[sportKey]?.isSoccer || false;
};

// Helper function to get soccer league from sport key
const getSoccerLeague = (sportKey: string): string => {
  if (sportKey === 'soccer_epl' || sportKey === 'epl') return 'epl';
  return 'epl'; // Default to EPL for now
};

// Fetch team history using new historical endpoints
const fetchTeamHistory = async (sportKey: string, teamName: string, limit: number = 5) => {
  const config = SPORT_CONFIG[sportKey];
  if (!config) throw new Error(`Unsupported sport: ${sportKey}`);
  
  const convertedTeamName = convertTeamNameBySport(sportKey, teamName);
  
  let url: string;
  if (isSoccerSport(sportKey)) {
    const league = getSoccerLeague(sportKey);
    url = `https://www.getstam.com/api/historical/soccer/teams/${encodeURIComponent(convertedTeamName)}/games?league=${league}&limit=${limit}`;
  } else {
    url = `https://www.getstam.com/api/historical/${config.apiPath}/teams/${encodeURIComponent(convertedTeamName)}/games?limit=${limit}`;
  }
  
  const response = await fetch(url, {
    headers: {
      "X-API-KEY": process.env.REACT_APP_API_KEY || "",
    },
  });
  if (!response.ok) throw new Error("Failed to fetch team history");
  return response.json();
};

// Fetch head-to-head history using new historical endpoints
const fetchHeadToHead = async (sportKey: string, homeTeam: string, awayTeam: string, limit: number = 5) => {
  const config = SPORT_CONFIG[sportKey];
  if (!config) throw new Error(`Unsupported sport: ${sportKey}`);
  
  const convertedHomeTeam = convertTeamNameBySport(sportKey, homeTeam);
  const convertedAwayTeam = convertTeamNameBySport(sportKey, awayTeam);
  
  let url: string;
  if (isSoccerSport(sportKey)) {
    const league = getSoccerLeague(sportKey);
    url = `https://www.getstam.com/api/historical/soccer/teams/${encodeURIComponent(convertedHomeTeam)}/vs/${encodeURIComponent(convertedAwayTeam)}?league=${league}&limit=${limit}`;
  } else {
    url = `https://www.getstam.com/api/historical/${config.apiPath}/teams/${encodeURIComponent(convertedHomeTeam)}/vs/${encodeURIComponent(convertedAwayTeam)}?limit=${limit}`;
  }
  
  const response = await fetch(url, {
    headers: {
      "X-API-KEY": process.env.REACT_APP_API_KEY || "",
    },
  });
  if (!response.ok) throw new Error("Failed to fetch head-to-head history");
  return response.json();
};

// Helper function to get team-specific data from a game based on sport
const getTeamData = (game: any, teamName: string, sportKey: string) => {
  // Convert the search team name to the short form for comparison
  const convertedTeamName = convertTeamNameBySport(sportKey, teamName);
  
  // Determine field names based on sport
  let homeTeamField, awayTeamField, homeScoreField, awayScoreField;
  
  if (sportKey.includes('mlb') || sportKey === 'baseball_mlb') {
    // MLB uses different field names
    homeTeamField = 'home_team_name';
    awayTeamField = 'away_team_name'; 
    homeScoreField = 'home_runs';
    awayScoreField = 'away_runs';
  } else if (isSoccerSport(sportKey)) {
    // Soccer uses different field names
    homeTeamField = 'home_team_name';
    awayTeamField = 'away_team_name';
    homeScoreField = 'home_goals';
    awayScoreField = 'away_goals';
  } else {
    // NFL, NCAAF, NBA, NHL use points
    homeTeamField = 'home_team_name';
    awayTeamField = 'away_team_name';
    homeScoreField = 'home_points';
    awayScoreField = 'away_points';
  }
  
  const homeTeam = game[homeTeamField] || game.home_team;
  const awayTeam = game[awayTeamField] || game.away_team;
  const homeScore = game[homeScoreField];
  const awayScore = game[awayScoreField];
  
  const isTeamHome = homeTeam === teamName || homeTeam === convertedTeamName;
  const isTeamAway = awayTeam === teamName || awayTeam === convertedTeamName;
  
  if (isTeamHome) {
    return {
      teamPoints: homeScore,
      teamLine: game.home_line,
      opponentPoints: awayScore,
      opponentLine: game.away_line
    };
  } else if (isTeamAway) {
    return {
      teamPoints: awayScore,
      teamLine: game.away_line,
      opponentPoints: homeScore,
      opponentLine: game.home_line
    };
  } else {
    // Team not found in this game, return nulls
    return {
      teamPoints: game.team_side === 'home' ? homeScore : awayScore,
      teamLine: game.team_side === 'home' ? game.home_line : game.away_line,
      opponentPoints: game.team_side === 'home' ? awayScore : homeScore,
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
    
    // Total analysis - handle different field names for each sport
    let actualTotal, totalLine;
    
    if (sportKey.includes('mlb') || sportKey === 'baseball_mlb') {
      // MLB: actual total is home_runs + away_runs
      actualTotal = (game.home_runs || 0) + (game.away_runs || 0);
      totalLine = game.total;
    } else if (isSoccerSport(sportKey)) {
      // Soccer: actual total is home_goals + away_goals
      actualTotal = (game.home_goals || 0) + (game.away_goals || 0);
      totalLine = game.total_goals || game.total;
    } else {
      // NFL, NCAAF, NBA, NHL: actual total is home_points + away_points
      actualTotal = (game.home_points || 0) + (game.away_points || 0);
      totalLine = game.total_points || game.total;
    }
    
    if (actualTotal !== null && totalLine !== null) {
      if (actualTotal > totalLine) {
        overResults.push(true);
        underResults.push(false);
      } else if (actualTotal < totalLine) {
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
