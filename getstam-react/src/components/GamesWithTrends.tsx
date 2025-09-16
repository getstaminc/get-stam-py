import React from "react";
import { Box, Typography, Paper, Button, Chip, Stack, FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import { Link, useLocation } from "react-router-dom";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";
import GameOdds from "./GameOdds";
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';

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

const getTrendColor = (trendType: string): 'success' | 'error' | 'warning' | 'info' => {
  switch (trendType) {
    case 'win_streak':
    case 'cover_streak':
    case 'over_streak':
      return 'success';
    case 'loss_streak':
    case 'no_cover_streak':
    case 'under_streak':
      return 'error';
    default:
      return 'info';
  }
};

const getTrendIcon = (trendType: string) => {
  switch (trendType) {
    case 'win_streak':
    case 'cover_streak':
    case 'over_streak':
      return <TrendingUpIcon fontSize="small" />;
    case 'loss_streak':
    case 'no_cover_streak':
    case 'under_streak':
      return <TrendingDownIcon fontSize="small" />;
    default:
      return null;
  }
};

const TrendChip: React.FC<{ trend: TrendResult }> = ({ trend }) => {
  const icon = getTrendIcon(trend.type);
  return (
    <Chip
      icon={icon || undefined}
      label={trend.description}
      color={getTrendColor(trend.type)}
      size="small"
      variant="outlined"
      sx={{ fontSize: '0.75rem' }}
    />
  );
};

const TeamTrends: React.FC<{ teamName: string; trends: TrendResult[] }> = ({ teamName, trends }) => {
  if (trends.length === 0) return null;
  
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, color: '#1976d2' }}>
        {teamName} Trends:
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {trends.map((trend, index) => (
          <TrendChip key={index} trend={trend} />
        ))}
      </Stack>
    </Box>
  );
};

const GamesWithTrends: React.FC<GamesWithTrendsProps> = ({ 
  gamesWithTrends, 
  loading, 
  onViewDetails,
  minTrendLength,
  onMinTrendLengthChange,
  getPitcherDataForGame
}) => {
  const location = useLocation();
  
  // Helper function to extract sport from URL path (e.g. "/nfl" → "nfl")
  const getSportFromPath = (pathname: string): string => {
    const match = pathname.match(/^\/([^/]+)/);
    return match ? match[1] : "nfl";
  };
  
  const urlSport = getSportFromPath(location.pathname);
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <Typography>Analyzing trends...</Typography>
      </Box>
    );
  }

  // Filter games to only show those with trends of the minimum length or higher
  const filterTrendsByLength = (trends: TrendResult[]): TrendResult[] => {
    return trends.filter(trend => trend.count >= minTrendLength);
  };

  const gamesWithFilteredTrends = gamesWithTrends.map(gameWithTrends => {
    const filteredHomeTeamTrends = filterTrendsByLength(gameWithTrends.homeTeamTrends);
    const filteredAwayTeamTrends = filterTrendsByLength(gameWithTrends.awayTeamTrends);
    const filteredHeadToHeadTrends = filterTrendsByLength(gameWithTrends.headToHeadTrends);
    
    const hasFilteredTrends = filteredHomeTeamTrends.length > 0 || 
                              filteredAwayTeamTrends.length > 0 || 
                              filteredHeadToHeadTrends.length > 0;
    
    return {
      ...gameWithTrends,
      homeTeamTrends: filteredHomeTeamTrends,
      awayTeamTrends: filteredAwayTeamTrends,
      headToHeadTrends: filteredHeadToHeadTrends,
      hasTrends: hasFilteredTrends
    };
  });

  const gamesWithActiveTrends = gamesWithFilteredTrends.filter(gameWithTrends => gameWithTrends.hasTrends);

  if (gamesWithActiveTrends.length === 0) {
    return (
      <Box>
        {/* Trend Length Filter */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ color: '#1976d2', fontWeight: 'bold' }}>
            Games with Strong Trends
          </Typography>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Minimum Trend Length</InputLabel>
            <Select
              value={minTrendLength}
              label="Minimum Trend Length"
              onChange={(e) => onMinTrendLengthChange(e.target.value as number)}
            >
              <MenuItem value={3}>3+ Games</MenuItem>
              <MenuItem value={4}>4+ Games</MenuItem>
              <MenuItem value={5}>5+ Games</MenuItem>
              <MenuItem value={6}>6+ Games</MenuItem>
              <MenuItem value={7}>7+ Games</MenuItem>
              <MenuItem value={8}>8+ Games</MenuItem>
              <MenuItem value={9}>9+ Games</MenuItem>
              <MenuItem value={10}>10+ Games</MenuItem>
            </Select>
          </FormControl>
        </Box>
        
        <Box sx={{ textAlign: 'center', mt: 4 }}>
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
      {/* Trend Length Filter */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Games with Strong Trends ({gamesWithActiveTrends.length} found)
        </Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Minimum Trend Length</InputLabel>
          <Select
            value={minTrendLength}
            label="Minimum Trend Length"
            onChange={(e) => onMinTrendLengthChange(e.target.value as number)}
          >
            <MenuItem value={3}>3+ Games</MenuItem>
            <MenuItem value={4}>4+ Games</MenuItem>
            <MenuItem value={5}>5+ Games</MenuItem>
          </Select>
        </FormControl>
      </Box>
      
      {gamesWithActiveTrends.map((gameWithTrends) => {
        const { game, homeTeamTrends, awayTeamTrends, headToHeadTrends } = gameWithTrends;
        const homeTeam = game.home?.team || game.home_team_name || 'Home';
        const awayTeam = game.away?.team || game.away_team_name || 'Away';
        
        return (
          <Paper 
            key={game.game_id} 
            elevation={3} 
            sx={{ 
              mb: 3, 
              p: 2, 
              borderRadius: 2, 
              backgroundColor: "#f9f9f9",
              border: '2px solid #e3f2fd'
            }}
          >
            <GameOdds
              game={{
                home: game.home,
                away: game.away,
                totals: game.totals,
              }}
              pitcherData={getPitcherDataForGame?.(game)}
            />
            
            {/* Trends Display */}
            <Box sx={{ mt: 3, p: 2, backgroundColor: '#fafafa', borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 2, color: '#1976d2' }}>
                🔥 Active Trends
              </Typography>
              
              <TeamTrends teamName={homeTeam} trends={homeTeamTrends} />
              <TeamTrends teamName={awayTeam} trends={awayTeamTrends} />
              
              {headToHeadTrends.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, color: '#1976d2' }}>
                    Head-to-Head Trends:
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {headToHeadTrends.map((trend: TrendResult, index: number) => (
                      <TrendChip key={index} trend={trend} />
                    ))}
                  </Stack>
                </Box>
              )}
            </Box>
            
            <Box sx={{ mt: 3, textAlign: "center" }}>
              <Button
                component={Link}
                to={`/game-details/${urlSport}?game_id=${game.game_id}`}
                variant="contained"
                color="primary"
                onClick={() => onViewDetails(game)}
                size="medium"
                sx={{
                  px: 3,
                  py: 1,
                  fontWeight: 600,
                  fontSize: "1rem",
                  textTransform: "none",
                  borderRadius: 2,
                  textDecoration: "none"
                }}
              >
                View Details
              </Button>
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
};

export default GamesWithTrends;
