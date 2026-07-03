import React from "react";
import { Box, Typography, Button } from "@mui/material";
import { Link } from "react-router-dom";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { TrendResult } from "../utils/trendAnalysis";
import { getTeamPageLink } from "../utils/teamSlugUtils";
import PlayerStreaksStrip, { TeamStreaks } from "./PlayerStreaksStrip";

export interface TrendInsightCardProps {
  game: any;
  trends: TrendResult[]; // pre-sorted descending by count
  pitcherData?: {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  };
  detailsLink: string;
  sport: string;
  onViewDetails?: () => void;
  playerStreaks?: TeamStreaks[];
}

const POSITIVE_TYPES = new Set(["win_streak", "cover_streak", "over_streak"]);

// Extract a short title and concise context string from the enriched description.
// Full description format: "{label} — {historical context} — {team role or fav/dog stats}"
const parseDescription = (description: string) => {
  const parts = description.split(" — ");
  const title = parts[0];
  if (parts.length < 2) return { title, context: "" };

  const pctMatch = parts.slice(1).join(" — ").match(/continues (\d+%) of the time/i);
  const pct = pctMatch ? pctMatch[1] : null;

  // Last segment is the team role or fav/dog breakdown; strip "(Team today)" annotations
  const lastPart = parts.length >= 3 ? parts[parts.length - 1] : "";
  const cleanedLast = lastPart.replace(/ \([^)]+? today\)/g, "").trim();

  let context = "";
  if (pct && cleanedLast) context = `Continues ${pct} of the time • ${cleanedLast}`;
  else if (pct) context = `Continues ${pct} of the time`;
  else if (cleanedLast) context = cleanedLast.charAt(0).toUpperCase() + cleanedLast.slice(1);

  return { title, context };
};

export const getConfidenceScore = (trend: TrendResult): number => {
  const { continuation_rate, sample_size = 0, count } = trend;
  if (continuation_rate != null && sample_size >= 5) {
    const deviation = Math.abs(continuation_rate - 0.5);
    if (deviation >= 0.15 && sample_size >= 10) return 4;
    if (deviation >= 0.08 && sample_size >= 5)  return 3;
    if (deviation >= 0.04)                       return 2;
    return 1;
  }
  if (count >= 7) return 1;
  if (count >= 5) return 0.5;
  return 0;
};

export const getConfidence = (trend: TrendResult): { label: string; color: string } | null => {
  const { continuation_rate, sample_size = 0, count } = trend;

  if (continuation_rate != null && sample_size >= 5) {
    if (continuation_rate < 0.5) return null; // below 50% = likely to break; percentage shows it
    const deviation = continuation_rate - 0.5;
    if (deviation >= 0.15 && sample_size >= 10) return { label: "High Confidence", color: "#d97706" };
    if (deviation >= 0.08 && sample_size >= 5)  return { label: "Good Confidence", color: "#16a34a" };
    if (deviation >= 0.04)                       return { label: "Moderate",        color: "#64748b" };
    return null;
  }

  // Fallback to streak length when no stats available
  if (count >= 7) return { label: "High Confidence", color: "#d97706" };
  if (count >= 5) return { label: "Good Confidence", color: "#16a34a" };
  return null;
};

const fmt = (n: number | null | undefined, prefix = false): string => {
  if (n == null) return "N/A";
  return prefix && n > 0 ? `+${n}` : String(n);
};

const fmtOdds = (point?: number | null, price?: number | null): string => {
  if (point == null && price == null) return "N/A";
  if (point == null) return price != null ? fmt(price, true) : "N/A";
  const ps = fmt(point, true);
  return price != null ? `${ps} (${fmt(price, true)})` : ps;
};

