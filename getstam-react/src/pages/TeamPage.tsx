import React, { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { Box, Typography, CircularProgress, Divider } from "@mui/material";
import SEO from "../components/SEO";
import GameOdds from "../components/GameOdds";
import HistoricalGames from "../components/HistoricalGames";
import { getTeamBySlug } from "../utils/teamSlugUtils";
import { HistoricalGame, SportType, GameWithDraw } from "../types/gameTypes";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

const SPORT_URL_TO_API_KEY: Record<string, string> = {
  nba: "basketball_nba",
  nfl: "americanfootball_nfl",
  mlb: "baseball_mlb",
  nhl: "icehockey_nhl",
  ncaaf: "americanfootball_ncaaf",
  ncaab: "basketball_ncaab",
};

const SPORT_URL_TO_HISTORICAL: Record<string, SportType> = {
  nba: "nba",
  nfl: "nfl",
  mlb: "mlb",
  nhl: "nhl",
  ncaaf: "ncaaf",
  ncaab: "ncaab",
};

const SPORT_DISPLAY: Record<string, string> = {
  nba: "NBA",
  nfl: "NFL",
  mlb: "MLB",
  nhl: "NHL",
  ncaaf: "NCAAF",
  ncaab: "NCAAB",
};

const HISTORICAL_PAGE_SIZE = 11;

const TeamPage: React.FC = () => {
  const { sport = "", teamSlug = "" } = useParams<{ sport: string; teamSlug: string }>();

  useEffect(() => { window.scrollTo(0, 0); }, [sport, teamSlug]);

  const teamInfo = useMemo(() => getTeamBySlug(sport, teamSlug), [sport, teamSlug]);
  const sportDisplay = SPORT_DISPLAY[sport] || sport.toUpperCase();
  const sportType = SPORT_URL_TO_HISTORICAL[sport];
  const apiKey = SPORT_URL_TO_API_KEY[sport];

  const [oddsGame, setOddsGame] = useState<GameWithDraw | null>(null);
  const [oddsLoading, setOddsLoading] = useState(true);

  const [historicalGames, setHistoricalGames] = useState<HistoricalGame[]>([]);
  const [historicalLoading, setHistoricalLoading] = useState(true);
  const historicalLimit = HISTORICAL_PAGE_SIZE;

  // Fetch today's odds and filter for this team
  useEffect(() => {
    if (!teamInfo || !apiKey) {
      setOddsLoading(false);
      return;
    }
    setOddsLoading(true);
    fetch(`${API_BASE_URL}/api/odds/${apiKey}`, {
      headers: { "X-API-KEY": process.env.REACT_APP_API_KEY || "" },
    })
      .then((res) => (res.ok ? res.json() : { games: [] }))
      .then((data) => {
        const games: any[] = data.games || [];
        const teamGames = games.filter(
          (g: any) =>
            g.isToday === true &&
            (g.home?.team === teamInfo.oddsApiName ||
              g.away?.team === teamInfo.oddsApiName)
        );
        // Prefer game with live/upcoming odds over a completed game
        const found =
          teamGames.find((g: any) => g.home?.odds?.h2h !== null || g.away?.odds?.h2h !== null) ||
          teamGames[0] ||
          null;
        setOddsGame(found || null);
      })
      .catch(() => setOddsGame(null))
      .finally(() => setOddsLoading(false));
  }, [teamInfo, apiKey]);

  // Fetch historical games
  useEffect(() => {
    if (!teamInfo || !sport) {
      setHistoricalLoading(false);
      return;
    }
    setHistoricalLoading(true);
    fetch(
      `${API_BASE_URL}/api/historical/${sport}/teams/${encodeURIComponent(teamInfo.dbName)}/games?limit=${historicalLimit}`,
      { headers: { "X-API-KEY": process.env.REACT_APP_API_KEY || "" } }
    )
      .then((res) => (res.ok ? res.json() : { games: [] }))
      .then((data) => {
        setHistoricalGames(data.games || []);
      })
      .catch(() => setHistoricalGames([]))
      .finally(() => setHistoricalLoading(false));
  }, [teamInfo, sport, historicalLimit]);

  if (!teamInfo) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <SEO
          title={`Team Not Found | GetSTAM`}
          description="The requested team page could not be found."
        />
        <Typography variant="h5" color="text.secondary">
          Team not found
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          The team <strong>{teamSlug}</strong> was not found for {sportDisplay}.
        </Typography>
      </Box>
    );
  }

  const teamFullName = teamInfo.oddsApiName;

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", px: 2, py: 3, width: "100%" }}>
      <SEO
        title={`${teamFullName} ${sportDisplay} Odds, Stats & Recent Games`}
        description={`${teamFullName} betting odds, ATS records, and last 10 games with spread and total results.`}
        canonicalPath={`/team/${sport}/${teamSlug}`}
      />

      {/* Page header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          {teamFullName}
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          {sportDisplay}
        </Typography>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Today's Game */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600 }}>
          Today's Game
        </Typography>
        <Box sx={{ minHeight: 180 }}>
          {oddsLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 180 }}>
              <CircularProgress size={28} />
            </Box>
          ) : oddsGame ? (
            <GameOdds
              game={oddsGame}
              sport={sport}
              detailsLink={`/game-details/${sport}?game_id=${(oddsGame as any).game_id}`}
            />
          ) : (
            <Typography color="text.secondary">No game today</Typography>
          )}
        </Box>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Recent Games */}
      <Box>
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600 }}>
          Recent Games
        </Typography>
        <Box sx={{ minHeight: 420 }}>
          {sportType ? (
            <>
              <HistoricalGames
                title=""
                games={historicalGames}
                loading={historicalLoading}
                teamName={teamInfo.dbName}
                sportType={sportType}
                sport={sport}
              />
            </>
          ) : (
            <Typography color="text.secondary">
              Historical data not available for this sport.
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default TeamPage;
