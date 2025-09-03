import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { CircularProgress, Box, Typography } from "@mui/material";
import GameDetails from "../components/GameDetails";
import { useGame } from "../contexts/GameContext";
import { convertTeamNameBySport, convertSportKeyForDatabase } from "../utils/teamNameConverter";

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

// Map API sport key to database sport key
const API_SPORT_TO_DB_SPORT: { [key: string]: string } = {
  americanfootball_nfl: "nfl",
  baseball_mlb: "mlb", 
  basketball_nba: "nba",
  icehockey_nhl: "nhl",
  americanfootball_ncaaf: "ncaaf",
  basketball_ncaab: "ncaab",
  soccer_epl: "epl",
  americanfootball_nfl_preseason: "nfl",
};

// Fetch single game data from backend API
async function fetchSingleGameData(sport: string, gameId: string) {
  const url = `https://www.getstam.com/api/odds/${sport}/${gameId}`;
  try {
    const res = await fetch(url, {
      headers: {
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    });
    if (!res.ok) throw new Error("API error");
    const data = await res.json();
    // The backend returns { game: gameData }, so we need to extract the game object
    return data.game || data;
  } catch (e) {
    console.error("Error fetching single game data:", e);
    return null;
  }
}

const GameDetailsPage: React.FC = () => {
  const { sport } = useParams<{ sport: string }>();
  const [searchParams] = useSearchParams();
  const gameId = searchParams.get('game_id');
  const { currentGame } = useGame();
  const [gameData, setGameData] = useState<any>(null);
  const [homeTeamHistory, setHomeTeamHistory] = useState<any>(null);
  const [awayTeamHistory, setAwayTeamHistory] = useState<any>(null);
  const [headToHeadHistory, setHeadToHeadHistory] = useState<any>(null);
  const [homeRankings, setHomeRankings] = useState<any>(null);
  const [awayRankings, setAwayRankings] = useState<any>(null);
  const [rankingsLoading, setRankingsLoading] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gamesLimit, setGamesLimit] = useState<number>(5);

  // Convert URL sport to API sport key
  const sportKey = sport ? SPORT_URL_TO_API_KEY[sport] || sport : null;

  // Fetch team history
  const fetchTeamHistory = async (sportKey: string, teamName: string, limit: number = 5) => {
    const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
    const convertedTeamName = convertTeamNameBySport(sportKey, teamName);
    const response = await fetch(`https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedTeamName)}?limit=${limit}`, {
      headers: {
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    });
    if (!response.ok) throw new Error("Failed to fetch team history");
    return response.json();
  };

  // Fetch head-to-head history
  const fetchHeadToHead = async (sportKey: string, homeTeam: string, awayTeam: string, limit: number = 5) => {
    const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
    const convertedHomeTeam = convertTeamNameBySport(sportKey, homeTeam);
    const convertedAwayTeam = convertTeamNameBySport(sportKey, awayTeam);
    const response = await fetch(
      `https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedHomeTeam)}/vs/${encodeURIComponent(convertedAwayTeam)}?limit=${limit}`,
      {
        headers: {
          "X-API-KEY": process.env.REACT_APP_API_KEY || "",
        },
      }
    );
    if (!response.ok) throw new Error("Failed to fetch head-to-head history");
    return response.json();
  };

  // Fetch team rankings for NFL and NCAAF
  const fetchRankings = async (sportKey: string, homeTeam: string, awayTeam: string) => {
    if (sportKey !== 'americanfootball_nfl' && sportKey !== 'americanfootball_ncaaf') return null;
    
    try {
      setRankingsLoading(true);
      
      // Determine which API endpoint to use
      const apiSport = sportKey === 'americanfootball_nfl' ? 'nfl' : 'ncaaf';
      
      const response = await fetch(
        `https://www.getstam.com/api/rankings/${apiSport}`,
        {
          headers: {
            "X-API-KEY": process.env.REACT_APP_API_KEY || "",
          },
        }
      );
      if (!response.ok) throw new Error("Failed to fetch rankings");
      const data = await response.json();
      
      // Extract rankings for both teams
      const homeTeamRankings = data.rankings[homeTeam] || null;
      const awayTeamRankings = data.rankings[awayTeam] || null;
      
      setHomeRankings(homeTeamRankings);
      setAwayRankings(awayTeamRankings);
      setRankingsLoading(false);
      
      return { homeTeamRankings, awayTeamRankings };
    } catch (error) {
      console.error("Error fetching rankings:", error);
      setRankingsLoading(false);
      return null;
    }
  };

  // Function to fetch all historical data
  const fetchAllHistoricalData = async (sportKey: string, homeTeam: string, awayTeam: string, limit: number = 5) => {
    try {
      const promises = [
        fetchTeamHistory(sportKey, homeTeam, limit),
        fetchTeamHistory(sportKey, awayTeam, limit),
        fetchHeadToHead(sportKey, homeTeam, awayTeam, limit)
      ];
      
      // Add rankings fetch for NFL and NCAAF games
      if (sportKey === 'americanfootball_nfl' || sportKey === 'americanfootball_ncaaf') {
        promises.push(fetchRankings(sportKey, homeTeam, awayTeam));
      }
      
      const results = await Promise.all(promises);
      const [homeHistory, awayHistory, h2hHistory] = results;
      
      setHomeTeamHistory(homeHistory);
      setAwayTeamHistory(awayHistory);
      setHeadToHeadHistory(h2hHistory);
    } catch (error) {
      console.error("Error fetching historical data:", error);
    }
  };

  // Handle limit change from dropdown
  const handleLimitChange = async (newLimit: number) => {
    setGamesLimit(newLimit);
    
    if (gameData && sportKey) {
      const homeTeam = gameData.home?.team || gameData.home_team_name;
      const awayTeam = gameData.away?.team || gameData.away_team_name;
      
      if (homeTeam && awayTeam) {
        await fetchAllHistoricalData(sportKey, homeTeam, awayTeam, newLimit);
      }
    }
  };

  useEffect(() => {
    // If we have game data from context and the game_id matches, use it
    if (currentGame && currentGame.game_id === gameId) {
      setGameData(currentGame);
      
      // Also fetch historical data for context game
      if (sportKey && currentGame.home?.team && currentGame.away?.team) {
        fetchAllHistoricalData(sportKey, currentGame.home.team, currentGame.away.team, gamesLimit);
      }
      return;
    }

    // Otherwise, fetch from API if we have sport and gameId
    if (sportKey && gameId) {
      setLoading(true);
      setError(null);
      
      fetchSingleGameData(sportKey, gameId)
        .then((data) => {
          if (data) {
            setGameData(data);
            
            // After getting game data, fetch historical data
            // Check if data has team names (could be from odds API or database)
            const homeTeam = data.home?.team || data.home_team_name;
            const awayTeam = data.away?.team || data.away_team_name;
            
            if (homeTeam && awayTeam) {
              fetchAllHistoricalData(sportKey, homeTeam, awayTeam, gamesLimit);
            }
          } else {
            setError("Failed to load game data");
          }
        })
        .catch(() => {
          setError("Failed to load game data");
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setError("Missing sport or game ID");
    }
  }, [sportKey, gameId, currentGame, gamesLimit]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <Typography variant="h6" color="error">
          {error}
        </Typography>
      </Box>
    );
  }

  if (!gameData) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <Typography variant="h6">
          No game data available
        </Typography>
      </Box>
    );
  }

  return (
    <div>
      <GameDetails 
        game={gameData} 
        homeTeamHistory={homeTeamHistory}
        awayTeamHistory={awayTeamHistory}
        headToHeadHistory={headToHeadHistory}
        onLimitChange={handleLimitChange}
        currentLimit={gamesLimit}
        sportKey={sportKey || "americanfootball_nfl"}
        homeRankings={homeRankings}
        awayRankings={awayRankings}
        rankingsLoading={rankingsLoading}
      />
    </div>
  );
};

export default GameDetailsPage;