import React, { useState } from "react";
import { Box, Typography, Paper, FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import GameOdds from "./GameOdds";
import HistoricalGames from "./HistoricalGames";
import { getSportType } from "../types/gameTypes";
import TeamRankings from "./TeamRankings";
import { convertTeamNameBySport } from "../utils/teamNameConverter";
import { TeamOdds, TeamData, TotalsData } from "../types/gameTypes";

type Game = {
  home: TeamData;
  away: TeamData;
  totals: TotalsData;
  home_team_name?: string; // For database games
  away_team_name?: string; // For database games
};

type HistoricalData = {
  games: any[];
  count: number;
  sport: string;
  team_name?: string;
  home_team?: string;
  away_team?: string;
  limit: number;
};

type RankingsData = {
  offense: {
    Total: string;
    "Total Rank": string;
    Passing: string;
    "Passing Rank": string;
    Rushing: string;
    "Rushing Rank": string;
    Scoring: string;
    "Scoring Rank": string;
  };
  defense: {
    Total: string;
    "Total Rank": string;
    Passing: string;
    "Passing Rank": string;
    Rushing: string;
    "Rushing Rank": string;
    Scoring: string;
    "Scoring Rank": string;
  };
};

type GameDetailsProps = {
  game: Game;
  homeTeamHistory?: HistoricalData | null;
  awayTeamHistory?: HistoricalData | null;
  headToHeadHistory?: HistoricalData | null;
  onLimitChange?: (limit: number) => void;
  currentLimit?: number;
  sportKey?: string; // Add sport key to determine which converter to use
  homeRankings?: RankingsData | null;
  awayRankings?: RankingsData | null;
  rankingsLoading?: boolean;
};

const GameDetails: React.FC<GameDetailsProps> = ({ 
  game, 
  homeTeamHistory, 
  awayTeamHistory, 
  headToHeadHistory,
  onLimitChange,
  currentLimit = 5,
  sportKey = "americanfootball_nfl", // Default to NFL if not provided
  homeRankings,
  awayRankings,
  rankingsLoading = false
}) => {
  const { home, away } = game;
  const [gamesLimit, setGamesLimit] = useState<number>(currentLimit);

  const handleLimitChange = (newLimit: number) => {
    setGamesLimit(newLimit);
    if (onLimitChange) {
      onLimitChange(newLimit);
    }
  };

  const hasScore =
    home.score !== null &&
    home.score !== undefined &&
    away.score !== null &&
    away.score !== undefined;
  
  console.log("GameDetails Rendered with game:", game);

  const scoreDisplay = hasScore ? `${away.score} - ${home.score}` : "— —";
  const gameStatus = hasScore ? "" : "Scheduled";

  // Get team names for historical data titles
  const homeTeamName = home.team || game.home_team_name || "Home Team";
  const awayTeamName = away.team || game.away_team_name || "Away Team";

  return (
    <Box>
      <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 900, mx: "auto", backgroundColor: "#f9f9f9" }}>
        {/* Odds section */}
        <GameOdds game={game} />
      </Paper>

      {/* Historical Games Section */}
      <Box sx={{ maxWidth: 900, mx: "auto", mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
            Recent Performance
          </Typography>
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="games-limit-label">Show Games</InputLabel>
            <Select
              labelId="games-limit-label"
              id="games-limit-select"
              value={gamesLimit}
              label="Show Games"
              onChange={(e) => handleLimitChange(e.target.value as number)}
            >
              <MenuItem value={3}>Last 3</MenuItem>
              <MenuItem value={5}>Last 5</MenuItem>
              <MenuItem value={10}>Last 10</MenuItem>
              <MenuItem value={15}>Last 15</MenuItem>
              <MenuItem value={20}>Last 20</MenuItem>
            </Select>
          </FormControl>
        </Box>
        
        {/* Home Team Last N Games */}
        <HistoricalGames
          title={`${homeTeamName} - Last ${gamesLimit} Games`}
          games={homeTeamHistory?.games || []}
          loading={homeTeamHistory === null}
          teamName={convertTeamNameBySport(sportKey, homeTeamName)}
          sportType={getSportType(sportKey)}
        />

        {/* Away Team Last N Games */}
        <HistoricalGames
          title={`${awayTeamName} - Last ${gamesLimit} Games`}
          games={awayTeamHistory?.games || []}
          loading={awayTeamHistory === null}
          teamName={convertTeamNameBySport(sportKey, awayTeamName)}
          sportType={getSportType(sportKey)}
        />

        {/* Head to Head */}
        <HistoricalGames
          title={`${awayTeamName} vs ${homeTeamName} - Last ${gamesLimit} H2H`}
          games={headToHeadHistory?.games || []}
          loading={headToHeadHistory === null}
          teamName={convertTeamNameBySport(sportKey, homeTeamName)}
          isHeadToHead={true}
          sportType={getSportType(sportKey)}
        />

        {/* Team Rankings for NFL and NCAAF */}
        {(sportKey === 'americanfootball_nfl' || sportKey === 'americanfootball_ncaaf') && (
          <TeamRankings 
            homeTeam={homeTeamName}
            awayTeam={awayTeamName}
            homeRankings={homeRankings || null}
            awayRankings={awayRankings || null}
            loading={rankingsLoading}
          />
        )}
      </Box>
    </Box>
  );
};

export default GameDetails;