// Shared game type definitions

// Base game interface
export interface BaseGame {
  game_id: number;
  game_date: string;
  start_time: string;
  team_side?: string;
}

// NFL/NCAAF game structure
export interface NFLGame extends BaseGame {
  home_team_name: string;
  away_team_name: string;
  home_points: number;
  away_points: number;
  total_points: number;
  home_line: number;
  away_line: number;
  home_money_line: number;
  away_money_line: number;
  total?: number;
}

// MLB game structure
export interface MLBGame extends BaseGame {
  home_team: string;
  away_team: string;
  home_runs: number;
  away_runs: number;
  home_line: number;
  away_line: number;
  total: number;
  home_starting_pitcher?: string;
  away_starting_pitcher?: string;
  playoffs: boolean;
}

// Soccer game structure
export interface SoccerGame extends BaseGame {
  home_team_name: string;
  away_team_name: string;
  home_goals: number;
  away_goals: number;
  total_goals: number;
  home_spread: number;
  away_spread: number;
  home_money_line: number;
  away_money_line: number;
  draw_money_line: number;
  total_over_point: number;
  total_under_point: number;
  total_over_price: number;
  total_under_price: number;
  league: string;
  home_first_half_goals?: number;
  away_first_half_goals?: number;
  home_second_half_goals?: number;
  away_second_half_goals?: number;
}

// NBA game structure
export interface NBAGame extends BaseGame {
  home_team_name: string;
  away_team_name: string;
  home_points: number;
  away_points: number;
  total_points: number;
  home_line: number;
  away_line: number;
  home_money_line: number;
  away_money_line: number;
  total?: number;
}

// NHL game structure
export interface NHLGame extends BaseGame {
  home_team_name: string;
  away_team_name: string;
  home_goals: number;
  away_goals: number;
  total_goals: number;
  home_money_line: number;
  away_money_line: number;
  total: number;
  playoffs: boolean;
}

// Union type for all game types
export type HistoricalGame = NFLGame | MLBGame | SoccerGame | NHLGame;

// Unified game data interface for display components
export interface GameData {
  game_id: number;
  date: string;
  home_team_name: string;
  away_team_name: string;
  home_runs?: number;
  away_runs?: number;
  home_points?: number;
  away_points?: number;
  home_goals?: number;
  away_goals?: number;
  total: number;
  home_line: number;
  away_line: number;
  start_time?: string;
  playoffs?: boolean;
  home_starting_pitcher?: string;
  away_starting_pitcher?: string;
  league?: string;
  home_spread?: number;
  away_spread?: number;
}

export type SportType = 'nfl' | 'ncaaf' | 'mlb' | 'soccer' | 'nba' | 'nhl';

export type HistoricalGamesProps = {
  title: string;
  games: HistoricalGame[];
  loading?: boolean;
  teamName?: string;
  isHeadToHead?: boolean;
  sportType: SportType;
};

// Helper function to convert API sport key to our SportType
export const getSportType = (sportKey: string): SportType => {
  const sportMap: { [key: string]: SportType } = {
    'americanfootball_nfl': 'nfl',
    'americanfootball_nfl_preseason': 'nfl',
    'americanfootball_ncaaf': 'ncaaf',
    'basketball_nba': 'nba',
    'baseball_mlb': 'mlb',
    'icehockey_nhl': 'nhl',
    'soccer_epl': 'soccer',
    // Also support short forms
    'nfl': 'nfl',
    'ncaaf': 'ncaaf',
    'nba': 'nba',
    'mlb': 'mlb',
    'nhl': 'nhl',
    'soccer': 'soccer',
    'epl': 'soccer'
  };
  
  return sportMap[sportKey] || 'nfl'; // Default to NFL
};

// Common odds-related types
export interface TeamOdds {
  h2h: number | null;
  spread_point: number | null;
  spread_price: number | null;
}

export interface TotalsData {
  over_point: number | null;
  over_price: number | null;
  under_point: number | null;
  under_price: number | null;
}

export interface TeamData {
  team: string;
  score: number | null;
  odds: TeamOdds;
}

// Live game data structure (for GameContext and similar)
export interface LiveGameData {
  game_id: string;
  commence_time: string;
  home: TeamData;
  away: TeamData;
  totals: TotalsData;
  isToday: boolean;
}