const OddsRow: React.FC<{ left: string; label: string; right: string; sub?: string }> = ({ left, label, right, sub }) => (
  <Box sx={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 1, alignItems: "center", py: 0.75 }}>
    <Box>
      <Typography sx={{ fontSize: "0.96rem", fontWeight: 600, color: "#334155" }}>{left}</Typography>
      {sub && <Typography sx={{ fontSize: "0.75rem", color: "#94a3b8" }}>{sub}</Typography>}
    </Box>
    <Typography sx={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.06em", color: "#94a3b8", textTransform: "uppercase", textAlign: "center", minWidth: 56 }}>
      {label}
    </Typography>
    <Typography sx={{ fontSize: "0.96rem", fontWeight: 600, color: "#334155", textAlign: "right" }}>{right}</Typography>
  </Box>
);

const TrendInsightCard: React.FC<TrendInsightCardProps> = ({ game, trends, pitcherData, detailsLink, sport, onViewDetails, playerStreaks }) => {
  const { home, away, totals, draw } = game;
  if (trends.length === 0) return null;

  const hasScore = home.score != null && away.score != null;
  const noOdds =
    (!home.odds || (home.odds.h2h == null && home.odds.spread_point == null)) &&
    (!away.odds || (away.odds.h2h == null && away.odds.spread_point == null)) &&
    (!totals || (totals.over_point == null && totals.under_point == null));
  const isGameOver = hasScore && noOdds;

  if (noOdds) return null;

  const statusLabel = hasScore ? `${home.score} - ${away.score}` : "Scheduled";
  const gameTime = !hasScore && game.commence_time
    ? new Date(game.commence_time).toLocaleString("en-US", {
        month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
        timeZone: "America/New_York", timeZoneName: "short",
      })
    : null;

  return (
    <Box sx={{ background: "#fff", border: "1px solid rgba(220,227,234,0.95)", borderRadius: "18px", boxShadow: "0 8px 24px rgba(15,23,42,0.07)", overflow: "hidden", display: "flex", flexDirection: "column" }}>

      {/* Team header */}
      <Box sx={{ px: 2, pt: 2, pb: 1.5, display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 1, alignItems: "start" }}>
        {/* Home */}
        <Box>
          <Link to={getTeamPageLink(sport, home.team)} style={{ textDecoration: "none", color: "inherit" }}>
            <Typography sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.2, "&:hover": { color: "#1976d2" }, cursor: "pointer" }}>
              {home.team}
            </Typography>
          </Link>
          {pitcherData?.home_pitcher && (
            <Typography sx={{ fontSize: "0.8rem", color: "#5b7cff", fontStyle: "italic", mt: 0.25 }}>
              {pitcherData.home_pitcher}{pitcherData.home_pitcher_stats ? ` · ${pitcherData.home_pitcher_stats}` : ""}
            </Typography>
          )}
          <Typography sx={{ fontSize: "0.82rem", color: "#94a3b8", mt: 0.25 }}>Home</Typography>
        </Box>

        {/* Status pill */}
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", pt: 0.5 }}>
          <Box sx={{ px: 1.5, py: 0.35, borderRadius: "999px", border: "1px solid #e2e8f0", bgcolor: "#f8fafc" }}>
            <Typography sx={{ fontSize: "0.72rem", fontWeight: 700, color: "#475569", whiteSpace: "nowrap" }}>{statusLabel}</Typography>
          </Box>
          {isGameOver && (
            <Typography sx={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.08em", color: "#94a3b8", mt: 0.25 }}>FINAL</Typography>
          )}
          {gameTime && (
            <Typography sx={{ fontSize: "0.7rem", color: "#94a3b8", mt: 0.25, whiteSpace: "nowrap" }}>{gameTime}</Typography>
          )}
        </Box>

        {/* Away */}
        <Box sx={{ textAlign: "right" }}>
          <Link to={getTeamPageLink(sport, away.team)} style={{ textDecoration: "none", color: "inherit" }}>
            <Typography sx={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.2, "&:hover": { color: "#1976d2" }, cursor: "pointer" }}>
              {away.team}
            </Typography>
          </Link>
          {pitcherData?.away_pitcher && (
            <Typography sx={{ fontSize: "0.8rem", color: "#5b7cff", fontStyle: "italic", mt: 0.25, textAlign: "right" }}>
              {pitcherData.away_pitcher}{pitcherData.away_pitcher_stats ? ` · ${pitcherData.away_pitcher_stats}` : ""}
            </Typography>
          )}
          <Typography sx={{ fontSize: "0.82rem", color: "#94a3b8", mt: 0.25, textAlign: "right" }}>Away</Typography>
        </Box>
      </Box>

      {/* Trend insight boxes */}
      <Box sx={{ mx: 2, mb: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
        {trends.map((trend, idx) => {
          const positive = POSITIVE_TYPES.has(trend.type);
          const trendColor = positive ? "#16a34a" : "#dc2626";
          const { title, context } = parseDescription(trend.description);
          const confidence = getConfidence(trend);
          return (
            <Box key={idx} sx={{
              px: 1.5, py: 1.25,
              background: positive ? "#f0fdf4" : "#fff5f5",
              borderRadius: "12px",
              border: `1px solid ${positive ? "#bbf7d0" : "#fecaca"}`,
              display: "flex", alignItems: "center", gap: 1.25,
            }}>
              <Box sx={{
                width: 38, height: 38, borderRadius: "50%",
                background: positive ? "#dcfce7" : "#fee2e2",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}>
                {positive
                  ? <TrendingUpIcon sx={{ color: "#16a34a", fontSize: 20 }} />
                  : <TrendingDownIcon sx={{ color: "#dc2626", fontSize: 20 }} />}
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontWeight: 800, fontSize: "0.88rem", color: trendColor, lineHeight: 1.3 }}>
                  {title}
                </Typography>
                {context && (
                  <Typography sx={{ fontSize: "0.75rem", color: "#64748b", mt: 0.3, lineHeight: 1.4 }}>
                    {context}
                  </Typography>
                )}
              </Box>
              {confidence && (
                <Box sx={{
                  px: 0.9, py: 0.4,
                  borderRadius: "999px",
                  border: `1.5px solid ${confidence.color}`,
                  color: confidence.color,
                  fontSize: "0.58rem",
                  fontWeight: 800,
                  letterSpacing: "0.07em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                }}>
                  {confidence.label}
                </Box>
              )}
            </Box>
          );
        })}

        {playerStreaks && playerStreaks.some(g => g.streaks.length > 0) && (
          <Box sx={{ pt: 0.5 }}>
            <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", mb: 0.75 }}>
              Player Streaks
            </Typography>
            <PlayerStreaksStrip groups={playerStreaks} />
          </Box>
        )}
      </Box>

      {/* Divider + Odds */}
      {!isGameOver && (
        <Box sx={{ px: 2, borderTop: "1px solid rgba(148,163,184,0.18)", pt: 0.5 }}>
          <OddsRow
            left={fmt(home.odds?.h2h, true)}
            label="H2H"
            right={fmt(away.odds?.h2h, true)}
            sub={draw?.h2h != null ? `Draw: ${fmt(draw.h2h, true)}` : undefined}
          />
          <OddsRow
            left={fmtOdds(home.odds?.spread_point, home.odds?.spread_price)}
            label="Spread"
            right={fmtOdds(away.odds?.spread_point, away.odds?.spread_price)}
          />
          <OddsRow
            left={totals?.over_point != null ? `Over ${fmtOdds(totals.over_point, totals.over_price)}` : "N/A"}
            label="Total"
            right={totals?.under_point != null ? `Under ${fmtOdds(totals.under_point, totals.under_price)}` : "N/A"}
          />
        </Box>
      )}

      {/* Button */}
      <Box sx={{ px: 2, pt: 1, pb: 1.5, display: "flex", justifyContent: "flex-end" }}>
        <Button
          component={Link}
          to={detailsLink}
          onClick={onViewDetails}
          sx={{ height: 36, px: "16px", borderRadius: "999px", background: "#1976d2", color: "#fff", fontSize: "0.875rem", fontWeight: 700, textTransform: "none", "&:hover": { background: "#1565c0" } }}
        >
          Game Details
        </Button>
      </Box>
    </Box>
  );
};

export default TrendInsightCard;
