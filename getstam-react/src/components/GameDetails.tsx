import React from "react";
import { Box, Typography, Paper } from "@mui/material";
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
};

const GameDetails: React.FC<GameDetailsProps> = ({ 
  game, 
  homeTeamHistory, 
  awayTeamHistory, 
  headToHeadHistory 
}) => {
  const { home, away } = game;

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
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Recent Performance
        </Typography>
        
        {/* Home Team Last 5 Games */}
        <HistoricalGames
          title={`${homeTeamName} - Last 5 Games`}
          games={homeTeamHistory?.games || []}
          loading={homeTeamHistory === null}
          teamName={convertTeamName(homeTeamName)}
        />

        {/* Away Team Last 5 Games */}
        <HistoricalGames
          title={`${awayTeamName} - Last 5 Games`}
          games={awayTeamHistory?.games || []}
          loading={awayTeamHistory === null}
          teamName={convertTeamName(awayTeamName)}
        />

        {/* Head to Head */}
        <HistoricalGames
          title={`${awayTeamName} vs ${homeTeamName} - Last 5 H2H`}
          games={headToHeadHistory?.games || []}
          loading={headToHeadHistory === null}
          isHeadToHead={true}
        />
      </Box>
    </Box>
  );
};

export default GameDetails;