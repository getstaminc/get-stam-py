import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import { Link } from "react-router-dom";
import SEO from "../components/SEO";
import HistoricalGames from "../components/HistoricalGames";
import { encodeGameId } from "../utils/gameIdCrypto";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

const API_KEY = process.env.REACT_APP_API_KEY || "";

interface GameData {
  home_last_5: any[];
  away_last_5: any[];
  home_home_last_5: any[];
  away_away_last_5: any[];
  h2h_last_5: any[];
  trends: any;
}

interface BlogPost {
  id: number;
  slug: string;
  title: string;
  meta_description: string | null;
  excerpt: string | null;
  content: string | null;
  og_image_url: string | null;
  youtube_thumbnail_url: string | null;
  tags: string[] | null;
  reading_time_minutes: number | null;
  published_at: string;
  category?: string;
  sport?: string;
  sport_key?: string;
  home_team?: string;
  away_team?: string;
  odds_event_id?: string;
  game_data?: GameData | null;
}

// ---------------------------------------------------------------------------
// Daily Digest content parser + renderer
// ---------------------------------------------------------------------------

interface TrendItem { description: string }
interface TeamSection { label: string; trends: TrendItem[] }
interface GameCard { matchup: string; teams: TeamSection[] }
interface SportSection { name: string; games: GameCard[] }

function parseDailyDigest(markdown: string): { intro: string; sports: SportSection[] } {
  const lines = markdown.split("\n");
  let intro = "";
  const sports: SportSection[] = [];
  let currentSport: SportSection | null = null;
  let currentGame: GameCard | null = null;
  let currentTeam: TeamSection | null = null;

  const flushTeam = () => {
    if (currentTeam && currentGame) { currentGame.teams.push(currentTeam); currentTeam = null; }
  };
  const flushGame = () => {
    flushTeam();
    if (currentGame && currentSport) { currentSport.games.push(currentGame); currentGame = null; }
  };
  const flushSport = () => {
    flushGame();
    if (currentSport) { sports.push(currentSport); currentSport = null; }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("# ")) continue;
    if (line.startsWith("## ")) {
      flushSport();
      currentSport = { name: line.slice(3).trim(), games: [] };
    } else if (line.startsWith("### ")) {
      flushGame();
      currentGame = { matchup: line.slice(4).trim(), teams: [] };
    } else if (/^\*\*[^*]+\*\*:/.test(line)) {
      flushTeam();
      const label = line.match(/^\*\*([^*]+)\*\*:/)?.[1] || "";
      currentTeam = { label, trends: [] };
    } else if (line.startsWith("- ") && currentTeam) {
      currentTeam.trends.push({ description: line.slice(2).trim() });
    } else if (!currentSport && line.trim() && !line.startsWith("#")) {
      intro = intro ? intro + " " + line.trim() : line.trim();
    }
  }
  flushSport();
  return { intro, sports };
}

const SPORT_COLORS: Record<string, { bg: string; text: string; light: string }> = {
  MLB: { bg: "#1565c0", text: "#fff", light: "#e3f2fd" },
  NHL: { bg: "#00695c", text: "#fff", light: "#e0f2f1" },
  NBA: { bg: "#bf360c", text: "#fff", light: "#fbe9e7" },
};

function getTrendStyle(description: string) {
  const d = description.toLowerCase();
  if (d.includes("won") || d.includes("win")) return { bg: "#e8f5e9", color: "#2e7d32", border: "#a5d6a7", icon: <TrendingUpIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("lost") || d.includes("loss")) return { bg: "#ffebee", color: "#c62828", border: "#ef9a9a", icon: <TrendingDownIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("over")) return { bg: "#e3f2fd", color: "#1565c0", border: "#90caf9", icon: <TrendingUpIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("under")) return { bg: "#f3e5f5", color: "#6a1b9a", border: "#ce93d8", icon: <TrendingDownIcon sx={{ fontSize: 14 }} /> };
  return { bg: "#f5f5f5", color: "#424242", border: "#e0e0e0", icon: undefined };
}

function TrendPill({ trend }: { trend: TrendItem }) {
  const style = getTrendStyle(trend.description);
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.5,
        px: 1.5,
        py: 0.5,
        borderRadius: 4,
        fontSize: "0.78rem",
        fontWeight: 600,
        bgcolor: style.bg,
        color: style.color,
        border: `1px solid ${style.border}`,
        lineHeight: 1.4,
      }}
    >
      {style.icon}
      {trend.description}
    </Box>
  );
}

