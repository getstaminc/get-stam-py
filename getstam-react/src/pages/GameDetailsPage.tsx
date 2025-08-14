import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { CircularProgress, Box, Typography } from "@mui/material";
import GameDetails from "../components/GameDetails";
import { useGame } from "../contexts/GameContext";
import { convertTeamName, convertSportKeyForDatabase } from "../utils/teamNameConverter";

// Map URL sport (e.g. "nfl") to Odds API sport key
const SPORT_URL_TO_API_KEY: { [key: string]: string } = {
  nfl: "americanfootball_nfl",
  mlb: "baseball_mlb",
  nba: "basketball_nba",
  nhl: "icehockey_nhl",
  ncaafb: "americanfootball_ncaaf",
  ncaabb: "basketball_ncaab",
  epl: "soccer_epl",
  nfl_preseason: "americanfootball_nfl_preseason",
};

// Map API sport key to database sport key
const API_SPORT_TO_DB_SPORT: { [key: string]: string } = {
  americanfootball_nfl: "nfl",
  baseball_mlb: "mlb", 
  basketball_nba: "nba",
  icehockey_nhl: "nhl",
  americanfootball_ncaaf: "ncaafb",
  basketball_ncaab: "ncaabb",
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert URL sport to API sport key
  const sportKey = sport ? SPORT_URL_TO_API_KEY[sport] || sport : null;

  // Fetch team history
  const fetchTeamHistory = async (sportKey: string, teamName: string) => {
    const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
    const convertedTeamName = convertTeamName(teamName);
    const response = await fetch(`https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedTeamName)}`, {
      headers: {
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    });
    if (!response.ok) throw new Error("Failed to fetch team history");
    return response.json();
  };

  // Fetch head-to-head history
  const fetchHeadToHead = async (sportKey: string, homeTeam: string, awayTeam: string) => {
    const dbSportKey = API_SPORT_TO_DB_SPORT[sportKey] || sportKey;
    const convertedHomeTeam = convertTeamName(homeTeam);
    const convertedAwayTeam = convertTeamName(awayTeam);
    const response = await fetch(
      `https://www.getstam.com/api/games/${dbSportKey}/team/${encodeURIComponent(convertedHomeTeam)}/vs/${encodeURIComponent(convertedAwayTeam)}`,
      {
        headers: {
          "X-API-KEY": process.env.REACT_APP_API_KEY || "",
        },
      }
    );
    if (!response.ok) throw new Error("Failed to fetch head-to-head history");
    return response.json();
  };

  useEffect(() => {
    // If we have game data from context and the game_id matches, use it
    if (currentGame && currentGame.game_id === gameId) {
      setGameData(currentGame);
      
      // Also fetch historical data for context game
      if (sportKey && currentGame.home?.team && currentGame.away?.team) {
        Promise.all([
          fetchTeamHistory(sportKey, currentGame.home.team),
          fetchTeamHistory(sportKey, currentGame.away.team),
          fetchHeadToHead(sportKey, currentGame.home.team, currentGame.away.team)
        ]).then(([homeHistory, awayHistory, h2hHistory]) => {
          setHomeTeamHistory(homeHistory);
          setAwayTeamHistory(awayHistory);
          setHeadToHeadHistory(h2hHistory);
        }).catch((error) => {
          console.error("Error fetching historical data:", error);
        });
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
              Promise.all([
                fetchTeamHistory(sportKey, homeTeam),
                fetchTeamHistory(sportKey, awayTeam),
                fetchHeadToHead(sportKey, homeTeam, awayTeam)
              ]).then(([homeHistory, awayHistory, h2hHistory]) => {
                setHomeTeamHistory(homeHistory);
                setAwayTeamHistory(awayHistory);
                setHeadToHeadHistory(h2hHistory);
              }).catch((error) => {
                console.error("Error fetching historical data:", error);
              });
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
  }, [sportKey, gameId, currentGame]);

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
      />
    </div>
  );
};

export default GameDetailsPage;