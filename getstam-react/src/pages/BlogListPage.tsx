import React, { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  CardMedia,
  Chip,
  CircularProgress,
  Container,
  Paper,
  Typography,
  Alert,
  Stack,
} from "@mui/material";
import SEO from "../components/SEO";
import EmailSubscribeForm from "../components/EmailSubscribeForm";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

const API_KEY = process.env.REACT_APP_API_KEY || "";

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "preview", label: "Previews" },
  { value: "trends", label: "Trends" },
  { value: "analysis", label: "Analysis" },
  { value: "news", label: "News" },
  { value: "daily_trends", label: "Daily Digest" },
];

const SPORTS = [
  { value: "", label: "All Sports" },
  { value: "mlb", label: "MLB" },
  { value: "nhl", label: "NHL" },
  { value: "nba", label: "NBA" },
  { value: "nfl", label: "NFL" },
];

const CATEGORY_COLORS: Record<string, "primary" | "success" | "warning" | "info" | "secondary"> = {
  preview: "primary",
  trends: "success",
  analysis: "warning",
  news: "info",
  daily_trends: "secondary",
};

interface BlogPostSummary {
  id: number;
  slug: string;
  title: string;
  excerpt: string | null;
  og_image_url: string | null;
  youtube_thumbnail_url: string | null;
  tags: string[] | null;
  reading_time_minutes: number | null;
  published_at: string;
  category?: string;
}

export default function BlogListPage() {
  const [posts, setPosts] = useState<BlogPostSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeCategory, setActiveCategory] = useState("");
  const [activeSport, setActiveSport] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ limit: "20" });
    if (activeCategory) params.set("category", activeCategory);
    if (activeSport) params.set("sport", activeSport);

    fetch(`${API_BASE_URL}/api/blog/posts?${params}`, {
      headers: { "X-API-KEY": API_KEY },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Error ${res.status}`);
        return res.json();
      })
      .then((data) => setPosts(data.posts || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeCategory, activeSport]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <SEO
        title="Blog"
        description="Sports betting analysis and tips from the GetSTAM team."
        canonicalPath="/blog"
      />
      <Paper elevation={2} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: "#1976d2", fontWeight: "bold" }}>
          GetSTAM Blog
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Sports betting analysis, trends, and insights.
        </Typography>
      </Paper>

      {/* Filters */}
      <Box sx={{ mb: 3, display: "flex", flexDirection: "column", gap: 1.5 }}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {CATEGORIES.map((c) => (
            <Chip
              key={c.value}
              label={c.label}
              onClick={() => setActiveCategory(c.value)}
              color={activeCategory === c.value ? "primary" : "default"}
              variant={activeCategory === c.value ? "filled" : "outlined"}
            />
          ))}
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {SPORTS.map((s) => (
            <Chip
              key={s.value}
              label={s.label}
              onClick={() => setActiveSport(s.value)}
              color={activeSport === s.value ? "secondary" : "default"}
              variant={activeSport === s.value ? "filled" : "outlined"}
              size="small"
            />
          ))}
        </Stack>
      </Box>

      {/* Subscribe banner */}
      <Paper
        elevation={3}
        sx={{
          p: 3,
          background: "linear-gradient(135deg, #1976d2, #42a5f5)",
          color: "#fff",
          borderRadius: 2,
          mb: 3,
        }}
      >
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Get Daily Trends in Your Inbox
        </Typography>
        <Typography variant="body2" sx={{ mb: 2, opacity: 0.9 }}>
          Every morning we send the strongest betting streaks across MLB, NHL, and NBA.
        </Typography>
        <EmailSubscribeForm compact={true} />
      </Paper>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && posts.length === 0 && (
        <Typography color="text.secondary">No posts found.</Typography>
      )}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
        {posts.map((post) => {
          const thumb = post.og_image_url || post.youtube_thumbnail_url;
          const date = post.published_at
            ? new Date(post.published_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })
            : "";
          return (
            <Box
              key={post.id}
              sx={{ flexBasis: { xs: "100%", sm: "calc(50% - 12px)", md: "calc(33.33% - 16px)" }, flexGrow: 0 }}
            >
              <Card
                component={RouterLink}
                to={`/blog/${post.slug}`}
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  textDecoration: "none",
                  color: "inherit",
                  transition: "box-shadow 0.2s",
                  "&:hover": { boxShadow: 6 },
                }}
              >
                {thumb && (
                  <CardMedia component="img" height="180" image={thumb} alt={post.title} />
                )}
                <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
                  {post.category && (
                    <Chip
                      label={post.category.charAt(0).toUpperCase() + post.category.slice(1)}
                      size="small"
                      color={CATEGORY_COLORS[post.category] || "default"}
                      sx={{ alignSelf: "flex-start", mb: 1 }}
                    />
                  )}
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    {post.title}
                  </Typography>
                  {post.excerpt && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1, flex: 1 }}>
                      {post.excerpt}
                    </Typography>
                  )}
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1 }}>
                    {(post.tags || []).slice(0, 4).map((tag) => (
                      <Chip key={tag} label={tag} size="small" variant="outlined" />
                    ))}
                  </Box>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="caption" color="text.secondary">{date}</Typography>
                    {post.reading_time_minutes && (
                      <Typography variant="caption" color="text.secondary">
                        {post.reading_time_minutes} min read
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Box>
          );
        })}
      </Box>
    </Container>
  );
}
