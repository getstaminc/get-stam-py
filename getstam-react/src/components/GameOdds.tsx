import React from "react";
import { Link } from "react-router-dom";
import { Box, Typography, Button } from "@mui/material";
import { GameWithDraw } from "../types/gameTypes";

interface GameOddsProps {
  game: GameWithDraw;
  pitcherData?: {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  };
  detailsLink?: string;
  onViewDetails?: () => void;
}

const GameOdds: React.FC<GameOddsProps> = ({ game, pitcherData, detailsLink, onViewDetails }) => {
  const { home, away, totals, draw } = game as GameWithDraw;

  const allOddsNull = (
    (!home.odds || (home.odds.h2h === null && home.odds.spread_point === null && home.odds.spread_price === null)) &&
    (!away.odds || (away.odds.h2h === null && away.odds.spread_point === null && away.odds.spread_price === null)) &&
    (!totals || (totals.over_point === null && totals.under_point === null && totals.over_price === null && totals.under_price === null))
  );

  const hasScore =
    home.score !== null && home.score !== undefined &&
    away.score !== null && away.score !== undefined;

  const isGameOver = hasScore && allOddsNull;

  const formatOdds = (point: number | null, price: number | null) => {
    if (point === null && price === null) return "N/A";
    if (point === null) return price !== null ? `${price > 0 ? "+" : ""}${price}` : "N/A";
    const pointStr = `${point > 0 ? "+" : ""}${point}`;
    if (price === null) return pointStr;
    return `${pointStr} (${price > 0 ? "+" : ""}${price})`;
  };

  const formatH2H = (h2h: number | null | undefined) => {
    if (h2h === null || h2h === undefined) return "N/A";
    return `${h2h > 0 ? "+" : ""}${h2h}`;
  };

  const statusLabel = isGameOver
    ? `${home.score} - ${away.score}`
    : hasScore
    ? `${home.score} - ${away.score}`
    : "Scheduled";

  return (
    <Box
      sx={{
        background: "rgba(255,255,255,0.94)",
        border: "1px solid rgba(148,163,184,0.26)",
        borderRadius: "14px",
        p: 2,
        boxShadow: "0 8px 24px rgba(15,23,42,0.08)",
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
      }}
    >
      {/* Card header: Home | Status | Away */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          gap: 1,
          alignItems: "center",
          pb: 1.5,
          borderBottom: "1px solid rgba(148,163,184,0.32)",
        }}
      >
        {/* Home team */}
        <Box>
          <Typography sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.2 }}>
            {home.team}
          </Typography>
          {pitcherData?.home_pitcher && (
            <Box sx={{ mt: 0.25 }}>
              <Typography sx={{ fontSize: "0.86rem", color: "#5b7cff", fontStyle: "italic" }}>
                {pitcherData.home_pitcher}
              </Typography>
              {pitcherData.home_pitcher_stats && (
                <Typography sx={{ fontSize: "0.82rem", color: "#5b7cff", fontStyle: "italic" }}>
                  {pitcherData.home_pitcher_stats}
                </Typography>
              )}
            </Box>
          )}
          <Typography sx={{ fontSize: "0.88rem", color: "#64748b", mt: 0.25 }}>Home</Typography>
        </Box>

        {/* Status / score */}
        <Box sx={{ textAlign: "center", px: 1 }}>
          <Typography sx={{ fontWeight: 700, fontSize: "0.78rem", color: "#334155", whiteSpace: "nowrap" }}>
            {statusLabel}
          </Typography>
          {isGameOver && (
            <Typography sx={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.06em", color: "#64748b" }}>
              FINAL
            </Typography>
          )}
        </Box>

        {/* Away team */}
        <Box sx={{ textAlign: "right" }}>
          <Typography sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.2 }}>
            {away.team}
          </Typography>
          {pitcherData?.away_pitcher && (
            <Box sx={{ mt: 0.25 }}>
              <Typography sx={{ fontSize: "0.86rem", color: "#5b7cff", fontStyle: "italic" }}>
                {pitcherData.away_pitcher}
              </Typography>
              {pitcherData.away_pitcher_stats && (
                <Typography sx={{ fontSize: "0.82rem", color: "#5b7cff", fontStyle: "italic" }}>
                  {pitcherData.away_pitcher_stats}
                </Typography>
              )}
            </Box>
          )}
          <Typography sx={{ fontSize: "0.88rem", color: "#64748b", mt: 0.25 }}>Away</Typography>
        </Box>
      </Box>

      {/* Odds rows */}
      {!isGameOver && (
        <Box sx={{ display: "grid", gap: 1 }}>
          {/* H2H */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
              {formatH2H(home.odds?.h2h)}
              {draw?.h2h !== null && draw?.h2h !== undefined && (
                <Typography component="span" sx={{ fontSize: "0.86rem", color: "#64748b", ml: 0.5 }}>
                  Draw: {formatH2H(draw.h2h)}
                </Typography>
              )}
            </Typography>
            <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase", textAlign: "center" }}>
              H2H
            </Typography>
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155", textAlign: "right" }}>
              {formatH2H(away.odds?.h2h)}
            </Typography>
          </Box>

          {/* Spread */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
              {formatOdds(home.odds?.spread_point ?? null, home.odds?.spread_price ?? null)}
            </Typography>
            <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase", textAlign: "center" }}>
              Spread
            </Typography>
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155", textAlign: "right" }}>
              {formatOdds(away.odds?.spread_point ?? null, away.odds?.spread_price ?? null)}
            </Typography>
          </Box>

          {/* Total */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: 1,
              alignItems: "center",
              px: 1,
              py: 0.75,
              borderRadius: "9px",
              background: "rgba(255,255,255,0.68)",
            }}
          >
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155" }}>
              {totals?.over_point != null
                ? `Over ${formatOdds(totals.over_point, totals.over_price ?? null)}`
                : "N/A"}
            </Typography>
            <Typography sx={{ fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", textTransform: "uppercase", textAlign: "center" }}>
              Total
            </Typography>
            <Typography sx={{ fontSize: "0.98rem", fontWeight: 600, color: "#334155", textAlign: "right" }}>
              {totals?.under_point != null
                ? `Under ${formatOdds(totals.under_point, totals.under_price ?? null)}`
                : "N/A"}
            </Typography>
          </Box>
        </Box>
      )}

      {/* View Details button */}
      {detailsLink && (
        <Box sx={{ mt: 0.5, textAlign: "center" }}>
          <Button
            component={Link}
            to={detailsLink}
            variant="contained"
            onClick={onViewDetails}
            size="small"
            sx={{
              px: 3,
              py: 0.75,
              fontWeight: 600,
              fontSize: "0.98rem",
              textTransform: "none",
              borderRadius: "10px",
              textDecoration: "none",
              background: "#1976d2;",
              "&:hover": { background: "#1565c0" },
            }}
          >
            View Details
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default GameOdds;
