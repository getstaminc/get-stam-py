import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Paper,
  TextField,
  CircularProgress,
} from "@mui/material";
import { useGame } from "../contexts/GameContext";
import GameOdds from "../components/GameOdds";
import GamesWithTrends from "../components/GamesWithTrends";
import PastGamesDisplay from "../components/PastGamesDisplay";
import { GameWithTrends } from "../utils/trendAnalysis";
import { fetchPitcherData, getPitcherDataForGame } from "../utils/mlbUtils"; 

// Map URL sport (e.g. "nfl") to Odds API sport key
const SPORT_URL_TO_API_KEY: { [key: string]: string } = {
  nfl: "americanfootball_nfl",
  mlb: "baseball_mlb",
  nba: "basketball_nba",
  nhl: "icehockey_nhl",
  ncaaf: "americanfootball_ncaaf",
  ncaab: "basketball_ncaab",
  epl: "soccer_epl",
  nfl_preseason: "americanfootball_nfl_preseason",
};

// Map URL sport to historical API sport type
type HistoricalSportType = 'mlb' | 'nfl' | 'ncaaf' | 'soccer' | 'nhl' | 'nba';
const SPORT_URL_TO_HISTORICAL: { [key: string]: HistoricalSportType } = {
  nfl: "nfl",
  mlb: "mlb",
  ncaaf: "ncaaf",
  epl: "soccer",
  nba: "nba",
  nfl_preseason: "nfl", // Map preseason to nfl,
  nhl: "nhl"
};

// Map Odds API sport key to display name
const SPORT_API_KEY_TO_DISPLAY: { [key: string]: string } = {
  baseball_mlb: "MLB",
  basketball_nba: "NBA",
  americanfootball_nfl: "NFL",
  americanfootball_nfl_preseason: "NFL",
  icehockey_nhl: "NHL",
  americanfootball_ncaaf: "NCAAF",
  basketball_ncaab: "NCAAB",
  soccer_epl: "EPL",
};

const formatDate = (date: Date) => {
  if (!date || isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
};
const formatDateForUrl = (date: Date) => {
  if (!date || isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10).replace(/-/g, "");
};
const getToday = (): Date => {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
};

// Helper to check if a date is in the past
const isPastDate = (date: Date): boolean => {
  const today = getToday();
  return date < today;
};

// Helper to extract sport from URL path (e.g. "/nfl" → "nfl")
function getSportFromPath(pathname: string): string {
  const match = pathname.match(/^\/([^/]+)/);
  return match ? match[1] : "nfl";
}

// Get API base URL from env, fallback to prod or dev
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:5000" : "https://www.getstam.com");

// Fetch games from your backend API
async function fetchGamesData(sportKey: string, date: Date) {
  const dateStr = formatDate(date);
  const url = `${API_BASE_URL}/api/odds/${sportKey}?date=${dateStr}`;
  try {
    const res = await fetch(url, {
      headers: {
        // Uncomment if your backend requires an API key header:
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    });
    if (!res.ok) throw new Error("API error");
    const data = await res.json();
    return data;
  } catch (e) {
    console.error("Error fetching games data:", e);
    return { games: [], nextGameDate: null };
  }
}

// Fetch trends from your new API endpoint
async function fetchTrendsData(games: any[], sportKey: string, minTrendLength: number) {
  // Map sportKey to the appropriate endpoint
  const sportEndpointMap: { [key: string]: string } = {
    'americanfootball_nfl': 'nfl',
    'americanfootball_nfl_preseason': 'nfl',
    'americanfootball_ncaaf': 'ncaaf',
    'baseball_mlb': 'mlb',
    'basketball_nba': 'nba',
    'soccer_epl': 'soccer',
    'soccer_uefa_champs_league': 'soccer',
    'soccer_uefa_europa_league': 'soccer',
    'soccer_fifa_world_cup': 'soccer',
    'soccer_uefa_nations_league': 'soccer',
    'icehockey_nhl': 'nhl',
    // Add other sports as endpoints become available
  };
  
  const sportEndpoint = sportEndpointMap[sportKey];
  if (!sportEndpoint) {
    throw new Error(`Trends analysis not available for sport: ${sportKey}`);
  }
  
  const url = `${API_BASE_URL}/api/historical/trends/${sportEndpoint}`;
  const requestBody = {
    games: games,
    sportKey: sportKey,
    minTrendLength: minTrendLength
  };
  
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!res.ok) throw new Error(`Trends API error: ${res.status}`);
    const trendsData = await res.json();
    return trendsData;
  } catch (e) {
    console.error("Error fetching trends data:", e);
    throw e;
  }
}

const GamesPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { setCurrentGame } = useGame();

  // Get sport from URL path (e.g. "/nfl")
  const urlSport = getSportFromPath(location.pathname);
  const sportKey = SPORT_URL_TO_API_KEY[urlSport] || "nfl";
  const historicalSportType = SPORT_URL_TO_HISTORICAL[urlSport];
  const displaySport = SPORT_API_KEY_TO_DISPLAY[sportKey] || "NFL";

  // Get date from URL query param if present
  const params = new URLSearchParams(location.search);
  const urlDate = params.get("date");
  const isTrends = location.pathname.includes("/trends");

  const initialDate: Date = urlDate
    ? new Date(
        parseInt(urlDate.slice(0,4)), // year
        parseInt(urlDate.slice(4,6)) - 1, // month (0-indexed)
        parseInt(urlDate.slice(6,8)) // day
      )
    : getToday();

  const [selectedDate, setSelectedDate] = useState<Date>(initialDate);
  const [activeView, setActiveView] = useState<"all" | "trends">(isTrends ? "trends" : "all");
  const [games, setGames] = useState<any[]>([]);
  const [gamesWithTrends, setGamesWithTrends] = useState<GameWithTrends[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(false);
  const [gamesLoading, setGamesLoading] = useState(false);
  const [minTrendLength, setMinTrendLength] = useState<number>(3);
  const [pitcherData, setPitcherData] = useState<any>({});

  // Get pitcher data for a specific game using shared utility
  const getGamePitcherData = (game: any) => {
    return getPitcherDataForGame(game, pitcherData, selectedDate, sportKey);
  };

  const [nextGameDate, setNextGameDate] = useState<string | null>(null);
  
  // Check if selected date is in the past
  const isHistoricalDate = isPastDate(selectedDate);

  // Helper to update date only
  // Always update selectedDate as a new Date object to force effect
  const updateDate = (date: Date) => {
    setSelectedDate(new Date(date));
  };

  // Sync selectedDate with URL changes (so isHistoricalDate is always recalculated)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlDate = params.get("date");
    let newDate: Date;
    if (urlDate) {
      newDate = new Date(
        parseInt(urlDate.slice(0,4)),
        parseInt(urlDate.slice(4,6)) - 1,
        parseInt(urlDate.slice(6,8))
      );
    } else {
      newDate = getToday();
    }
  setSelectedDate(new Date(newDate));
    // eslint-disable-next-line
  }, [location.search]);

  // Fetch pitcher data when sport is MLB
  useEffect(() => {
    if (sportKey === "baseball_mlb") {
      fetchPitcherData().then((data) => {
        setPitcherData(data);
      });
    } else {
      setPitcherData({});
    }
  }, [sportKey]);

  // CRITICAL: Sync activeView with URL IMMEDIATELY - this must run before trend analysis
  useEffect(() => {
    const newActiveView = isTrends ? "trends" : "all";
    
    // If date is historical and user is trying to view trends, force to "all" view
    if (isHistoricalDate && newActiveView === "trends") {
      setActiveView("all");
    } else {
      setActiveView(newActiveView);
    }
    
    // When switching away from trends, clear trends data immediately  
    if (newActiveView === "all" || isHistoricalDate) {
      setGamesWithTrends([]);
      setTrendsLoading(false);
    }
  }, [isTrends, location.pathname, isHistoricalDate]);

  // Fetch data when sport or date changes (only for current/future dates)


  // Fetch games when selectedDate, sportKey, or isHistoricalDate changes
  useEffect(() => {
    setGames([]);
    setGamesWithTrends([]);
    setTrendsLoading(false);
    if (!isHistoricalDate) {
      setGamesLoading(true);
      fetchGamesData(sportKey, selectedDate).then((data) => {
        setGames(data.games || []);
        setNextGameDate(data.nextGameDate || null);
      }).finally(() => {
        setGamesLoading(false);
      });
    } else {
      setNextGameDate(null);
      setGamesLoading(false);
    }
    // eslint-disable-next-line
  }, [selectedDate, sportKey, isHistoricalDate]);

  // Analyze trends when switching to trends view or when minTrendLength changes
  useEffect(() => {
    // Use isTrends directly instead of activeView to avoid race condition
    if (isTrends && games.length > 0) {
      setTrendsLoading(true);
      
      fetchTrendsData(games, sportKey, minTrendLength)
        .then((trendsResponse) => {
          // Extract the data array from the API response
          const trendsData = trendsResponse?.data || [];
          setGamesWithTrends(trendsData);
        })
        .catch((error) => {
          console.error("Error fetching trends:", error);
          setGamesWithTrends([]);
        })
        .finally(() => {
          setTrendsLoading(false);
        });
    } else {
      setGamesWithTrends([]);
    }
  }, [isTrends, games, sportKey, minTrendLength]); // Changed dependency from activeView to isTrends

  // Handle minimum trend length change
  const handleMinTrendLengthChange = (newMinLength: number) => {
    setMinTrendLength(newMinLength);
  };

  // Handle View Details button click
  const handleViewDetails = (game: any) => {
  // Save game data to context only
  setCurrentGame(game);
  };

  // Update URL when date or view changes
  useEffect(() => {
    const urlDateStr = formatDateForUrl(selectedDate);
    
    // If date is in the past and user is trying to view trends, redirect to all games
    if (isHistoricalDate && activeView === "trends") {
      navigate(`/${urlSport}?date=${urlDateStr}`, { replace: true });
    } else if (activeView === "all") {
      navigate(`/${urlSport}?date=${urlDateStr}`, { replace: true });
    } else {
      navigate(`/${urlSport}/trends?date=${urlDateStr}`, { replace: true });
    }
    // eslint-disable-next-line
  }, [selectedDate, activeView, urlSport, isHistoricalDate]);

  return (
    <Box sx={{ display: "flex", justifyContent: "center", px: 2, py: 4 }}>
      <Box sx={{ width: "100%", maxWidth: 900 }}>
        <Typography
          variant="h4"
          align="center"
          sx={{
            fontWeight: 700,
            mb: 1,
            color: "#1976d2",
          }}
        >
          {displaySport} Matchups
        </Typography>
        <Typography
          variant="body2"
          align="center"
          sx={{
            mb: 3,
            color: "#757575",
            fontStyle: "italic",
          }}
        >
          * Only games with betting odds data will display
        </Typography>
        <Box
          sx={{
            mb: 4,
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 2
          }}
        >
          {/* Only show buttons for current/future dates */}
          {!isHistoricalDate && (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                justifyContent: { xs: 'center', md: 'flex-start' },
                alignItems: 'center',
                width: '100%',
                gap: 0
              }}
            >
              <Button
                variant={activeView === "all" ? "contained" : "outlined"}
                color={activeView === "all" ? "primary" : "inherit"}
                onClick={() => setActiveView("all")}
                sx={{
                  px: 3,
                  py: 1,
                  fontSize: "1rem",
                  textTransform: "none",
                  borderRadius: '8px 0 0 8px',
                  borderRight: "1px solid #ccc",
                  boxShadow: "none",
                  ...(activeView === "all" && { zIndex: 1 }),
                  ...(activeView !== "all" && {
                    borderColor: '#e0e0e0',
                    color: '#666',
                    '&:hover': {
                      borderColor: '#bdbdbd',
                      backgroundColor: 'rgba(0, 0, 0, 0.04)'
                    }
                  })
                }}
              >
                All Games
              </Button>
              <Button
                variant={activeView === "trends" ? "contained" : "outlined"}
                color={activeView === "trends" ? "primary" : "inherit"}
                onClick={() => setActiveView("trends")}
                sx={{
                  px: 3,
                  py: 1,
                  fontSize: "1rem",
                  textTransform: "none",
                  borderRadius: '0 8px 8px 0',
                  boxShadow: "none",
                  borderLeft: "none",
                  ...(activeView === "trends" && { zIndex: 1 }),
                  ...(activeView !== "trends" && {
                    borderColor: '#e0e0e0',
                    color: '#666',
                    '&:hover': {
                      borderColor: '#bdbdbd',
                      backgroundColor: 'rgba(0, 0, 0, 0.04)'
                    }
                  })
                }}
              >
                Games with Trends
              </Button>
            </Box>
          )}
          <TextField
            label="Select Date"
            type="date"
            value={formatDate(selectedDate)}
            onChange={(e) => updateDate(new Date(e.target.value))}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 160, mb: { xs: 2, sm: 0 } }}
          />
        </Box>

        {/* Show historical games for past dates */}
        {isHistoricalDate && historicalSportType && (
          <PastGamesDisplay
            selectedDate={formatDate(selectedDate)}
            sportType={historicalSportType}
          />
        )}

        {/* Show message if historical sport not supported */}
        {isHistoricalDate && !historicalSportType && (
          <Typography align="center" sx={{ mt: 4, mb: 2 }}>
            Historical data is not available for {displaySport} yet.
          </Typography>
        )}

        {/* Show current/future games */}
        {!isHistoricalDate && activeView === "all" && gamesLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 4, mb: 2 }}>
            <CircularProgress />
          </Box>
        )}

        {!isHistoricalDate && activeView === "all" && !gamesLoading && games.length === 0 && (
          <Typography align="center" sx={{ mt: 4, mb: 2 }}>
            No games found for this date.
            {nextGameDate && (
              <span>
                {" "}
                Next games are on{" "}
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => updateDate(new Date(nextGameDate))}
                  sx={{ ml: 1 }}
                >
                  {nextGameDate}
                </Button>
              </span>
            )}
          </Typography>
        )}

        {!isHistoricalDate && activeView === "all" && games.map((match) => (
          <Paper key={match.game_id} elevation={3} sx={{ mb: 3, p: 2, borderRadius: 2,  backgroundColor: "#f9f9f9" }}>
            <GameOdds
              game={{
                home: match.home,
                away: match.away,
                totals: match.totals,
                ...(match.draw ? { draw: match.draw } : {})
              }}
              pitcherData={getGamePitcherData(match)}
            />
            <Box sx={{ mt: 3, textAlign: "center" }}>
              <Button
                component={Link}
                to={`/game-details/${urlSport}?game_id=${match.game_id}`}
                variant="contained"
                color="primary"
                onClick={() => setCurrentGame(match)}
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
        ))}

        {!isHistoricalDate && activeView === "trends" && gamesLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 4, mb: 2 }}>
            <CircularProgress />
          </Box>
        )}

        {!isHistoricalDate && activeView === "trends" && !gamesLoading && games.length === 0 && (
          <Typography align="center" sx={{ mt: 4, mb: 2 }}>
            No games found for this date.
            {nextGameDate && (
              <span>
                {" "}
                Next games are on{" "}
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setSelectedDate(new Date(nextGameDate))}
                  sx={{ ml: 1 }}
                >
                  {nextGameDate}
                </Button>
              </span>
            )}
          </Typography>
        )}

        {!isHistoricalDate && activeView === "trends" && games.length > 0 && (
          <GamesWithTrends 
            gamesWithTrends={gamesWithTrends}
            loading={trendsLoading}
            onViewDetails={handleViewDetails}
            minTrendLength={minTrendLength}
            onMinTrendLengthChange={handleMinTrendLengthChange}
            getPitcherDataForGame={getGamePitcherData}
          />
        )}

        {/* Hide trends button for historical dates */}
        {isHistoricalDate && activeView === "trends" && (
          <Typography align="center" sx={{ mt: 4, mb: 2 }}>
            Trends analysis is only available for current and future games.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default GamesPage;