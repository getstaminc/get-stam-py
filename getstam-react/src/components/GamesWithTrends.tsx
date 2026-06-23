import React from "react";
import {
  Box,
  Chip,
  Stack,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from "@mui/material";
import { Link, useLocation } from "react-router-dom";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";
import { encodeGameId } from "../utils/gameIdCrypto";
import GameOdds from "./GameOdds";

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

const getTrendColor = (type: string): "success" | "error" | "info" => {
  if (["win_streak", "cover_streak", "over_streak"].includes(type)) return "success";
  if (["loss_streak", "no_cover_streak", "under_streak"].includes(type)) return "error";
  return "info";
};

const getTrendIcon = (type: string): React.ReactElement | undefined => {
  if (["win_streak", "cover_streak", "over_streak"].includes(type))
    return <TrendingUpIcon fontSize="small" />;
  if (["loss_streak", "no_cover_streak", "under_streak"].includes(type))
    return <TrendingDownIcon fontSize="small" />;
  return undefined;
};

const TrendChip: React.FC<{ trend: TrendResult }> = ({ trend }) => {
  const sepIdx = trend.description.indexOf(" — ");
  const label = sepIdx >= 0 ? trend.description.slice(0, sepIdx) : trend.description;
  const context = sepIdx >= 0 ? trend.description.slice(sepIdx + 3) : "";
  return (
    <Box>
      <Chip
        icon={getTrendIcon(trend.type)}
        label={label}
        color={getTrendColor(trend.type)}
        size="small"
        variant="outlined"
        sx={{ fontSize: "0.75rem" }}
      />
      {context && (
        <Typography sx={{ fontSize: "0.78rem", color: "#555", mt: 0.5, pl: 0.5, lineHeight: 1.45 }}>
          {context.charAt(0).toUpperCase() + context.slice(1)}
        </Typography>
      )}
    </Box>
  );
};

const TrendFilter: React.FC<{ value: number; onChange: (v: number) => void; sport: string }> = ({ value, onChange, sport }) => {
  const minAllowed = sport === "mlb" ? 5 : 3;
  const options = [3, 4, 5].filter((n) => n >= minAllowed);
  return (
    <FormControl size="small" sx={{ minWidth: 180 }}>
      <InputLabel>Min Trend Length</InputLabel>
      <Select value={value} label="Min Trend Length" onChange={(e) => onChange(e.target.value as number)}>
        {options.map((n) => (
          <MenuItem key={n} value={n}>{n}+ Games</MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

interface TrendGameCardProps {
  gwt: GameWithTrends;
  urlSport: string;
  onViewDetails: (game: any) => void;
  getPitcherDataForGame?: (game: any) => any;
}

const TrendGameCard: React.FC<TrendGameCardProps> = ({ gwt, urlSport, onViewDetails, getPitcherDataForGame }) => {
  const [expanded, setExpanded] = React.useState(false);
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

  const visibleTrends = expanded ? allTrends : allTrends.slice(0, 2);
  const hiddenCount = allTrends.length - 2;

  return (
    <Box
      sx={{
        background: "#fff",
        border: "1px solid rgba(220,227,234,0.95)",
        borderRadius: "18px",
        boxShadow: "0 14px 34px rgba(28,42,31,.08)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ p: 2 }}>
        <GameOdds
          game={{
            home: game.home,
            away: game.away,
            totals: game.totals,
            ...(game.draw ? { draw: game.draw } : {}),
          }}
          pitcherData={getPitcherDataForGame?.(game)}
          sport={urlSport}
          sx={{ border: "none", boxShadow: "none", borderRadius: 0, p: 0, background: "transparent" }}
        />
      </Box>

      <Box
        sx={{
          borderTop: "1px solid #dce3ea",
          background: "linear-gradient(90deg, #e3f2fd, #fff 78%)",
          px: 2,
          py: 1.5,
          mt: "auto",
        }}
      >
        <Stack direction="column" gap={1} sx={{ mb: 1.5 }}>
          {visibleTrends.map((trend, i) => (
            <TrendChip key={i} trend={trend} />
          ))}
          {!expanded && hiddenCount > 0 && (
            <Typography
              onClick={() => setExpanded(true)}
              sx={{ fontSize: "0.78rem", color: "#1976d2", fontWeight: 600, pl: 0.5, cursor: "pointer", "&:hover": { textDecoration: "underline" } }}
            >
              +{hiddenCount} more
            </Typography>
          )}
        </Stack>
        <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
          <Button
            component={Link}
            to={`/game-details/${urlSport}?game_id=${encodeGameId(game.game_id)}`}
            onClick={() => onViewDetails(game)}
            sx={{
              height: 34,
              px: "13px",
              borderRadius: "999px",
              background: "#1976d2",
              color: "#fff",
              fontSize: "0.8125rem",
              fontWeight: 700,
              textTransform: "none",
              whiteSpace: "nowrap",
              "&:hover": { background: "#1565c0" },
            }}
          >
            Game Details
          </Button>
        </Box>
      </Box>
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

  const getSportFromPath = (pathname: string): string => {
    const match = pathname.match(/^\/([^/]+)/);
    return match ? match[1] : "nfl";
  };

  const urlSport = getSportFromPath(location.pathname);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <Typography>Analyzing trends...</Typography>
      </Box>
    );
  }

  const filterTrendsByLength = (trends: TrendResult[]): TrendResult[] =>
    trends.filter((t) => t.count >= minTrendLength);

  const gamesWithFilteredTrends = gamesWithTrends.map((gwt) => {
    const homeTeamTrends = filterTrendsByLength(gwt.homeTeamTrends);
    const awayTeamTrends = filterTrendsByLength(gwt.awayTeamTrends);
    const headToHeadTrends = filterTrendsByLength(gwt.headToHeadTrends);
    const homeTeamHomeTrends = filterTrendsByLength(gwt.homeTeamHomeTrends || []);
    const awayTeamAwayTrends = filterTrendsByLength(gwt.awayTeamAwayTrends || []);
    const homeAtHomeH2HTrends = filterTrendsByLength(gwt.homeAtHomeH2HTrends || []);

    const hasTrends =
      homeTeamTrends.length > 0 ||
      awayTeamTrends.length > 0 ||
      headToHeadTrends.length > 0 ||
      homeTeamHomeTrends.length > 0 ||
      awayTeamAwayTrends.length > 0 ||
      homeAtHomeH2HTrends.length > 0;

    return {
      ...gwt,
      homeTeamTrends,
      awayTeamTrends,
      headToHeadTrends,
      homeTeamHomeTrends,
      awayTeamAwayTrends,
      homeAtHomeH2HTrends,
      hasTrends,
    };
  });

  const gamesWithActiveTrends = gamesWithFilteredTrends.filter((gwt) => gwt.hasTrends);

  if (gamesWithActiveTrends.length === 0) {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h6" sx={{ color: "#1976d2", fontWeight: 700 }}>
            Games with Trends
          </Typography>
          <TrendFilter value={minTrendLength} onChange={onMinTrendLengthChange} sport={urlSport} />
        </Box>
        <Box sx={{ textAlign: "center", mt: 4 }}>
          <Typography variant="h6" color="text.secondary">
            No games with trends of {minTrendLength}+ games found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try lowering the minimum trend length or check a different date.
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h6" sx={{ color: "#1976d2", fontWeight: 700 }}>
          Games with Trends ({gamesWithActiveTrends.length})
        </Typography>
        <TrendFilter value={minTrendLength} onChange={onMinTrendLengthChange} sport={urlSport} />
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
        {gamesWithActiveTrends.map((gwt) => (
          <TrendGameCard
            key={gwt.game.game_id}
            gwt={gwt}
            urlSport={urlSport}
            onViewDetails={onViewDetails}
            getPitcherDataForGame={getPitcherDataForGame}
          />
        ))}
      </Box>
    </Box>
  );
};

export default GamesWithTrends;
