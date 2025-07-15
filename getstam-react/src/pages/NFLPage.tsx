import React, { useEffect, useState } from "react";
import { Box, Typography, Paper, Button, Divider, TextField } from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";

const dummyData = [
  {
    game_id: 1,
    homeTeam: "Patriots",
    awayTeam: "Jets",
    homeScore: null,
    awayScore: null,
    odds: {
      h2h: ["Patriots -150", "Jets +130"],
      spreads: ["Patriots -3.5 (-110)", "Jets +3.5 (-110)"],
      totals: ["Over 42.5 (-110)", "Under 42.5 (-110)"],
    },
  },
  {
    game_id: 2,
    homeTeam: "Cowboys",
    awayTeam: "Giants",
    homeScore: null,
    awayScore: null,
    odds: {
      h2h: ["Cowboys -120", "Giants +100"],
      spreads: ["Cowboys -2.5 (-105)", "Giants +2.5 (-115)"],
      totals: ["Over 48.5 (-110)", "Under 48.5 (-110)"],
    },
  },
];

// Helper to format date as YYYY-MM-DD for input[type="date"]
const formatDate = (date: Date) => date.toISOString().slice(0, 10);
// Helper to format date as YYYYMMDD for URL
const formatDateForUrl = (date: Date) => date.toISOString().slice(0, 10).replace(/-/g, "");
const getToday = (): Date => {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
};

const NFLPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Get date from URL query param if present
  const params = new URLSearchParams(location.search);
  const urlDate = params.get("date");
  const isTrends = location.pathname.includes("/trends");

  // Parse date from URL or default to today
  const initialDate: Date = urlDate
    ? new Date(
        `${urlDate.slice(0, 4)}-${urlDate.slice(4, 6)}-${urlDate.slice(6, 8)}`
      )
    : getToday();

  const [selectedDate, setSelectedDate] = useState<Date>(initialDate);
  const [activeView, setActiveView] = useState<"all" | "trends">(isTrends ? "trends" : "all");

  // Update URL when date or view changes
  useEffect(() => {
    const urlDateStr = formatDateForUrl(selectedDate);
    if (activeView === "all") {
      navigate(`/nfl?date=${urlDateStr}`, { replace: true });
    } else {
      navigate(`/nfl/trends?date=${urlDateStr}`, { replace: true });
    }
    // eslint-disable-next-line
  }, [selectedDate, activeView]);

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
          NFL Matchups
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

        {dummyData.map((match) => {
          const hasScore =
            match.homeScore !== null && match.awayScore !== null;
          const scoreDisplay = hasScore
            ? `${match.homeScore} - ${match.awayScore}`
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
                    {match.homeTeam}
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
                    {match.awayTeam}
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
                    {match.odds.h2h.join(" | ")}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Spreads
                  </Typography>
                  <Typography variant="body1">
                    {match.odds.spreads.join(" | ")}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Totals
                  </Typography>
                  <Typography variant="body1">
                    {match.odds.totals.join(" | ")}
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ mt: 3, textAlign: "center" }}>
                <Button
                  variant="contained"
                  color="primary"
                  href={`/game/${match.game_id}?sport_key=americanfootball_nfl`}
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