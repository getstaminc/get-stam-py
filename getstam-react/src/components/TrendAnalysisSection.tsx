import React from "react";
import { Box, Typography, CircularProgress } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";
import { getConfidenceScore, getConfidence } from "./TrendInsightCard";

interface TrendAnalysisSectionProps {
  gameTrends: GameWithTrends | null;
  loading: boolean;
  game: any;
  minTrendLength: number;
  dataSinceYear?: number | null;
}

const POSITIVE_TYPES = new Set(["win_streak", "cover_streak", "over_streak"]);

// Build the full rich text for the detail page (reconstruct from description parts)
const parseFullDescription = (description: string) => {
  const parts = description.split(" — ");
  const title = parts[0];
  if (parts.length < 2) return { title, fullContext: "" };

  // Capitalize first letter of each part and join cleanly
  const contextParts = parts.slice(1).map((p, i) => {
    const clean = p.replace(/ \([^)]+? today\)/g, (match) => {
      // Keep "(Team today)" but strip the " today" to make it cleaner
      return match.replace(" today", "");
    }).trim();
    return i === 0 ? clean.charAt(0).toUpperCase() + clean.slice(1) : clean.charAt(0).toUpperCase() + clean.slice(1);
  });

  return { title, fullContext: contextParts.join(" — ") };
};

const TrendDetailCard: React.FC<{ trend: TrendResult; dataSinceYear?: number | null }> = ({ trend, dataSinceYear }) => {
  const positive = POSITIVE_TYPES.has(trend.type);
  const trendColor = positive ? "#16a34a" : "#dc2626";
  const borderColor = positive ? "#bbf7d0" : "#fecaca";
  const bgColor = positive ? "#f0fdf4" : "#fff5f5";
  const confidence = getConfidence(trend);
  const { title, fullContext } = parseFullDescription(trend.description);

  const { continuation_rate, sample_size } = trend;
  const pct = continuation_rate != null ? Math.round(continuation_rate * 100) : null;
  const continued = continuation_rate != null && sample_size != null
    ? Math.round(continuation_rate * sample_size)
    : null;

  return (
    <Box sx={{
      px: 2, py: 2,
      background: bgColor,
      borderRadius: "14px",
      border: `1px solid ${borderColor}`,
    }}>
      {/* Header: icon + title + badges */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
        <Box sx={{
          width: 44, height: 44, borderRadius: "50%", flexShrink: 0, mt: 0.25,
          background: positive ? "#dcfce7" : "#fee2e2",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {positive
            ? <TrendingUpIcon sx={{ color: "#16a34a", fontSize: 24 }} />
            : <TrendingDownIcon sx={{ color: "#dc2626", fontSize: 24 }} />}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          {confidence && (
            <Box sx={{
              display: "inline-block", mb: 0.5,
              px: 0.9, py: 0.3, borderRadius: "999px",
              border: `1.5px solid ${confidence.color}`, color: confidence.color,
              fontSize: "0.58rem", fontWeight: 800, letterSpacing: "0.07em", textTransform: "uppercase",
            }}>
              {confidence.label}
            </Box>
          )}
          <Typography sx={{ fontWeight: 800, fontSize: "0.95rem", color: trendColor, lineHeight: 1.3 }}>
            {title}
          </Typography>
        </Box>
      </Box>

      {/* Full prose context */}
      {fullContext && (
        <Typography sx={{ fontSize: "0.875rem", color: "#475569", lineHeight: 1.65, mt: 1.5, mb: pct != null ? 1.5 : 0 }}>
          {fullContext}
        </Typography>
      )}

      {/* Progress bar + sample count */}
      {pct != null && sample_size != null && sample_size >= 3 && (
        <Box>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", mb: 0.75 }}>
            <Typography sx={{ fontSize: "0.78rem", color: "#64748b" }}>
              {continued} out of {sample_size} historical instances{dataSinceYear ? ` since ${dataSinceYear}` : ""}
            </Typography>
            <Typography sx={{ fontSize: "1rem", fontWeight: 800, color: trendColor }}>
              {pct}%
            </Typography>
          </Box>
          <Box sx={{ height: 7, borderRadius: "999px", bgcolor: positive ? "#dcfce7" : "#fee2e2", overflow: "hidden" }}>
            <Box sx={{
              height: "100%",
              width: `${pct}%`,
              bgcolor: trendColor,
              borderRadius: "999px",
              transition: "width 0.6s ease",
            }} />
          </Box>
        </Box>
      )}
    </Box>
  );
};

const TrendAnalysisSection: React.FC<TrendAnalysisSectionProps> = ({ gameTrends, loading, game, minTrendLength, dataSinceYear }) => {
  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 1.5, pt: 4, pb: 2, maxWidth: 900, mx: "auto" }}>
        <CircularProgress size={20} />
        <Typography sx={{ color: "#64748b", fontSize: "0.875rem" }}>Loading trend analysis…</Typography>
      </Box>
    );
  }

  if (!gameTrends) return null;

  const { home, away, totals } = game;

  // Collect all trends, filter by minTrendLength, sort by confidence
  const allTrends: TrendResult[] = [
    ...(gameTrends.headToHeadTrends || []),
    ...(gameTrends.homeAtHomeH2HTrends || []),
    ...(gameTrends.homeTeamHomeTrends || []),
    ...(gameTrends.awayTeamAwayTrends || []),
    ...(gameTrends.homeTeamTrends || []),
    ...(gameTrends.awayTeamTrends || []),
  ]
    .filter(t => t.count >= minTrendLength)
    .sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);

  if (allTrends.length === 0) return null;

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", px: { xs: 2, sm: 3 }, pt: 4, mb: 2 }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2, color: "#1e293b" }}>
        Trend Analysis
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {allTrends.map((trend, idx) => (
          <TrendDetailCard key={idx} trend={trend} dataSinceYear={dataSinceYear} />
        ))}
      </Box>
    </Box>
  );
};

export default TrendAnalysisSection;
