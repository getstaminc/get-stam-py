import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { CircularProgress, Box, Typography } from "@mui/material";
import GameDetails from "../components/GameDetails";
import { useGame } from "../contexts/GameContext";

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

// Fetch single game data from backend API
async function fetchSingleGameData(sport: string, gameId: string) {
  const url = `https://www.getstam.com/api/game/${sport}/${gameId}`;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert URL sport to API sport key
  const sportKey = sport ? SPORT_URL_TO_API_KEY[sport] || sport : null;

  useEffect(() => {
    // If we have game data from context and the game_id matches, use it
    if (currentGame && currentGame.game_id === gameId) {
      setGameData(currentGame);
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
      <GameDetails game={gameData} />
    </div>
  );
};

export default GameDetailsPage;