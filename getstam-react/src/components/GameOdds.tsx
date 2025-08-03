import React from "react";
import { Box, Typography, Divider } from "@mui/material";

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

type GameOddsProps = {
  game: Game;
};

const GameOdds: React.FC<GameOddsProps> = ({ game }) => {
  const { home, away, totals } = game;

  const hasScore =
    home.score !== null &&
    home.score !== undefined &&
    away.score !== null &&
    away.score !== undefined;

  const scoreDisplay = hasScore ? `${home.score} - ${away.score}` : "— —";
  const gameStatus = hasScore ? "Final Score" : "Scheduled";

  const formatOdds = (point: number | null, price: number | null) => {
    if (point === null && price === null) return "N/A";
    if (point === null) return `${price}`;
    if (price === null) return `${point}`;
    return `${point} (${price})`;
  };

  return (
    <Box sx={{ p: 2, backgroundColor: "#f9f9f9", borderRadius: 2 }}>
      {/* Teams and Score */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
          mb: 1,
        }}
      >
        <Box sx={{ flex: 1, textAlign: "right" }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {home.team}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Home
          </Typography>
        </Box>

        <Box sx={{ flex: "none", textAlign: "center", px: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {scoreDisplay}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {gameStatus}
          </Typography>
        </Box>

        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {away.team}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Away
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Odds */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          gap: 2,
          textAlign: "center",
          flexWrap: "wrap",
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            H2H
          </Typography>
          <Typography variant="body1">
            {home.odds?.h2h !== undefined && away.odds?.h2h !== undefined
              ? `${home.team}: ${home.odds.h2h} | ${away.team}: ${away.odds.h2h}`
              : "N/A"}
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            Spreads
          </Typography>
          <Typography variant="body1">
            {home.odds?.spread_point !== undefined && away.odds?.spread_point !== undefined
              ? `${home.team}: ${formatOdds(home.odds.spread_point, home.odds.spread_price)} | ${away.team}: ${formatOdds(away.odds.spread_point, away.odds.spread_price)}`
              : "N/A"}
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            Totals
          </Typography>
          <Typography variant="body1">
            {totals.over_point !== undefined && totals.under_point !== undefined
              ? `Over: ${formatOdds(totals.over_point, totals.over_price)} | Under: ${formatOdds(totals.under_point, totals.under_price)}`
              : "N/A"}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default GameOdds;
