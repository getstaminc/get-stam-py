import React from "react";
import { Box, Typography, Paper, Button, Divider } from "@mui/material";

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

const NFLPage = () => (
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
      <Box sx={{ textAlign: "center", mb: 4, display: "flex", justifyContent: "center", gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          href="/nfl/all"
          size="large"
          sx={{
            px: 3,
            py: 1,
            fontWeight: 600,
            fontSize: "1rem",
            textTransform: "none",
            borderRadius: 2,
          }}
        >
          View All Games
        </Button>
        <Button
          variant="outlined"
          color="secondary"
          href="/nfl/trends"
          size="large"
          sx={{
            px: 3,
            py: 1,
            fontWeight: 600,
            fontSize: "1rem",
            textTransform: "none",
            borderRadius: 2,
          }}
        >
          View Games with Trends
        </Button>
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

export default NFLPage;