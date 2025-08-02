import React, { useEffect, useState } from "react";
import { Box, Typography, Paper, Button, Divider, TextField } from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";

// Odds API key from .env (ODDS_API_KEY)
const ODDS_API_KEY = process.env.REACT_APP_ODDS_API_KEY;

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

// Map Odds API sport key to display name
const SPORT_API_KEY_TO_DISPLAY: { [key: string]: string } = {
  baseball_mlb: "MLB",
  basketball_nba: "NBA",
  americanfootball_nfl: "NFL",
  americanfootball_nfl_preseason: "NFL",
  icehockey_nhl: "NHL",
  americanfootball_ncaaf: "NCAAFB",
  basketball_ncaab: "NCAABB",
  soccer_epl: "EPL",
};

// Helper to format date as YYYY-MM-DD for input[type="date"]
const formatDate = (date: Date) => date.toISOString().slice(0, 10);
// Helper to format date as YYYYMMDD for URL
const formatDateForUrl = (date: Date) => date.toISOString().slice(0, 10).replace(/-/g, "");
const getToday = (): Date => {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
};

// Helper to extract sport from URL path (e.g. "/nfl" → "nfl")
function getSportFromPath(pathname: string): string {
  const match = pathname.match(/^\/([^/]+)/);
  return match ? match[1] : "nfl";
}

// Fetch games from your backend API
async function fetchGamesData(sportKey: string, date: Date) {
  const dateStr = formatDate(date);
  const url = `https://www.getstam.com/api/games/${sportKey}?date=${dateStr}`;
  try {
    const res = await fetch(url, {
      headers: {
        // Uncomment if your backend requires an API key header:
        "X-API-KEY": process.env.REACT_APP_API_KEY || "",
      },
    });
    if (!res.ok) throw new Error("API error");
    return await res.json();
  } catch (e) {
    console.error("Error fetching games data:", e);
    return { games: [], nextGameDate: null };
  }
}

const NFLPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Get sport from URL path (e.g. "/nfl")
  const urlSport = getSportFromPath(location.pathname);
  const sportKey = SPORT_URL_TO_API_KEY[urlSport] || "nfl";
  const displaySport = SPORT_API_KEY_TO_DISPLAY[sportKey] || "NFL";

  // Get date from URL query param if present
  const params = new URLSearchParams(location.search);
  const urlDate = params.get("date");
  const isTrends = location.pathname.includes("/trends");

  // Parse date from URL or default to today
  const initialDate: Date = urlDate
    ? new Date(urlDate)
    : getToday();

  const [selectedDate, setSelectedDate] = useState<Date>(initialDate);
  const [activeView, setActiveView] = useState<"all" | "trends">(isTrends ? "trends" : "all");
  const [games, setGames] = useState<any[]>([]);
  const [nextGameDate, setNextGameDate] = useState<string | null>(null);

  // Fetch data when sport or date changes
  useEffect(() => {
    fetchGamesData(sportKey, selectedDate).then((data) => {
      setGames(data.games || []);
      setNextGameDate(data.nextGameDate || null);
    });
  }, [sportKey, selectedDate, activeView]);

  // Update URL when date or view changes
  useEffect(() => {
    const urlDateStr = formatDateForUrl(selectedDate);
    if (activeView === "all") {
      navigate(`/${urlSport}?date=${urlDateStr}`, { replace: true });
    } else {
      navigate(`/${urlSport}/trends?date=${urlDateStr}`, { replace: true });
    }
    // eslint-disable-next-line
  }, [selectedDate, activeView, urlSport]);

  // Sync activeView with URL if user navigates directly
  useEffect(() => {
    setActiveView(isTrends ? "trends" : "all");
    // eslint-disable-next-line
  }, [isTrends]);

  return (
    <Box sx={{ display: "flex", justifyContent: "center", px: 2, py: 4 }}>
      <Box sx={{ width: "100%", maxWidth: 900 }}>
        <Typography
          variant="h4"
          align="center"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: "#1976d2",
          }}
        >
          {displaySport} Matchups
        </Typography>
        <Box
          sx={{
            mb: 4,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <TextField
            label="Select Date"
            type="date"
            value={formatDate(selectedDate)}
            onChange={(e) => setSelectedDate(new Date(e.target.value))}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 160 }}
          />
          <Box sx={{ display: "flex", gap: 0 }}>
            <Button
              variant={activeView === "all" ? "contained" : "outlined"}
              color={activeView === "all" ? "primary" : "inherit"}
              onClick={() => setActiveView("all")}
              sx={{
                px: 3,
                py: 1,
                fontSize: "1rem",
                textTransform: "none",
                borderRadius: "8px 0 0 8px",
                borderRight: "1px solid #ccc",
                boxShadow: "none",
                ...(activeView === "all" && { zIndex: 1 }),
              }}
            >
              All Games
            </Button>
            <Button
              variant={activeView === "trends" ? "contained" : "outlined"}
              color={activeView === "trends" ? "secondary" : "inherit"}
              onClick={() => setActiveView("trends")}
              sx={{
                px: 3,
                py: 1,
                fontSize: "1rem",
                textTransform: "none",
                borderRadius: "0 8px 8px 0",
                boxShadow: "none",
                borderLeft: "none",
                ...(activeView !== "trends" && { color: "text.primary" }),
                ...(activeView === "trends" && { zIndex: 1 }),
              }}
            >
              Games with Trends
            </Button>
          </Box>
        </Box>

        {games.length === 0 && (
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

        {games.map((match) => {
          const home = match.home || {};
          const away = match.away || {};
          const totals = match.totals || {};

          const hasScore =
            home.score !== null && home.score !== undefined &&
            away.score !== null && away.score !== undefined;
          const scoreDisplay = hasScore
            ? `${home.score} - ${away.score}`
            : "— —";

          return (
            <Paper
              key={match.game_id}
              elevation={3}
              sx={{
                mb: 3,
                p: 2,
                borderRadius: 2,
                backgroundColor: "#f9f9f9",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 2,
                }}
              >
                <Box sx={{ flex: 1, textAlign: "right" }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {home.team}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Home
                  </Typography>
                </Box>

                <Box sx={{ flex: "none", textAlign: "center", px: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {scoreDisplay}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {hasScore ? "Final Score" : "Scheduled"}
                  </Typography>
                </Box>

                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {away.team}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Away
                  </Typography>
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 2,
                  textAlign: "center",
                  flexWrap: "wrap",
                }}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    H2H
                  </Typography>
                  <Typography variant="body1">
                    {home.odds?.h2h !== undefined && away.odds?.h2h !== undefined
                      ? `${home.team}: ${home.odds.h2h} | ${away.team}: ${away.odds.h2h}`
                      : "N/A"}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Spreads
                  </Typography>
                  <Typography variant="body1">
                    {home.odds?.spread_point !== undefined && away.odds?.spread_point !== undefined
                      ? `${home.team}: ${home.odds.spread_point} (${home.odds.spread_price}) | ${away.team}: ${away.odds.spread_point} (${away.odds.spread_price})`
                      : "N/A"}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Totals
                  </Typography>
                  <Typography variant="body1">
                    {totals.over_point !== undefined && totals.under_point !== undefined
                      ? `Over: ${totals.over_point} (${totals.over_price}) | Under: ${totals.under_point} (${totals.under_price})`
                      : "N/A"}
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ mt: 3, textAlign: "center" }}>
                <Button
                  variant="contained"
                  color="primary"
                  href={`/game/${match.game_id}?sport_key=${sportKey}`}
                  size="medium"
                  sx={{
                    px: 3,
                    py: 1,
                    fontWeight: 600,
                    fontSize: "1rem",
                    textTransform: "none",
                    borderRadius: 2,
                  }}
                >
                  View Details
                </Button>
              </Box>
            </Paper>
          );
        })}
      </Box>
    </Box>
  );
};

export default NFLPage;