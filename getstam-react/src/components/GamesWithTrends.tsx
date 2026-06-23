import React from "react";
import { Box, Typography, FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import { useLocation } from "react-router-dom";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";
import { encodeGameId } from "../utils/gameIdCrypto";
import TrendInsightCard from "./TrendInsightCard";

interface GamesWithTrendsProps {
  gamesWithTrends: GameWithTrends[];
  loading: boolean;
  onViewDetails: (game: any) => void;
  minTrendLength: number;
  onMinTrendLengthChange: (length: number) => void;
  getPitcherDataForGame?: (game: any) => {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  } | undefined;
}

const TrendFilter: React.FC<{ value: number; onChange: (v: number) => void; sport: string }> = ({ value, onChange, sport }) => {
  const minAllowed = sport === "mlb" ? 5 : 3;
  const options = [3, 4, 5].filter((n) => n >= minAllowed);
  return (
    <FormControl size="small" sx={{ minWidth: 180 }}>
      <InputLabel>Min Trend Length</InputLabel>
      <Select value={value} label="Min Trend Length" onChange={(e) => onChange(e.target.value as number)}>
        {options.map((n) => <MenuItem key={n} value={n}>{n}+ Games</MenuItem>)}
      </Select>
    </FormControl>
  );
};

const GamesWithTrends: React.FC<GamesWithTrendsProps> = ({
  gamesWithTrends,
  loading,
  onViewDetails,
  minTrendLength,
  onMinTrendLengthChange,
  getPitcherDataForGame,
}) => {
  const location = useLocation();
  const urlSport = location.pathname.match(/^\/([^/]+)/)?.[1] ?? "nfl";

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <Typography>Analyzing trends...</Typography>
      </Box>
    );
  }

  const filterByLength = (trends: TrendResult[]) => trends.filter((t) => t.count >= minTrendLength);

  const filtered = gamesWithTrends.map((gwt) => {
    const homeTeamTrends = filterByLength(gwt.homeTeamTrends);
    const awayTeamTrends = filterByLength(gwt.awayTeamTrends);
    const headToHeadTrends = filterByLength(gwt.headToHeadTrends);
    const homeTeamHomeTrends = filterByLength(gwt.homeTeamHomeTrends || []);
    const awayTeamAwayTrends = filterByLength(gwt.awayTeamAwayTrends || []);
    const homeAtHomeH2HTrends = filterByLength(gwt.homeAtHomeH2HTrends || []);
    const hasTrends =
      homeTeamTrends.length > 0 || awayTeamTrends.length > 0 || headToHeadTrends.length > 0 ||
      homeTeamHomeTrends.length > 0 || awayTeamAwayTrends.length > 0 || homeAtHomeH2HTrends.length > 0;
    return { ...gwt, homeTeamTrends, awayTeamTrends, headToHeadTrends, homeTeamHomeTrends, awayTeamAwayTrends, homeAtHomeH2HTrends, hasTrends };
  }).filter((gwt) => gwt.hasTrends);

  if (filtered.length === 0) {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h6" sx={{ color: "#1976d2", fontWeight: 700 }}>Games with Trends</Typography>
          <TrendFilter value={minTrendLength} onChange={onMinTrendLengthChange} sport={urlSport} />
        </Box>
        <Box sx={{ textAlign: "center", mt: 4 }}>
          <Typography variant="h6" color="text.secondary">No games with trends of {minTrendLength}+ games found</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Try lowering the minimum trend length or check a different date.</Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h6" sx={{ color: "#1976d2", fontWeight: 700 }}>
          Games with Trends ({filtered.length})
        </Typography>
        <TrendFilter value={minTrendLength} onChange={onMinTrendLengthChange} sport={urlSport} />
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
        {filtered.map((gwt) => {
          const { game } = gwt;
          const allTrends = [
            ...(gwt.headToHeadTrends || []),
            ...(gwt.homeAtHomeH2HTrends || []),
            ...(gwt.homeTeamHomeTrends || []),
            ...(gwt.awayTeamAwayTrends || []),
            ...(gwt.homeTeamTrends || []),
            ...(gwt.awayTeamTrends || []),
          ].sort((a, b) => b.count - a.count);

          if (allTrends.length === 0) return null;

          return (
            <TrendInsightCard
              key={game.game_id}
              game={{ home: game.home, away: game.away, totals: game.totals, ...(game.draw ? { draw: game.draw } : {}) }}
              trends={allTrends}
              pitcherData={getPitcherDataForGame?.(game)}
              detailsLink={`/game-details/${urlSport}?game_id=${encodeGameId(game.game_id)}`}
              sport={urlSport}
              onViewDetails={() => onViewDetails(game)}
            />
          );
        })}
      </Box>
    </Box>
  );
};

export default GamesWithTrends;
