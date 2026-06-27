import React, { useState, useEffect, useCallback, useRef } from "react";
import { Navigate, Link } from "react-router-dom";
import { Box, Button, Chip, CircularProgress, Container, Typography } from "@mui/material";
import SEO from "../components/SEO";
import EmailSubscribeForm from "../components/EmailSubscribeForm";
import { sports } from "../configs/sportsConfig";
import TrendInsightCard, { getConfidenceScore, getConfidence } from "../components/TrendInsightCard";
import { encodeGameId } from "../utils/gameIdCrypto";
import { GameWithTrends, TrendResult } from "../utils/trendAnalysis";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");
const API_KEY = process.env.REACT_APP_API_KEY || "";

// Config for each sport that may appear on the homepage
const SPORT_CONFIG: Record<
  string,
  { apiKey: string; historicalKey: string; minTrendLength: number }
> = {
  MLB:   { apiKey: "baseball_mlb",           historicalKey: "mlb",   minTrendLength: 5 },
  NBA:   { apiKey: "basketball_nba",         historicalKey: "nba",   minTrendLength: 3 },
  NHL:   { apiKey: "icehockey_nhl",          historicalKey: "nhl",   minTrendLength: 3 },
  NFL:   { apiKey: "americanfootball_nfl",   historicalKey: "nfl",   minTrendLength: 3 },
  NCAAF: { apiKey: "americanfootball_ncaaf", historicalKey: "ncaaf", minTrendLength: 3 },
  NCAAB: { apiKey: "basketball_ncaab",       historicalKey: "ncaab", minTrendLength: 3 },
};

const SKIP_SPORTS = new Set(["WORLD CUP", "SOCCER"]);

const formatDate = (d: Date) => d.toISOString().slice(0, 10);

async function fetchGames(apiKey: string, dateStr: string): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/odds/${apiKey}?date=${dateStr}`, {
      headers: { "X-API-KEY": API_KEY },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.games || [];
  } catch {
    return [];
  }
}

async function fetchTrends(
  games: any[],
  apiKey: string,
  historicalKey: string,
  minTrendLength: number
): Promise<GameWithTrends[]> {
  if (games.length === 0) return [];
  try {
    const res = await fetch(`${API_BASE_URL}/api/historical/trends/${historicalKey}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-KEY": API_KEY },
      body: JSON.stringify({ games, sportKey: apiKey, limit: 20, minTrendLength, enrich: true }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.data || [];
  } catch {
    return [];
  }
}



interface SportSectionProps {
  name: string;
  urlKey: string;
  apiKey: string;
  historicalKey: string;
  minTrendLength: number;
  onReport: (hasActiveGames: boolean, maxScore: number) => void;
}

