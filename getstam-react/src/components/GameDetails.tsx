import React, { useState } from "react";
import { Box, Typography, Paper, FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import GameOdds from "./GameOdds";
import HistoricalGames from "./HistoricalGames";
import { convertTeamName } from "../utils/teamNameConverter";

type TeamOdds = {
  h2h: number | null;
  spread_point: number | null;
  spread_price: number | null;
};

type TeamData = {
  team: string;
  score: number | null;
  odds: TeamOdds;
};

type TotalsData = {
  over_point: number | null;
  over_price: number | null;
  under_point: number | null;
  under_price: number | null;
};

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

type GameDetailsProps = {
  game: Game;
  homeTeamHistory?: HistoricalData | null;
  awayTeamHistory?: HistoricalData | null;
  headToHeadHistory?: HistoricalData | null;
  onLimitChange?: (limit: number) => void;
  currentLimit?: number;
};

const GameDetails: React.FC<GameDetailsProps> = ({ 
  game, 
  homeTeamHistory, 
  awayTeamHistory, 
  headToHeadHistory,
  onLimitChange,
  currentLimit = 5
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

  const scoreDisplay = hasScore ? `${home.score} - ${away.score}` : "— —";
  const gameStatus = hasScore ? "Final Score" : "Scheduled";

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
          teamName={convertTeamName(homeTeamName)}
        />

        {/* Away Team Last N Games */}
        <HistoricalGames
          title={`${awayTeamName} - Last ${gamesLimit} Games`}
          games={awayTeamHistory?.games || []}
          loading={awayTeamHistory === null}
          teamName={convertTeamName(awayTeamName)}
        />

        {/* Head to Head */}
        <HistoricalGames
          title={`${awayTeamName} vs ${homeTeamName} - Last ${gamesLimit} H2H`}
          games={headToHeadHistory?.games || []}
          loading={headToHeadHistory === null}
          isHeadToHead={true}
        />
      </Box>
    </Box>
  );
};

export default GameDetails;