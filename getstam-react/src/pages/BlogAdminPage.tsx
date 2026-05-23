import React, { useState, useEffect } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import PublishIcon from "@mui/icons-material/Publish";
import ReactMarkdown from "react-markdown";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

interface AdminPost {
  id: number;
  title: string;
  slug: string;
  status: "draft" | "published";
  created_at: string;
  published_at: string | null;
  youtube_video_id: string | null;
  reading_time_minutes: number | null;
}

interface FullPost {
  id: number;
  title: string;
  slug: string;
  meta_description: string;
  excerpt: string;
  content: string;
  tags: string[];
  reading_time_minutes: number;
  status: string;
  category?: string;
  sport?: string;
  sport_key?: string;
  home_team?: string;
  away_team?: string;
  odds_event_id?: string;
  game_date?: string;
}

export default function BlogAdminPage() {
  const [password, setPassword] = useState(
    () => sessionStorage.getItem("blog_admin_password") || ""
  );
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const [posts, setPosts] = useState<AdminPost[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [postsError, setPostsError] = useState("");

  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [subscribing, setSubscribing] = useState(false);
  const [subscribeMsg, setSubscribeMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [actionMsg, setActionMsg] = useState<{ id: number; type: "success" | "error"; text: string } | null>(null);

  // Edit modal state
  const [editPost, setEditPost] = useState<FullPost | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editSaveMsg, setEditSaveMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [editTab, setEditTab] = useState(0);
  const [fetchingGameData, setFetchingGameData] = useState(false);
  const [gameDataMsg, setGameDataMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const isAuthenticated = !!password;

  useEffect(() => {
    if (isAuthenticated) loadPosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts`, {
        headers: { "X-API-KEY": passwordInput },
      });
      if (res.status === 401) { setAuthError("Incorrect API key."); return; }
      if (!res.ok) { setAuthError(`Server error: ${res.status}`); return; }
      sessionStorage.setItem("blog_admin_password", passwordInput);
      setPassword(passwordInput);
    } catch (e: any) {
      setAuthError(e.message || "Request failed");
    } finally {
      setAuthLoading(false);
    }
  }

  async function loadPosts() {
    setLoadingPosts(true);
    setPostsError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts`, {
        headers: { "X-API-KEY": password },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setPosts(data.posts || []);
    } catch (e: any) {
      setPostsError(e.message || "Failed to load posts");
    } finally {
      setLoadingPosts(false);
    }
  }

  async function handleOpenEdit(post: AdminPost) {
    setEditLoading(true);
    setEditSaveMsg(null);
    setEditTab(0);
    try {
      // Fetch full post from admin endpoint
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts`, {
        headers: { "X-API-KEY": password },
      });
      const data = await res.json();
      const full = (data.posts || []).find((p: any) => p.id === post.id);
      if (full) {
        // Get the full content too
        const res2 = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${post.id}`, {
          headers: { "X-API-KEY": password },
        });
        if (res2.ok) {
          const fullData = await res2.json();
          setEditPost({
            id: fullData.id,
            title: fullData.title || "",
            slug: fullData.slug || "",
            meta_description: fullData.meta_description || "",
            excerpt: fullData.excerpt || "",
            content: fullData.content || "",
            tags: fullData.tags || [],
            reading_time_minutes: fullData.reading_time_minutes || 0,
            status: fullData.status || "draft",
            category: fullData.category || "",
            sport: fullData.sport || undefined,
            sport_key: fullData.sport_key || undefined,
            home_team: fullData.home_team || "",
            away_team: fullData.away_team || "",
            odds_event_id: fullData.odds_event_id || "",
            game_date: fullData.game_date || "",
          });
        } else {
          setEditPost({
            id: post.id,
            title: post.title || "",
            slug: post.slug || "",
            meta_description: "",
            excerpt: "",
            content: "",
            tags: [],
            reading_time_minutes: post.reading_time_minutes || 0,
            status: post.status,
          });
        }
      }
    } catch (e: any) {
      console.error("Failed to load post for editing", e);
    } finally {
      setEditLoading(false);
    }
  }

  async function handleSaveEdit() {
    if (!editPost) return;
    setEditSaving(true);
    setEditSaveMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${editPost.id}`, {
        method: "PUT",
        headers: { "X-API-KEY": password, "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editPost.title,
          slug: editPost.slug,
          meta_description: editPost.meta_description,
          excerpt: editPost.excerpt,
          content: editPost.content,
          tags: editPost.tags,
          reading_time_minutes: editPost.reading_time_minutes,
          category: editPost.category,
          home_team: editPost.home_team,
          away_team: editPost.away_team,
          odds_event_id: editPost.odds_event_id,
          game_date: editPost.game_date,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setEditSaveMsg({ type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      setEditSaveMsg({ type: "success", text: "Saved!" });
      await loadPosts();
    } catch (e: any) {
      setEditSaveMsg({ type: "error", text: e.message || "Save failed" });
    } finally {
      setEditSaving(false);
    }
  }

  async function handleSaveAndPublish() {
    if (!editPost) return;
    await handleSaveEdit();
    // Then publish
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${editPost.id}/publish`, {
        method: "POST",
        headers: { "X-API-KEY": password },
      });
      if (res.ok) {
        setEditSaveMsg({ type: "success", text: "Saved and published!" });
        setEditPost(null);
        await loadPosts();
      }
    } catch (e: any) {
      setEditSaveMsg({ type: "error", text: e.message });
    }
  }

  async function handleGenerate() {
    if (!youtubeUrl.trim()) return;
    setGenerating(true);
    setGenerateMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/from-youtube`, {
        method: "POST",
        headers: { "X-API-KEY": password, "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: youtubeUrl }),
      });
      const data = await res.json();
      if (!res.ok) {
        setGenerateMsg({ type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      setGenerateMsg({ type: "success", text: `Draft created! Post ID: ${data.post_id}` });
      setYoutubeUrl("");
      await loadPosts();
    } catch (e: any) {
      setGenerateMsg({ type: "error", text: e.message || "Request failed" });
    } finally {
      setGenerating(false);
    }
  }

  async function handleSubscribe() {
    setSubscribing(true);
    setSubscribeMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/subscribe-youtube`, {
        method: "POST",
        headers: { "X-API-KEY": password },
      });
      const data = await res.json();
      if (!res.ok) {
        setSubscribeMsg({ type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      setSubscribeMsg({ type: "success", text: "Subscribed! YouTube will push new videos automatically." });
    } catch (e: any) {
      setSubscribeMsg({ type: "error", text: e.message || "Request failed" });
    } finally {
      setSubscribing(false);
    }
  }

  async function handlePublish(post: AdminPost) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${post.id}/publish`, {
        method: "POST",
        headers: { "X-API-KEY": password },
      });
      const data = await res.json();
      if (!res.ok) {
        setActionMsg({ id: post.id, type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      setActionMsg({ id: post.id, type: "success", text: "Published!" });
      await loadPosts();
    } catch (e: any) {
      setActionMsg({ id: post.id, type: "error", text: e.message });
    }
  }

  async function handleRefetchGameData() {
    if (!editPost) return;
    setFetchingGameData(true);
    setGameDataMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${editPost.id}/fetch-game-data`, {
        method: "POST",
        headers: { "X-API-KEY": password, "Content-Type": "application/json" },
        body: JSON.stringify({
          sport: editPost.sport,
          sport_key: editPost.sport_key,
          home_team: editPost.home_team,
          away_team: editPost.away_team,
          game_date: editPost.game_date,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setGameDataMsg({ type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      setGameDataMsg({ type: "success", text: `Game data fetched! Event ID: ${data.odds_event_id || "N/A"}` });
      if (data.odds_event_id) setEditPost((p) => p ? { ...p, odds_event_id: data.odds_event_id } : p);
      if (data.game_date) setEditPost((p) => p ? { ...p, game_date: data.game_date } : p);
    } catch (e: any) {
      setGameDataMsg({ type: "error", text: e.message || "Request failed" });
    } finally {
      setFetchingGameData(false);
    }
  }

  async function handleDelete(post: AdminPost) {
    if (!window.confirm(`Delete "${post.title}"?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/blog/posts/${post.id}`, {
        method: "DELETE",
        headers: { "X-API-KEY": password },
      });
      if (!res.ok) {
        const data = await res.json();
        setActionMsg({ id: post.id, type: "error", text: data.error || `Error ${res.status}` });
        return;
      }
      await loadPosts();
    } catch (e: any) {
      setActionMsg({ id: post.id, type: "error", text: e.message });
    }
  }

  // --- Password gate ---
  if (!isAuthenticated) {
    return (
      <Box
        component="form"
        onSubmit={handlePasswordSubmit}
        sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 2, px: 2 }}
      >
        <Typography variant="h5">Blog Admin — API Key Required</Typography>
        <TextField label="API Key" type="password" value={passwordInput} onChange={(e) => setPasswordInput(e.target.value)} size="small" sx={{ width: 320 }} autoFocus />
        {authError && <Alert severity="error">{authError}</Alert>}
        <Button type="submit" variant="contained" disabled={authLoading || !passwordInput}>
          {authLoading ? <CircularProgress size={20} /> : "Enter"}
        </Button>
      </Box>
    );
  }

  const drafts = posts.filter((p) => p.status === "draft");
  const published = posts.filter((p) => p.status === "published");

  return (
    <Box sx={{ maxWidth: 1000, mx: "auto", px: 2, py: 3 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>Blog Admin</Typography>

      {/* Subscribe */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>YouTube WebSub Subscription</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Subscribe so YouTube automatically pushes new video notifications. The daily cron job keeps this renewed.
        </Typography>
        <Button variant="outlined" onClick={handleSubscribe} disabled={subscribing}>
          {subscribing ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null} Subscribe
        </Button>
        {subscribeMsg && <Alert severity={subscribeMsg.type} sx={{ mt: 1 }}>{subscribeMsg.text}</Alert>}
      </Paper>

      {/* Generate */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Generate Draft from YouTube URL</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField label="YouTube URL or Video ID" value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} size="small" sx={{ flex: 1 }} placeholder="https://www.youtube.com/watch?v=..." />
          <Button variant="contained" onClick={handleGenerate} disabled={generating || !youtubeUrl.trim()}>
            {generating ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null} Generate
          </Button>
        </Box>
        {generateMsg && <Alert severity={generateMsg.type} sx={{ mt: 1 }}>{generateMsg.text}</Alert>}
      </Paper>

      <Divider sx={{ my: 3 }} />

      {loadingPosts && <CircularProgress />}
      {postsError && <Alert severity="error">{postsError}</Alert>}

      {/* Drafts */}
      <Typography variant="h6" gutterBottom>Drafts ({drafts.length})</Typography>
      {drafts.length === 0 && !loadingPosts && <Typography color="text.secondary" sx={{ mb: 2 }}>No drafts.</Typography>}
      {drafts.length > 0 && (
        <Table size="small" sx={{ mb: 4 }}>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {drafts.map((post) => (
              <React.Fragment key={post.id}>
                <TableRow>
                  <TableCell>{post.title}</TableCell>
                  <TableCell>{new Date(post.created_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" title="Edit" onClick={() => handleOpenEdit(post)}><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="primary" title="Publish" onClick={() => handlePublish(post)}><PublishIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(post)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
                {actionMsg?.id === post.id && (
                  <TableRow><TableCell colSpan={3} sx={{ py: 0 }}><Alert severity={actionMsg.type} sx={{ py: 0 }}>{actionMsg.text}</Alert></TableCell></TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Published */}
      <Typography variant="h6" gutterBottom>Published ({published.length})</Typography>
      {published.length === 0 && !loadingPosts && <Typography color="text.secondary">No published posts.</Typography>}
      {published.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Published</TableCell>
              <TableCell>Slug</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {published.map((post) => (
              <React.Fragment key={post.id}>
                <TableRow>
                  <TableCell>{post.title}</TableCell>
                  <TableCell>{post.published_at ? new Date(post.published_at).toLocaleDateString() : "—"}</TableCell>
                  <TableCell><Chip label={post.slug} size="small" component="a" href={`/blog/${post.slug}`} target="_blank" clickable /></TableCell>
                  <TableCell align="right">
                    <IconButton size="small" title="Edit" onClick={() => handleOpenEdit(post)}><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(post)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
                {actionMsg?.id === post.id && (
                  <TableRow><TableCell colSpan={4} sx={{ py: 0 }}><Alert severity={actionMsg.type} sx={{ py: 0 }}>{actionMsg.text}</Alert></TableCell></TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editPost} onClose={() => setEditPost(null)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Edit Post
          {editPost && <Typography variant="body2" color="text.secondary">{editPost.slug}</Typography>}
        </DialogTitle>
        <DialogContent dividers>
          {editLoading && <CircularProgress />}
          {editPost && !editLoading && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField label="Title" value={editPost.title} onChange={(e) => setEditPost({ ...editPost, title: e.target.value })} fullWidth />
              <TextField label="Meta Description (150-160 chars)" value={editPost.meta_description} onChange={(e) => setEditPost({ ...editPost, meta_description: e.target.value })} fullWidth helperText={`${editPost.meta_description.length} chars`} />
              <TextField label="Excerpt (2-3 sentences)" value={editPost.excerpt} onChange={(e) => setEditPost({ ...editPost, excerpt: e.target.value })} fullWidth multiline rows={2} />
              <TextField label="Tags (comma-separated)" value={(editPost.tags || []).join(", ")} onChange={(e) => setEditPost({ ...editPost, tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean) })} fullWidth />
              <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
                <TextField label="Reading Time (minutes)" type="number" value={editPost.reading_time_minutes} onChange={(e) => setEditPost({ ...editPost, reading_time_minutes: parseInt(e.target.value) || 0 })} sx={{ width: 200 }} />
                <FormControl sx={{ width: 180 }}>
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={editPost.category || ""}
                    label="Category"
                    onChange={(e) => setEditPost({ ...editPost, category: e.target.value })}
                  >
                    <MenuItem value=""><em>None</em></MenuItem>
                    <MenuItem value="preview">Preview</MenuItem>
                    <MenuItem value="trends">Trends</MenuItem>
                    <MenuItem value="analysis">Analysis</MenuItem>
                    <MenuItem value="news">News</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              {/* Game Data Section */}
              <Box sx={{ border: "1px solid #e0e0e0", borderRadius: 1, p: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Game Data
                  {editPost.sport && <Chip label={editPost.sport.toUpperCase()} size="small" sx={{ ml: 1 }} color="primary" />}
                </Typography>
                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 2 }}>
                  <TextField label="Home Team" value={editPost.home_team || ""} onChange={(e) => setEditPost({ ...editPost, home_team: e.target.value })} size="small" sx={{ flex: 1, minWidth: 140 }} />
                  <TextField label="Away Team" value={editPost.away_team || ""} onChange={(e) => setEditPost({ ...editPost, away_team: e.target.value })} size="small" sx={{ flex: 1, minWidth: 140 }} />
                  <TextField label="Odds Event ID" value={editPost.odds_event_id || ""} onChange={(e) => setEditPost({ ...editPost, odds_event_id: e.target.value })} size="small" sx={{ flex: 2, minWidth: 200 }} />
                  <TextField
                    label="Game Date"
                    type="date"
                    value={editPost.game_date || ""}
                    onChange={(e) => setEditPost({ ...editPost, game_date: e.target.value })}
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    sx={{ width: 160 }}
                  />
                </Box>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleRefetchGameData}
                  disabled={fetchingGameData || !editPost.home_team || !editPost.away_team}
                >
                  {fetchingGameData ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                  Re-fetch Game Data
                </Button>
                {gameDataMsg && <Alert severity={gameDataMsg.type} sx={{ mt: 1 }}>{gameDataMsg.text}</Alert>}
              </Box>

              <Box>
                <Tabs value={editTab} onChange={(_, v) => setEditTab(v)} sx={{ mb: 1 }}>
                  <Tab label="Edit Markdown" />
                  <Tab label="Preview" />
                </Tabs>
                {editTab === 0 && (
                  <TextField
                    label="Content (Markdown)"
                    value={editPost.content}
                    onChange={(e) => setEditPost({ ...editPost, content: e.target.value })}
                    fullWidth
                    multiline
                    rows={24}
                    inputProps={{ style: { fontFamily: "monospace", fontSize: "0.85rem" } }}
                  />
                )}
                {editTab === 1 && (
                  <Box sx={{ border: "1px solid #eee", borderRadius: 1, p: 2, minHeight: 400, "& h2": { mt: 3, mb: 1 }, "& p": { mb: 1.5, lineHeight: 1.7 }, "& ul": { pl: 3 } }}>
                    <ReactMarkdown>{editPost.content}</ReactMarkdown>
                  </Box>
                )}
              </Box>
            </Box>
          )}
          {editSaveMsg && <Alert severity={editSaveMsg.type} sx={{ mt: 2 }}>{editSaveMsg.text}</Alert>}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
          <Button onClick={() => setEditPost(null)}>Close</Button>
          <Button variant="outlined" onClick={handleSaveEdit} disabled={editSaving}>
            {editSaving ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null} Save Draft
          </Button>
          {editPost?.status === "draft" && (
            <Button variant="contained" color="primary" onClick={handleSaveAndPublish} disabled={editSaving}>
              Save &amp; Publish
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