function SportSection({
  name,
  urlKey,
  apiKey,
  historicalKey,
  minTrendLength,
  onReport,
}: SportSectionProps) {
  const [loading, setLoading] = useState(true);
  const [gamesWithTrends, setGamesWithTrends] = useState<GameWithTrends[]>([]);
  const onReportRef = useRef(onReport);
  onReportRef.current = onReport;

  useEffect(() => {
    const dateStr = formatDate(new Date());
    let cancelled = false;

    (async () => {
      try {
        const games = await fetchGames(apiKey, dateStr);
        const trends = await fetchTrends(games, apiKey, historicalKey, minTrendLength);
        if (cancelled) return;
        const active = trends.filter((gwt) => !gwt.game.completed && gwt.hasTrends);
        setGamesWithTrends(active);
        const allOf = (gwt: GameWithTrends): TrendResult[] => [
          ...(gwt.headToHeadTrends||[]), ...(gwt.homeAtHomeH2HTrends||[]),
          ...(gwt.homeTeamHomeTrends||[]), ...(gwt.awayTeamAwayTrends||[]),
          ...(gwt.homeTeamTrends||[]), ...(gwt.awayTeamTrends||[]),
        ];
        const maxScore = active.length > 0
          ? Math.max(0, ...active.flatMap(gwt => allOf(gwt).map(t => getConfidenceScore(t))))
          : 0;
        onReportRef.current(active.length > 0, maxScore);
      } catch {
        if (!cancelled) onReportRef.current(false, 0);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  // onReport intentionally omitted — held in ref to avoid re-triggering the fetch
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, historicalKey, minTrendLength]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (gamesWithTrends.length === 0) return null;

  return (
    <Box sx={{ mb: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography
          sx={{ fontSize: "0.75rem", fontWeight: 900, letterSpacing: "0.12em", textTransform: "uppercase", color: "#245c38" }}
        >
          {name}
        </Typography>
        <Button
          component={Link}
          to={`/${urlKey}`}
          size="small"
          sx={{ fontWeight: 800, fontSize: "0.8rem", color: "#245c38" }}
        >
          All {name} games →
        </Button>
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
        {[...gamesWithTrends].sort((a, b) => {
          const allOf = (gwt: GameWithTrends): TrendResult[] => [
            ...(gwt.headToHeadTrends||[]), ...(gwt.homeAtHomeH2HTrends||[]),
            ...(gwt.homeTeamHomeTrends||[]), ...(gwt.awayTeamAwayTrends||[]),
            ...(gwt.homeTeamTrends||[]), ...(gwt.awayTeamTrends||[]),
          ];
          const badgeScore = (t: TrendResult): number => {
            const c = getConfidence(t);
            if (!c) return 0;
            if (c.label === "High Confidence") return 3;
            if (c.label === "Good Confidence") return 2;
            if (c.label === "Moderate") return 1;
            return 0;
          };
          const scoreA = Math.max(0, ...allOf(a).map(badgeScore));
          const scoreB = Math.max(0, ...allOf(b).map(badgeScore));
          return scoreB - scoreA;
        }).map((gwt) => {
          const { game } = gwt;
          const allTrends: TrendResult[] = [
            ...(gwt.headToHeadTrends || []),
            ...(gwt.homeAtHomeH2HTrends || []),
            ...(gwt.homeTeamHomeTrends || []),
            ...(gwt.awayTeamAwayTrends || []),
            ...(gwt.homeTeamTrends || []),
            ...(gwt.awayTeamTrends || []),
          ].sort((a, b) => getConfidenceScore(b) - getConfidenceScore(a) || b.count - a.count);
          if (allTrends.length === 0) return null;
          return (
            <TrendInsightCard
              key={game.game_id}
              game={{ home: game.home, away: game.away, totals: game.totals }}
              trends={allTrends}
              detailsLink={`/game-details/${urlKey}?game_id=${encodeGameId(game.game_id)}`}
              sport={urlKey}
            />
          );
        })}
      </Box>
    </Box>
  );
}

export default function HomePage() {
  const inSeasonSports = sports
    .filter(
      (s) => s.inSeason && !SKIP_SPORTS.has(s.name) && s.path && SPORT_CONFIG[s.name]
    )
    .map((s) => ({
      name: s.name,
      urlKey: s.path!.slice(1), // "/mlb" → "mlb"
      ...SPORT_CONFIG[s.name],
    }));

  const [reportedCount, setReportedCount] = useState(0);
  const [hasAnyActiveGames, setHasAnyActiveGames] = useState(false);
  const [sectionScores, setSectionScores] = useState<Record<string, number>>({});

  const handleSectionReport = useCallback((sportName: string, hasGames: boolean, maxScore: number) => {
    setReportedCount((prev) => prev + 1);
    if (hasGames) setHasAnyActiveGames(true);
    setSectionScores((prev) => ({ ...prev, [sportName]: maxScore }));
  }, []);

  const allLoaded =
    inSeasonSports.length > 0 && reportedCount >= inSeasonSports.length;

  const sortedSports = allLoaded
    ? [...inSeasonSports].sort((a, b) => (sectionScores[b.name] ?? 0) - (sectionScores[a.name] ?? 0))
    : inSeasonSports;

  const now = new Date();
  const shortDate = [
    now.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase(),
    "·",
    now.toLocaleDateString("en-US", { month: "long" }).toUpperCase(),
    `${now.getDate()},`,
    now.getFullYear(),
  ].join(" ");

  // Once all sections have reported and none have active games, fall back to /mlb
  if (allLoaded && !hasAnyActiveGames) {
    return <Navigate to="/mlb" replace />;
  }

  return (
    <>
      <SEO
        title="GetSTAM — Today's Betting Trends"
        description="Today's strongest betting trends. Win streaks, H2H patterns, and historical probabilities updated every morning."
        canonicalPath="/"
      />
      <Container maxWidth="md" sx={{ py: 4 }}>
        {/* Hero */}
        <Box sx={{ mb: 4, pb: 3, borderBottom: "2px solid #e8eaf6" }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1.5,
            }}
          >
            <Typography
              sx={{
                fontSize: "0.72rem",
                fontWeight: 700,
                color: "#9e9e9e",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              {shortDate}
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.6,
                px: 1.2,
                py: 0.4,
                bgcolor: "#e8f5e9",
                borderRadius: 4,
              }}
            >
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  bgcolor: "#43a047",
                }}
              />
              <Typography
                sx={{
                  fontSize: "0.68rem",
                  fontWeight: 800,
                  color: "#2e7d32",
                  letterSpacing: "0.1em",
                }}
              >
                LIVE
              </Typography>
            </Box>
          </Box>
          <Typography
            variant="h2"
            component="h1"
            sx={{
              fontWeight: 800,
              lineHeight: 1.1,
              color: "#0d1117",
              fontSize: { xs: "2.2rem", md: "3rem" },
              letterSpacing: "-0.02em",
              mb: 2,
            }}
          >
            Today's Trends
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {inSeasonSports.map((sport) => (
              <Chip
                key={sport.name}
                label={sport.name}
                component={Link}
                to={`/${sport.urlKey}`}
                clickable
                size="small"
                sx={{
                  fontWeight: 700,
                  fontSize: "0.72rem",
                  letterSpacing: "0.05em",
                  borderColor: "#c5cae9",
                  color: "#3949ab",
                  "&:hover": { bgcolor: "#e8eaf6", borderColor: "#9fa8da" },
                }}
                variant="outlined"
              />
            ))}
          </Box>
        </Box>

        {/* Sport sections — sorted by max confidence score once all have loaded */}
        {sortedSports.map((sport) => (
          <SportSection
            key={sport.name}
            {...sport}
            onReport={(hasGames, maxScore) => handleSectionReport(sport.name, hasGames, maxScore)}
          />
        ))}

        {/* Email subscription */}
        <Box
          sx={{
            p: 3,
            bgcolor: "#f8f9ff",
            border: "1px solid #e8eaf6",
            borderRadius: 3,
          }}
        >
          <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
            Get tomorrow's trends in your inbox
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            The strongest betting streaks delivered every morning before game time.
          </Typography>
          <EmailSubscribeForm />
        </Box>
      </Container>
    </>
  );
}
