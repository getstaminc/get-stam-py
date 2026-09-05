import React, { useState } from "react";
import { Box, Typography, FormControl, InputLabel, Select, MenuItem, Tooltip, Link } from "@mui/material";
import LockIcon from "@mui/icons-material/Lock";
import { useLocation } from "react-router-dom";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";
import { encodeGameId } from "../utils/gameIdCrypto";
import { getMatchupPageLink, MATCHUP_SLUG_SPORTS } from "../utils/teamSlugUtils";
import TrendInsightCard, { getConfidenceScore } from "./TrendInsightCard";
import { useAuth } from "../contexts/AuthContext";
import UpgradeDialog from "./UpgradeDialog";

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

// Above this length, MLB's filter is a Pro-only feature — free/anonymous users stay capped at 5+.
const MLB_FREE_MAX = 5;

const TrendFilter: React.FC<{ value: number; onChange: (v: number) => void; sport: string }> = ({ value, onChange, sport }) => {
  const { isPro } = useAuth();
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);

  const minAllowed = sport === "mlb" ? 5 : 3;
  const allOptions = sport === "mlb" ? [5, 7, 10] : [3, 4, 5];
  const options = allOptions.filter((n) => n >= minAllowed);
  const showUpgrade = sport === "mlb" && !isPro;

  const handleUpgradeClick = () => setUpgradeDialogOpen(true);

  // Locked options aren't marked MUI-`disabled` — a disabled MenuItem needed a pointer-events
  // override for its tooltip to work, which let clicks slip through and actually select it.
  // Instead: they're fully clickable, but the change handler intercepts a locked selection and
  // opens the Upgrade dialog instead of applying it, so the Select's value never actually changes.
  const handleSelectChange = (newValue: number) => {
    if (newValue > MLB_FREE_MAX && !isPro) {
      setUpgradeDialogOpen(true);
      return;
    }
    onChange(newValue);
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <FormControl size="small" sx={{ minWidth: 180 }}>
        <InputLabel>Min Trend Length</InputLabel>
        <Select value={value} label="Min Trend Length" onChange={(e) => handleSelectChange(e.target.value as number)}>
          {options.map((n) => {
            const locked = n > MLB_FREE_MAX && !isPro;
            return (
              <MenuItem key={n} value={n}>
                {locked ? (
                  <Tooltip title="Upgrade to Pro to unlock" placement="right">
                    <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5, color: "text.disabled" }}>
                      {n}+ Games <LockIcon fontSize="inherit" />
                    </Box>
                  </Tooltip>
                ) : (
                  `${n}+ Games`
                )}
              </MenuItem>
            );
          })}
        </Select>
      </FormControl>
      {showUpgrade && (
        <Link component="button" type="button" variant="body2" onClick={handleUpgradeClick}>
          Upgrade
        </Link>
      )}
      <UpgradeDialog open={upgradeDialogOpen} onClose={() => setUpgradeDialogOpen(false)} />
    </Box>
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

  const getTopTrends = (gwt: GameWithTrends) => [
    ...(gwt.headToHeadTrends || []),
    ...(gwt.homeAtHomeH2HTrends || []),
    ...(gwt.homeTeamHomeTrends || []),
    ...(gwt.awayTeamAwayTrends || []),
    ...(gwt.homeTeamTrends || []),
    ...(gwt.awayTeamTrends || []),
  ].sort((a, b) => b.count - a.count);

  const gameScore = (gwt: GameWithTrends) =>
    Math.max(0, ...getTopTrends(gwt).map(t => getConfidenceScore(t)));

  const sorted = [...filtered].sort((a, b) => gameScore(b) - gameScore(a));

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h6" sx={{ color: "#1976d2", fontWeight: 700 }}>
          Games with Trends ({filtered.length})
        </Typography>
        <TrendFilter value={minTrendLength} onChange={onMinTrendLengthChange} sport={urlSport} />
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
        {sorted.map((gwt) => {
          const { game } = gwt;
          const allTrends = [
            ...(gwt.headToHeadTrends || []),
            ...(gwt.homeAtHomeH2HTrends || []),
            ...(gwt.homeTeamHomeTrends || []),
            ...(gwt.awayTeamAwayTrends || []),
            ...(gwt.homeTeamTrends || []),
            ...(gwt.awayTeamTrends || []),
          ].sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);

          if (allTrends.length === 0) return null;

          const detailsLink =
            MATCHUP_SLUG_SPORTS.has(urlSport) && game.home?.team && game.away?.team && game.commence_time
              ? getMatchupPageLink(urlSport, game.away.team, game.home.team, game.commence_time)
              : `/game-details/${urlSport}?game_id=${encodeGameId(game.game_id)}`;

          return (
            <TrendInsightCard
              key={game.game_id}
              game={{ home: game.home, away: game.away, totals: game.totals, ...(game.draw ? { draw: game.draw } : {}) }}
              trends={allTrends}
              pitcherData={getPitcherDataForGame?.(game)}
              detailsLink={detailsLink}
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
