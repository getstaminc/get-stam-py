import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Container,
  useTheme,
  alpha
} from "@mui/material";
import { GameData, SportType } from "../types/gameTypes";

interface PastGamesDisplayProps {
  selectedDate: string; // Format: YYYY-MM-DD
  sportType: SportType;
}

const PastGamesDisplay: React.FC<PastGamesDisplayProps> = ({
  selectedDate,
  sportType
}) => {
  const [games, setGames] = useState<GameData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();

  useEffect(() => {
    fetchPastGames();
  }, [selectedDate, sportType]);

  const fetchPastGames = async () => {
    setLoading(true);
    setError(null);

    try {
      const endpoint = getApiEndpoint();
      const response = await fetch(endpoint, {
        headers: {
          "X-API-KEY": process.env.REACT_APP_API_KEY || "",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch games: ${response.statusText}`);
      }

      const data = await response.json();
      setGames(data.games || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch games");
    } finally {
      setLoading(false);
    }
  };

  const getApiEndpoint = () => {
    const formattedDate = selectedDate.replace(/-/g, ''); // Convert YYYY-MM-DD to YYYYMMDD
    const baseUrl = "http://127.0.0.1:5000/api/historical";
    
    switch (sportType) {
      case 'mlb':
        return `${baseUrl}/mlb/games?start_date=${formattedDate}&end_date=${formattedDate}&limit=100`;
      case 'nfl':
        return `${baseUrl}/nfl/games?start_date=${formattedDate}&end_date=${formattedDate}&limit=100`;
      case 'ncaaf':
        return `${baseUrl}/ncaaf/games?limit=100`; // Adjust based on your NCAAF API structure
      case 'soccer':
        return `${baseUrl}/soccer/games?league=epl&start_date=${formattedDate}&end_date=${formattedDate}&limit=100`;
      default:
        return `${baseUrl}/${sportType}/games?start_date=${formattedDate}&end_date=${formattedDate}&limit=100`;
    }
  };

  const getScoreLabel = () => {
    switch (sportType) {
      case 'mlb': return 'Runs';
      case 'soccer': return 'Goals';
      default: return 'Points';
    }
  };

  const getTeamScore = (game: GameData, isHome: boolean) => {
    switch (sportType) {
      case 'mlb':
        return isHome ? game.home_runs : game.away_runs;
      case 'soccer':
        return isHome ? game.home_goals : game.away_goals;
      default:
        return isHome ? game.home_points : game.away_points;
    }
  };

  const getWinnerStyle = (homeScore: number, awayScore: number, isHome: boolean) => {
    const isWinner = isHome ? homeScore > awayScore : awayScore > homeScore;
    const isTie = homeScore === awayScore;
    
    if (isTie) {
      return {
        backgroundColor: alpha(theme.palette.grey[500], 0.1),
        fontWeight: 'bold'
      };
    }
    
    return {
      backgroundColor: isWinner 
        ? alpha(theme.palette.success.main, 0.1)
        : alpha(theme.palette.error.main, 0.05),
      fontWeight: isWinner ? 'bold' : 'normal',
      color: isWinner ? theme.palette.success.dark : theme.palette.text.secondary
    };
  };

  const getLineCoverageColor = (teamScore: number, line: number, opponentScore: number) => {
    if (teamScore === null || line === null || opponentScore === null) {
      return theme.palette.text.secondary;
    }
    
    const covered = (teamScore + line) > opponentScore;
    const push = (teamScore + line) === opponentScore;
    
    if (push) return theme.palette.grey[500];
    return covered ? theme.palette.success.main : theme.palette.error.main;
  };

  const getTotalColor = (total: number, actualScore: number) => {
    if (actualScore > total) {
      return theme.palette.success.main; // Green for over
    } else if (actualScore < total) {
      return theme.palette.error.main; // Red for under
    } else {
      return theme.palette.grey[500]; // Grey for push
    }
  };

  const formatDate = (dateString: string) => {
    try {
      // Handle both YYYY-MM-DD and YYYYMMDD formats
      let year, month, day;
      
      if (dateString.includes('-')) {
        [year, month, day] = dateString.split('-').map(num => parseInt(num));
      } else {
        year = parseInt(dateString.slice(0,4));
        month = parseInt(dateString.slice(4,6));
        day = parseInt(dateString.slice(6,8));
      }
      
      // Create date in local timezone to avoid UTC conversion issues
      const date = new Date(year, month - 1, day); // month is 0-indexed
      return date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100px" }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Loading games for {formatDate(selectedDate)}...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!games || games.length === 0) {
    return (
      <Alert severity="info">
        No games found for {formatDate(selectedDate)}
      </Alert>
    );
  }

  return (
    <Box sx={{ width: "100%", maxWidth: 900, mx: "auto" }}>
      <Typography 
        variant="h5" 
        component="h2" 
        gutterBottom 
        sx={{ 
          mb: 3, 
          textAlign: 'center',
          color: theme.palette.primary.main,
          fontWeight: 'bold'
        }}
      >
        {formatDate(selectedDate)} - {games.length} {sportType.toUpperCase()} Games
      </Typography>

      {/* Games List - One per row */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
        {games.map((game) => {
          const homeScore = getTeamScore(game, true) ?? 0;
          const awayScore = getTeamScore(game, false) ?? 0;
          
          return (
            <Card 
              key={game.game_id}
              elevation={3}
              sx={{ 
                transition: 'none' // Remove hover effects
              }}
            >
              <CardContent sx={{ p: 2 }}>
                {/* Game Header */}
                <Box display="flex" justifyContent="flex-start" alignItems="center" mb={1.5}>
                  <Box display="flex" gap={1}>
                    {game.playoffs && (
                      <Chip 
                        label="Playoffs" 
                        size="small" 
                        color="secondary" 
                      />
                    )}
                    {game.league && (
                      <Chip 
                        label={game.league} 
                        size="small" 
                        color="info" 
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>

                {/* Teams and Scores - Home team first */}
                <Box mb={2}>
                  {/* Home Team */}
                  <Box 
                    display="flex" 
                    justifyContent="space-between" 
                    alignItems="center"
                    sx={{
                      ...getWinnerStyle(homeScore, awayScore, true),
                      p: 1,
                      borderRadius: 1,
                      mb: 0.5
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="h6" component="div">
                        {game.home_team || 'Home Team'}
                      </Typography>
                      <Chip label="Home" size="small" sx={{ fontSize: '0.6rem', height: '18px' }} />
                    </Box>
                    <Typography variant="h5" component="div" fontWeight="bold">
                      {homeScore}
                    </Typography>
                  </Box>

                  {/* Away Team */}
                  <Box 
                    display="flex" 
                    justifyContent="space-between" 
                    alignItems="center"
                    sx={{
                      ...getWinnerStyle(homeScore, awayScore, false),
                      p: 1,
                      borderRadius: 1
                    }}
                  >
                    <Typography variant="h6" component="div">
                      {game.away_team || 'Away Team'}
                    </Typography>
                    <Typography variant="h5" component="div" fontWeight="bold">
                      {awayScore}
                    </Typography>
                  </Box>
                </Box>

                <Divider sx={{ mb: 1.5 }} />

                {/* Game Details - Three columns */}
                <Box display="flex" justifyContent="space-between" gap={2}>
                  {/* Total */}
                  <Box flex={1}>
                    <Typography variant="body2" color="text.secondary">
                      Total
                    </Typography>
                    <Typography 
                      variant="h6" 
                      fontWeight="bold"
                      sx={{ 
                        color: getTotalColor(game.total, homeScore + awayScore)
                      }}
                    >
                      {game.total}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Actual: {homeScore + awayScore}
                    </Typography>
                  </Box>

                  {/* Line Coverage */}
                  <Box flex={1}>
                    <Typography variant="body2" color="text.secondary">
                      Line Coverage
                    </Typography>
                    <Box>
                      <Typography 
                        variant="body2"
                        sx={{ 
                          color: getLineCoverageColor(homeScore, game.home_line, awayScore),
                          fontWeight: 'bold'
                        }}
                      >
                        {game.home_team?.slice(0, 8) || 'Home'}: {game.home_line > 0 ? '+' : ''}{game.home_line}
                      </Typography>
                      <Typography 
                        variant="body2"
                        sx={{ 
                          color: getLineCoverageColor(awayScore, game.away_line, homeScore),
                          fontWeight: 'bold'
                        }}
                      >
                        {game.away_team?.slice(0, 8) || 'Away'}: {game.away_line > 0 ? '+' : ''}{game.away_line}
                      </Typography>
                    </Box>
                  </Box>

                  {/* Starting Pitchers - Third column */}
                  {sportType === 'mlb' && (game.home_starting_pitcher || game.away_starting_pitcher) ? (
                    <Box flex={1}>
                      <Typography variant="body2" color="text.secondary">
                        Starting Pitchers
                      </Typography>
                      <Box>
                        {game.away_starting_pitcher && (
                          <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                            {game.away_team?.slice(0, 8) || 'Away'}: {game.away_starting_pitcher}
                          </Typography>
                        )}
                        {game.home_starting_pitcher && (
                          <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                            {game.home_team?.slice(0, 8) || 'Home'}: {game.home_starting_pitcher}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  ) : (
                    <Box flex={1} /> // Empty space for non-MLB sports
                  )}
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
};

export default PastGamesDisplay;