function DailyDigestContent({ content }: { content: string }) {
  const { intro, sports } = parseDailyDigest(content);

  return (
    <Box>
      {intro && (
        <Typography variant="body1" sx={{ mb: 3, color: "text.secondary", fontSize: "1.05rem" }}>
          {intro}
        </Typography>
      )}

      <Stack spacing={3}>
        {sports.map((sport) => {
          const colors = SPORT_COLORS[sport.name] || { bg: "#37474f", text: "#fff", light: "#eceff1" };
          return (
            <Box key={sport.name}>
              {/* Sport header */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  px: 2.5,
                  py: 1.5,
                  bgcolor: colors.bg,
                  borderRadius: "10px 10px 0 0",
                }}
              >
                <Typography variant="h6" sx={{ color: colors.text, fontWeight: 800, letterSpacing: 1 }}>
                  {sport.name}
                </Typography>
                <Chip
                  label={`${sport.games.length} game${sport.games.length !== 1 ? "s" : ""}`}
                  size="small"
                  sx={{ bgcolor: "rgba(255,255,255,0.2)", color: colors.text, fontWeight: 600, fontSize: "0.72rem" }}
                />
              </Box>

              {/* Games */}
              <Box
                sx={{
                  border: `2px solid ${colors.bg}`,
                  borderTop: "none",
                  borderRadius: "0 0 10px 10px",
                  overflow: "hidden",
                }}
              >
                {sport.games.map((game, gi) => (
                  <Box
                    key={gi}
                    sx={{
                      p: 2.5,
                      borderTop: gi > 0 ? "1px solid #f0f0f0" : "none",
                      bgcolor: gi % 2 === 0 ? "#fff" : "#fafafa",
                    }}
                  >
                    {/* Matchup header */}
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
                      <Box sx={{ width: 4, height: 20, bgcolor: colors.bg, borderRadius: 1 }} />
                      <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#1a1a1a" }}>
                        {game.matchup}
                      </Typography>
                    </Box>

                    {/* Team trends */}
                    <Stack spacing={1.5}>
                      {game.teams.map((team, ti) => (
                        <Box key={ti}>
                          <Typography
                            variant="caption"
                            sx={{
                              display: "block",
                              fontWeight: 700,
                              color: colors.bg,
                              textTransform: "uppercase",
                              letterSpacing: 0.5,
                              mb: 0.75,
                              fontSize: "0.7rem",
                            }}
                          >
                            {team.label}
                          </Typography>
                          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                            {team.trends.map((t, trendIdx) => (
                              <TrendPill key={trendIdx} trend={t} />
                            ))}
                          </Box>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                ))}
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

// ---------------------------------------------------------------------------
// GamePreviewSection — trends helpers (for game preview posts)
// ---------------------------------------------------------------------------

function getTrendColor(type: string): "success" | "error" | "warning" | "default" {
  if (!type) return "default";
  const t = type.toLowerCase();
  if (t.includes("win") || t.includes("over") || t.includes("cover")) return "success";
  if (t.includes("loss") || t.includes("under") || t.includes("fail")) return "error";
  return "default";
}

function TrendChip({ trend }: { trend: any }) {
  const color = getTrendColor(trend.type || "");
  const icon = color === "success" ? <TrendingUpIcon fontSize="small" /> : color === "error" ? <TrendingDownIcon fontSize="small" /> : undefined;
  return (
    <Chip icon={icon} label={trend.description} color={color} size="small" variant="outlined" />
  );
}

function TeamTrends({ teamName, trends }: { teamName: string; trends: any[] }) {
  if (!trends || trends.length === 0) return null;
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1, color: "#1976d2" }}>
        {teamName} Trends:
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {trends.map((t: any, i: number) => <TrendChip key={i} trend={t} />)}
      </Stack>
    </Box>
  );
}

function GamePreviewSection({ post }: { post: BlogPost }) {
  const [tab, setTab] = useState(0);
  const { home_team, away_team, sport_key, game_data } = post;

  if (!game_data || !home_team || !away_team) return null;

  const sportTypeMap: Record<string, string> = {
    baseball_mlb: "mlb",
    basketball_nba: "nba",
    icehockey_nhl: "nhl",
  };
  const sportType = (sport_key ? sportTypeMap[sport_key] : post.sport) || "mlb";
  const sport = sportType;

  const trends = game_data.trends || {};
  const homeTeamTrends: any[] = trends.homeTeamTrends || [];
  const awayTeamTrends: any[] = trends.awayTeamTrends || [];
  const headToHeadTrends: any[] = trends.headToHeadTrends || [];
  const homeTeamHomeTrends: any[] = trends.homeTeamHomeTrends || [];
  const awayTeamAwayTrends: any[] = trends.awayTeamAwayTrends || [];
  const homeAtHomeH2HTrends: any[] = trends.homeAtHomeH2HTrends || [];
  const hasTrends = homeTeamTrends.length > 0 || awayTeamTrends.length > 0 || headToHeadTrends.length > 0 ||
    homeTeamHomeTrends.length > 0 || awayTeamAwayTrends.length > 0 || homeAtHomeH2HTrends.length > 0;

  const gameDetailsUrl = post.odds_event_id
    ? `/game-details/${sportType}?game_id=${encodeGameId(post.odds_event_id)}`
    : null;

  return (
    <Box sx={{ mt: 4 }}>
      <Divider sx={{ mb: 3 }} />
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1, mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          {away_team} vs {home_team} — Recent Performance
        </Typography>
        {gameDetailsUrl && (
          <Button component={Link} to={gameDetailsUrl} variant="outlined" size="small">
            View Full Game Details
          </Button>
        )}
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Last 5" />
        <Tab label={`${home_team} Home Last 5`} />
        <Tab label={`${away_team} Away Last 5`} />
      </Tabs>

      {tab === 0 && (
        <Box>
          <HistoricalGames title={`${home_team} — Last 5 Games`} games={game_data.home_last_5} teamName={home_team} sportType={sportType as any} sport={sport} />
          <HistoricalGames title={`${away_team} — Last 5 Games`} games={game_data.away_last_5} teamName={away_team} sportType={sportType as any} sport={sport} />
        </Box>
      )}
      {tab === 1 && (
        <HistoricalGames title={`${home_team} — Last 5 Home Games`} games={game_data.home_home_last_5} teamName={home_team} sportType={sportType as any} sport={sport} />
      )}
      {tab === 2 && (
        <HistoricalGames title={`${away_team} — Last 5 Away Games`} games={game_data.away_away_last_5} teamName={away_team} sportType={sportType as any} sport={sport} />
      )}

      {game_data.h2h_last_5.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6" gutterBottom>Head to Head</Typography>
          <HistoricalGames title={`${away_team} @ ${home_team} — Last 5 H2H`} games={game_data.h2h_last_5} teamName={home_team} isHeadToHead sportType={sportType as any} sport={sport} />
        </Box>
      )}

      {hasTrends && (
        <Box sx={{ mt: 3, p: 2, backgroundColor: "#fafafa", borderRadius: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: "bold", mb: 2, color: "#1976d2" }}>
            🔥 Active Trends
          </Typography>
          <TeamTrends teamName={home_team!} trends={homeTeamTrends} />
          <TeamTrends teamName={away_team!} trends={awayTeamTrends} />
          {homeTeamHomeTrends.length > 0 && <TeamTrends teamName={`${home_team} (Home)`} trends={homeTeamHomeTrends} />}
          {awayTeamAwayTrends.length > 0 && <TeamTrends teamName={`${away_team} (Away)`} trends={awayTeamAwayTrends} />}
          {headToHeadTrends.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1, color: "#1976d2" }}>H2H Trends:</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {headToHeadTrends.map((t: any, i: number) => <TrendChip key={i} trend={t} />)}
              </Stack>
            </Box>
          )}
          {homeAtHomeH2HTrends.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1, color: "#1976d2" }}>{home_team} Home H2H:</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {homeAtHomeH2HTrends.map((t: any, i: number) => <TrendChip key={i} trend={t} />)}
              </Stack>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}

// ---------------------------------------------------------------------------
// BlogPostPage
// ---------------------------------------------------------------------------

const CATEGORY_LABELS: Record<string, string> = {
  preview: "Preview",
  trends: "Trends",
  analysis: "Analysis",
  news: "News",
  daily_trends: "Daily Trends",
};

const CATEGORY_COLORS: Record<string, string> = {
  preview: "#1976d2",
  trends: "#2e7d32",
  analysis: "#e65100",
  news: "#0277bd",
  daily_trends: "#6a1b9a",
};

export default function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) return;
    fetch(`${API_BASE_URL}/api/blog/posts/${slug}`, {
      headers: { "X-API-KEY": API_KEY },
    })
      .then((res) => {
        if (res.status === 404) throw new Error("Post not found");
        if (!res.ok) throw new Error(`Error ${res.status}`);
        return res.json();
      })
      .then((data) => setPost(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !post) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert severity="error">{error || "Post not found"}</Alert>
      </Container>
    );
  }

  const date = post.published_at
    ? new Date(post.published_at).toLocaleDateString("en-US", {
        year: "numeric", month: "long", day: "numeric",
      })
    : "";

  const ogImage = post.og_image_url || post.youtube_thumbnail_url || undefined;
  const isDailyDigest = post.category === "daily_trends";
  const categoryColor = CATEGORY_COLORS[post.category || ""] || "#757575";
  const categoryLabel = CATEGORY_LABELS[post.category || ""] || post.category;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <SEO
        title={post.title}
        description={post.meta_description || post.excerpt || ""}
        canonicalPath={`/blog/${slug}`}
        ogImage={ogImage}
      />

      {/* Hero */}
      <Box
        sx={{
          borderRadius: 3,
          overflow: "hidden",
          mb: 3,
          background: isDailyDigest
            ? "linear-gradient(135deg, #1a237e 0%, #283593 40%, #1565c0 100%)"
            : "linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)",
          color: "#fff",
          px: { xs: 3, md: 5 },
          py: { xs: 4, md: 5 },
        }}
      >
        {post.category && (
          <Box
            sx={{
              display: "inline-block",
              px: 1.5,
              py: 0.4,
              borderRadius: 2,
              bgcolor: "rgba(255,255,255,0.18)",
              fontSize: "0.75rem",
              fontWeight: 700,
              letterSpacing: 1,
              textTransform: "uppercase",
              mb: 2,
            }}
          >
            {categoryLabel}
          </Box>
        )}
        <Typography
          variant="h3"
          component="h1"
          sx={{ fontWeight: 800, lineHeight: 1.2, mb: 2, fontSize: { xs: "1.8rem", md: "2.4rem" } }}
        >
          {post.title}
        </Typography>
        {post.excerpt && (
          <Typography variant="body1" sx={{ opacity: 0.85, mb: 2, fontSize: "1.05rem", lineHeight: 1.6 }}>
            {post.excerpt}
          </Typography>
        )}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", opacity: 0.8, fontSize: "0.85rem" }}>
          {date && <span>{date}</span>}
          {post.reading_time_minutes && <span>· {post.reading_time_minutes} min read</span>}
        </Box>
      </Box>

      {/* Thumbnail (non-daily-digest posts) */}
      {ogImage && !isDailyDigest && (
        <Box
          component="img"
          src={ogImage}
          alt={post.title}
          sx={{ width: "100%", maxHeight: 400, objectFit: "cover", borderRadius: 2, mb: 3 }}
        />
      )}

      {/* Tags */}
      {(post.tags || []).length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 3 }}>
          {(post.tags || []).map((tag) => (
            <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ borderRadius: 2 }} />
          ))}
        </Box>
      )}

      {/* Content */}
      <Paper elevation={0} sx={{ p: { xs: 2, md: 4 }, border: "1px solid #e8eaf6", borderRadius: 3 }}>
        {post.content && (
          isDailyDigest
            ? <DailyDigestContent content={post.content} />
            : (
              <Box
                sx={{
                  "& h2": { mt: 4, mb: 1.5, fontSize: "1.5rem", fontWeight: 700, color: "#1a237e" },
                  "& h3": { mt: 3, mb: 1, fontSize: "1.2rem", fontWeight: 600, color: "#283593" },
                  "& p": { mb: 2, lineHeight: 1.9, color: "#333" },
                  "& ul, & ol": { mb: 2, pl: 3 },
                  "& li": { mb: 0.75, lineHeight: 1.8 },
                  "& strong": { fontWeight: 700, color: "#1a1a1a" },
                }}
              >
                <ReactMarkdown>{post.content}</ReactMarkdown>
              </Box>
            )
        )}

        {post.game_data && <GamePreviewSection post={post} />}
      </Paper>
    </Container>
  );
}
