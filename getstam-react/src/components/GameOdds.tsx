import React from "react";
import { Box, Typography, Divider } from "@mui/material";
import { TeamOdds, TeamData, TotalsData } from "../types/gameTypes";

type Game = {
  home: TeamData;
  away: TeamData;
  totals: TotalsData;
};

type GameOddsProps = {
  game: Game;
  pitcherData?: {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  };
};

const GameOdds: React.FC<GameOddsProps> = ({ game, pitcherData }) => {
  const { home, away, totals } = game;
  // Hide odds if both scores are present and ALL odds/totals fields are null (game is over and no odds data)
  const allOddsNull = (
    (!home.odds || (home.odds.h2h === null && home.odds.spread_point === null && home.odds.spread_price === null)) &&
    (!away.odds || (away.odds.h2h === null && away.odds.spread_point === null && away.odds.spread_price === null)) &&
    (!totals || (totals.over_point === null && totals.under_point === null && totals.over_price === null && totals.under_price === null))
  );
  const isGameOver =
    home?.score !== null && home?.score !== undefined &&
    away?.score !== null && away?.score !== undefined &&
    allOddsNull;

  const hasScore =
    home.score !== null &&
    home.score !== undefined &&
    away.score !== null &&
    away.score !== undefined;

  // Responsive score display: one dash for mobile, two for desktop
  const scoreDisplayMobile = hasScore ? `${home.score} - ${away.score}` : "—";
  const scoreDisplayDesktop = hasScore ? `${home.score} - ${away.score}` : "— —";
  const gameStatus = hasScore ? "" : "Scheduled";

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
          gap: { xs: 0, sm: 2 },
          mb: 1,
        }}
      >
        <Box sx={{ flex: 1, textAlign: "right" }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {home.team}
          </Typography>
          {pitcherData?.home_pitcher && (
            <Typography variant="body2" color="primary" sx={{ fontStyle: "italic" }}>
              Pitcher: {pitcherData.home_pitcher_stats 
                ? `${pitcherData.home_pitcher} (${pitcherData.home_pitcher_stats})`
                : pitcherData.home_pitcher
              }
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            Home
          </Typography>
        </Box>

        <Box sx={{ flex: "none", textAlign: "center", px: { xs: 0, sm: 2 } }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              minWidth: { xs: 40, sm: 60 },
              fontSize: { xs: '1rem', sm: '1.25rem' },
              px: { xs: 0.5, sm: 2 },
              display: { xs: 'block', sm: 'none' }
            }}
          >
            {scoreDisplayMobile}
          </Typography>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              minWidth: { xs: 40, sm: 60 },
              fontSize: { xs: '1rem', sm: '1.25rem' },
              px: { xs: 0.5, sm: 2 },
              display: { xs: 'none', sm: 'block' }
            }}
          >
            {scoreDisplayDesktop}
          </Typography>
          {/* Hide 'Scheduled' on mobile to save space */}
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ display: { xs: 'none', sm: 'block' } }}
          >
            {gameStatus}
          </Typography>
          {/* Show FINAL label if game is over */}
          {isGameOver && (
            <Typography
              variant="subtitle2"
              sx={{ mt: 0.5, fontWeight: 700, letterSpacing: 1 }}
            >
              FINAL
            </Typography>
          )}
        </Box>

        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {away.team}
          </Typography>
          {pitcherData?.away_pitcher && (
            <Typography variant="body2" color="primary" sx={{ fontStyle: "italic" }}>
              Pitcher: {pitcherData.away_pitcher_stats 
                ? `${pitcherData.away_pitcher} (${pitcherData.away_pitcher_stats})`
                : pitcherData.away_pitcher
              }
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            Away
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Odds: Only show if game is not over */}
      {!isGameOver && (
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
      )}
    </Box>
  );
};

export default GameOdds;
