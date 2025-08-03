import React from "react";
import { Box, Typography, Paper, Divider } from "@mui/material";
import GameOdds from "./GameOdds";

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
};

type GameDetailsProps = {
  game: Game;
};

const GameDetails: React.FC<GameDetailsProps> = ({ game }) => {
  const { home, away } = game;

  const hasScore =
    home.score !== null &&
    home.score !== undefined &&
    away.score !== null &&
    away.score !== undefined;

  const scoreDisplay = hasScore ? `${home.score} - ${away.score}` : "— —";
  const gameStatus = hasScore ? "Final Score" : "Scheduled";

  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 900, mx: "auto", backgroundColor: "#f9f9f9" }}>
      {/* Odds section */}
      <GameOdds game={game} />
    </Paper>
  );
};

export default GameDetails;