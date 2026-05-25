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
  sport?: string;
  sport_key?: string;
  home_team?: string;
  away_team?: string;
  odds_event_id?: string;
  game_data?: GameData | null;
}

// ---------------------------------------------------------------------------
// GamePreviewSection — trends helpers
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

  // Map sport_key -> sportType for HistoricalGames
  const sportTypeMap: Record<string, string> = {
    baseball_mlb: "mlb",
    basketball_nba: "nba",
    icehockey_nhl: "nhl",
  };
  const sportType = (sport_key ? sportTypeMap[sport_key] : post.sport) || "mlb";
  const sport = sportType; // for link slugs

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
          <Button
            component={Link}
            to={gameDetailsUrl}
            variant="outlined"
            size="small"
          >
            View Full Game Details
          </Button>
        )}
      </Box>

      {/* Last 5 sub-tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Last 5" />
        <Tab label={`${home_team} Home Last 5`} />
        <Tab label={`${away_team} Away Last 5`} />
      </Tabs>

      {tab === 0 && (
        <Box>
          <HistoricalGames
            title={`${home_team} — Last 5 Games`}
            games={game_data.home_last_5}
            teamName={home_team}
            sportType={sportType as any}
            sport={sport}
          />
          <HistoricalGames
            title={`${away_team} — Last 5 Games`}
            games={game_data.away_last_5}
            teamName={away_team}
            sportType={sportType as any}
            sport={sport}
          />
        </Box>
      )}

      {tab === 1 && (
        <HistoricalGames
          title={`${home_team} — Last 5 Home Games`}
          games={game_data.home_home_last_5}
          teamName={home_team}
          sportType={sportType as any}
          sport={sport}
        />
      )}

      {tab === 2 && (
        <HistoricalGames
          title={`${away_team} — Last 5 Away Games`}
          games={game_data.away_away_last_5}
          teamName={away_team}
          sportType={sportType as any}
          sport={sport}
        />
      )}

      {/* H2H */}
      {game_data.h2h_last_5.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6" gutterBottom>Head to Head</Typography>
          <HistoricalGames
            title={`${away_team} @ ${home_team} — Last 5 H2H`}
            games={game_data.h2h_last_5}
            teamName={home_team}
            isHeadToHead
            sportType={sportType as any}
            sport={sport}
          />
        </Box>
      )}

      {/* Trends */}
      {hasTrends && (
        <Box sx={{ mt: 3, p: 2, backgroundColor: "#fafafa", borderRadius: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: "bold", mb: 2, color: "#1976d2" }}>
            🔥 Active Trends
          </Typography>
          <TeamTrends teamName={home_team!} trends={homeTeamTrends} />
          <TeamTrends teamName={away_team!} trends={awayTeamTrends} />
          {homeTeamHomeTrends.length > 0 && (
            <TeamTrends teamName={`${home_team} (Home)`} trends={homeTeamHomeTrends} />
          )}
          {awayTeamAwayTrends.length > 0 && (
            <TeamTrends teamName={`${away_team} (Away)`} trends={awayTeamAwayTrends} />
          )}
          {headToHeadTrends.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1, color: "#1976d2" }}>
                H2H Trends:
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {headToHeadTrends.map((t: any, i: number) => <TrendChip key={i} trend={t} />)}
              </Stack>
            </Box>
          )}
          {homeAtHomeH2HTrends.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: "bold", mb: 1, color: "#1976d2" }}>
                {home_team} Home H2H:
              </Typography>
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
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  const ogImage = post.og_image_url || post.youtube_thumbnail_url || undefined;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <SEO
        title={post.title}
        description={post.meta_description || post.excerpt || ""}
        canonicalPath={`/blog/${slug}`}
        ogImage={ogImage}
      />
      <Paper elevation={2} sx={{ p: { xs: 2, md: 4 } }}>
        {ogImage && (
          <Box
            component="img"
            src={ogImage}
            alt={post.title}
            sx={{ width: "100%", maxHeight: 400, objectFit: "cover", borderRadius: 1, mb: 3 }}
          />
        )}

        <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: "bold" }}>
          {post.title}
        </Typography>

        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
          {date && (
            <Typography variant="body2" color="text.secondary">
              {date}
            </Typography>
          )}
          {post.reading_time_minutes && (
            <Typography variant="body2" color="text.secondary">
              {post.reading_time_minutes} min read
            </Typography>
          )}
        </Box>

        {(post.tags || []).length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 3 }}>
            {(post.tags || []).map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" />
            ))}
          </Box>
        )}

        <Divider sx={{ mb: 3 }} />

        {post.content && (
          <Box
            sx={{
              "& h2": { mt: 4, mb: 1.5, fontSize: "1.5rem", fontWeight: 700 },
              "& h3": { mt: 3, mb: 1, fontSize: "1.2rem", fontWeight: 600 },
              "& p": { mb: 2, lineHeight: 1.8 },
              "& ul, & ol": { mb: 2, pl: 3 },
              "& li": { mb: 0.5 },
              "& strong": { fontWeight: 700 },
            }}
          >
            <ReactMarkdown>{post.content}</ReactMarkdown>
          </Box>
        )}

        {post.game_data && <GamePreviewSection post={post} />}
      </Paper>
    </Container>
  );
}
