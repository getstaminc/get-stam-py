import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Radio,
  RadioGroup,
  FormControlLabel,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Chip,
} from "@mui/material";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

interface PlaceholderGroup {
  player_id: number;
  normalized_name: string;
  batter_props: number;
  pitcher_props: number;
  total_props: number;
  first_game: string | null;
  last_game: string | null;
}

interface MismatchRecord {
  id: number;
  game_date: string;
  odds_home_team: string;
  odds_away_team: string;
  player_type: "batter" | "pitcher";
  batter_props_id: number | null;
  pitcher_props_id: number | null;
}

interface PlayerGroup {
  player_id: number;
  odds_name: string;
  total_mismatches: number;
  mismatch_ids: number[];
  records: MismatchRecord[];
}

interface Candidate {
  espn_player_id: string;
  espn_display_name: string;
  similarity_score: number;
  espn_event_id: string;
}

interface PlayerCardState {
  loadingCandidates: boolean;
  candidates: Candidate[] | null;
  candidatesError: string | null;
  selectedCandidate: string; // espn_player_id
  espnEventId: string | null;
  resolving: boolean;
  resolveSuccess: string | null;
  resolveError: string | null;
  manualEspnId: string;
  manualEspnName: string;
}

function makeCardState(): PlayerCardState {
  return {
    loadingCandidates: false,
    candidates: null,
    candidatesError: null,
    selectedCandidate: "",
    espnEventId: null,
    resolving: false,
    resolveSuccess: null,
    resolveError: null,
    manualEspnId: "",
    manualEspnName: "",
  };
}

export default function MismatchPlayersPage() {
  const [password, setPassword] = useState(
    () => sessionStorage.getItem("internal_password") || ""
  );
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const [groups, setGroups] = useState<PlayerGroup[]>([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [groupsError, setGroupsError] = useState("");
  const [cardStates, setCardStates] = useState<Record<number, PlayerCardState>>({});

  const [placeholders, setPlaceholders] = useState<PlaceholderGroup[]>([]);
  const [loadingPlaceholders, setLoadingPlaceholders] = useState(false);
  const [placeholdersError, setPlaceholdersError] = useState("");
  const [placeholderCardStates, setPlaceholderCardStates] = useState<Record<number, PlayerCardState>>({});

  const isAuthenticated = !!password;

  // Load mismatches + placeholders once authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    loadMismatches();
    loadPlaceholders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  async function loadMismatches() {
    setLoadingGroups(true);
    setGroupsError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/internal/mlb/mismatches`, {
        headers: { "X-Internal-Password": password },
      });
      if (!res.ok) {
        if (res.status === 401) {
          setGroupsError("Unauthorized — password may have changed.");
        } else {
          setGroupsError(`Error ${res.status}: ${res.statusText}`);
        }
        return;
      }
      const data: PlayerGroup[] = await res.json();
      setGroups(data);
      const states: Record<number, PlayerCardState> = {};
      data.forEach((g) => { states[g.player_id] = makeCardState(); });
      setCardStates(states);
    } catch (e: any) {
      setGroupsError(e.message || "Failed to load mismatches");
    } finally {
      setLoadingGroups(false);
    }
  }

  async function loadPlaceholders() {
    setLoadingPlaceholders(true);
    setPlaceholdersError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/internal/mlb/placeholders`, {
        headers: { "X-Internal-Password": password },
      });
      if (!res.ok) {
        setPlaceholdersError(`Error ${res.status}: ${res.statusText}`);
        return;
      }
      const data: PlaceholderGroup[] = await res.json();
      setPlaceholders(data);
      const states: Record<number, PlayerCardState> = {};
      data.forEach((g) => { states[g.player_id] = makeCardState(); });
      setPlaceholderCardStates(states);
    } catch (e: any) {
      setPlaceholdersError(e.message || "Failed to load placeholder players");
    } finally {
      setLoadingPlaceholders(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/internal/mlb/mismatches`, {
        headers: { "X-Internal-Password": passwordInput },
      });
      if (res.status === 401) {
        setAuthError("Incorrect password.");
        return;
      }
      if (!res.ok) {
        setAuthError(`Server error: ${res.status}`);
        return;
      }
      sessionStorage.setItem("internal_password", passwordInput);
      setPassword(passwordInput);
    } catch (e: any) {
      setAuthError(e.message || "Request failed");
    } finally {
      setAuthLoading(false);
    }
  }

  function updateCardState(playerId: number, patch: Partial<PlayerCardState>) {
    setCardStates((prev) => ({
      ...prev,
      [playerId]: { ...prev[playerId], ...patch },
    }));
  }

  async function handleFindCandidates(playerId: number) {
    updateCardState(playerId, {
      loadingCandidates: true,
      candidates: null,
      candidatesError: null,
      selectedCandidate: "",
      resolveSuccess: null,
      resolveError: null,
    });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/mismatches/${playerId}/candidates`,
        { headers: { "X-Internal-Password": password } }
      );
      const data = await res.json();
      if (!res.ok) {
        updateCardState(playerId, { candidatesError: data.error || `Error ${res.status}` });
        return;
      }
      updateCardState(playerId, { candidates: data.candidates || [], espnEventId: data.espn_event_id || null });
    } catch (e: any) {
      updateCardState(playerId, { candidatesError: e.message || "Request failed" });
    } finally {
      updateCardState(playerId, { loadingCandidates: false });
    }
  }

  async function handleConfirmMatch(group: PlayerGroup) {
    const state = cardStates[group.player_id];
    if (!state?.selectedCandidate || !state.candidates) return;

    const chosen = state.candidates.find(
      (c) => c.espn_player_id === state.selectedCandidate
    );
    if (!chosen) return;

    updateCardState(group.player_id, { resolving: true, resolveSuccess: null, resolveError: null });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/mismatches/${group.player_id}/resolve`,
        {
          method: "POST",
          headers: {
            "X-Internal-Password": password,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            espn_player_id: chosen.espn_player_id,
            espn_name: chosen.espn_display_name,
          }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        updateCardState(group.player_id, { resolveError: data.error || `Error ${res.status}` });
        return;
      }
      const processed = (data.dates_processed || []).join(", ");
      const skipped = (data.dates_skipped || []).join(", ");
      const msg =
        `Resolved! ESPN ID set to ${chosen.espn_player_id}.` +
        (processed ? ` Dates populated: ${processed}.` : "") +
        (skipped ? ` Dates skipped (no event found): ${skipped}.` : "");
      updateCardState(group.player_id, { resolveSuccess: msg });
      // Remove this group from the list
      setGroups((prev) => prev.filter((g) => g.player_id !== group.player_id));
    } catch (e: any) {
      updateCardState(group.player_id, { resolveError: e.message || "Request failed" });
    } finally {
      updateCardState(group.player_id, { resolving: false });
    }
  }

  async function handleManualResolve(group: PlayerGroup) {
    const state = cardStates[group.player_id];
    if (!state?.manualEspnId.trim()) return;

    updateCardState(group.player_id, { resolving: true, resolveSuccess: null, resolveError: null });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/mismatches/${group.player_id}/resolve`,
        {
          method: "POST",
          headers: {
            "X-Internal-Password": password,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            espn_player_id: state.manualEspnId.trim(),
            espn_name: state.manualEspnName.trim(),
          }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        updateCardState(group.player_id, { resolveError: data.error || `Error ${res.status}` });
        return;
      }
      const processed = (data.dates_processed || []).join(", ");
      const skipped = (data.dates_skipped || []).join(", ");
      const msg =
        `Resolved! ESPN ID set to ${state.manualEspnId.trim()}.` +
        (processed ? ` Dates populated: ${processed}.` : "") +
        (skipped ? ` Dates skipped: ${skipped}.` : "");
      updateCardState(group.player_id, { resolveSuccess: msg });
      setGroups((prev) => prev.filter((g) => g.player_id !== group.player_id));
    } catch (e: any) {
      updateCardState(group.player_id, { resolveError: e.message || "Request failed" });
    } finally {
      updateCardState(group.player_id, { resolving: false });
    }
  }

  function updatePlaceholderCardState(playerId: number, patch: Partial<PlayerCardState>) {
    setPlaceholderCardStates((prev) => ({
      ...prev,
      [playerId]: { ...prev[playerId], ...patch },
    }));
  }

  async function handleFindPlaceholderCandidates(playerId: number) {
    updatePlaceholderCardState(playerId, {
      loadingCandidates: true,
      candidates: null,
      candidatesError: null,
      selectedCandidate: "",
      resolveSuccess: null,
      resolveError: null,
    });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/placeholders/${playerId}/candidates`,
        { headers: { "X-Internal-Password": password } }
      );
      const data = await res.json();
      if (!res.ok) {
        updatePlaceholderCardState(playerId, { candidatesError: data.error || `Error ${res.status}` });
        return;
      }
      updatePlaceholderCardState(playerId, { candidates: data.candidates || [] });
    } catch (e: any) {
      updatePlaceholderCardState(playerId, { candidatesError: e.message || "Request failed" });
    } finally {
      updatePlaceholderCardState(playerId, { loadingCandidates: false });
    }
  }

  async function handleConfirmPlaceholderMatch(group: PlaceholderGroup) {
    const state = placeholderCardStates[group.player_id];
    if (!state?.selectedCandidate || !state.candidates) return;
    const chosen = state.candidates.find((c) => c.espn_player_id === state.selectedCandidate);
    if (!chosen) return;

    updatePlaceholderCardState(group.player_id, { resolving: true, resolveSuccess: null, resolveError: null });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/placeholders/${group.player_id}/resolve`,
        {
          method: "POST",
          headers: { "X-Internal-Password": password, "Content-Type": "application/json" },
          body: JSON.stringify({ espn_player_id: chosen.espn_player_id, espn_name: chosen.espn_display_name }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        updatePlaceholderCardState(group.player_id, { resolveError: data.error || `Error ${res.status}` });
        return;
      }
      const processed = (data.dates_processed || []).join(", ");
      const skipped = (data.dates_skipped || []).join(", ");
      const msg =
        `Resolved! ESPN ID set to ${chosen.espn_player_id}.` +
        (processed ? ` Dates populated: ${processed}.` : "") +
        (skipped ? ` Dates skipped: ${skipped}.` : "");
      updatePlaceholderCardState(group.player_id, { resolveSuccess: msg });
      setPlaceholders((prev) => prev.filter((g) => g.player_id !== group.player_id));
    } catch (e: any) {
      updatePlaceholderCardState(group.player_id, { resolveError: e.message || "Request failed" });
    } finally {
      updatePlaceholderCardState(group.player_id, { resolving: false });
    }
  }

  async function handleManualPlaceholderResolve(group: PlaceholderGroup) {
    const state = placeholderCardStates[group.player_id];
    if (!state?.manualEspnId.trim()) return;

    updatePlaceholderCardState(group.player_id, { resolving: true, resolveSuccess: null, resolveError: null });
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/internal/mlb/placeholders/${group.player_id}/resolve`,
        {
          method: "POST",
          headers: { "X-Internal-Password": password, "Content-Type": "application/json" },
          body: JSON.stringify({ espn_player_id: state.manualEspnId.trim(), espn_name: state.manualEspnName.trim() }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        updatePlaceholderCardState(group.player_id, { resolveError: data.error || `Error ${res.status}` });
        return;
      }
      const processed = (data.dates_processed || []).join(", ");
      const skipped = (data.dates_skipped || []).join(", ");
      const msg =
        `Resolved! ESPN ID set to ${state.manualEspnId.trim()}.` +
        (processed ? ` Dates populated: ${processed}.` : "") +
        (skipped ? ` Dates skipped: ${skipped}.` : "");
      updatePlaceholderCardState(group.player_id, { resolveSuccess: msg });
      setPlaceholders((prev) => prev.filter((g) => g.player_id !== group.player_id));
    } catch (e: any) {
      updatePlaceholderCardState(group.player_id, { resolveError: e.message || "Request failed" });
    } finally {
      updatePlaceholderCardState(group.player_id, { resolving: false });
    }
  }

  // --- Password gate ---
  if (!isAuthenticated) {
    return (
      <Box
        component="form"
        onSubmit={handlePasswordSubmit}
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
          gap: 2,
          px: 2,
        }}
      >
        <Typography variant="h5">Internal Tool — Password Required</Typography>
        <TextField
          label="Password"
          type="password"
          value={passwordInput}
          onChange={(e) => setPasswordInput(e.target.value)}
          size="small"
          sx={{ width: 280 }}
          autoFocus
        />
        {authError && <Alert severity="error">{authError}</Alert>}
        <Button
          type="submit"
          variant="contained"
          disabled={authLoading || !passwordInput}
        >
          {authLoading ? <CircularProgress size={20} /> : "Enter"}
        </Button>
      </Box>
    );
  }

  // --- Main UI ---
  return (
    <Box sx={{ maxWidth: 900, mx: "auto", px: 2, py: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          MLB Player Mismatch Resolution
        </Typography>
        {!loadingGroups && (
          <Chip
            label={`${groups.length} unresolved`}
            color={groups.length > 0 ? "warning" : "success"}
            size="small"
          />
        )}
        <Button size="small" variant="outlined" onClick={loadMismatches} disabled={loadingGroups}>
          Refresh
        </Button>
      </Box>

      {loadingGroups && <CircularProgress />}
      {groupsError && <Alert severity="error">{groupsError}</Alert>}
      {!loadingGroups && groups.length === 0 && !groupsError && (
        <Typography color="text.secondary">No unresolved mismatches.</Typography>
      )}

      {groups.map((group) => {

        const state = cardStates[group.player_id] || makeCardState();
        const selectedCandidate = state.candidates?.find(
          (c) => c.espn_player_id === state.selectedCandidate
        );

        return (
          <Card key={group.player_id} sx={{ mb: 2 }}>
            <CardContent>
              {/* Header */}
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
                <Typography variant="h6" fontWeight={600}>
                  {group.odds_name}
                </Typography>
                <Chip label={`${group.total_mismatches} mismatches`} size="small" />
                <Typography variant="body2" color="text.secondary">
                  player_id: {group.player_id}
                </Typography>
              </Box>

              {/* Dates table */}
              <Table size="small" sx={{ mb: 2 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Home</TableCell>
                    <TableCell>Away</TableCell>
                    <TableCell>Type</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {group.records.map((rec) => (
                    <TableRow key={rec.id}>
                      <TableCell>{rec.game_date}</TableCell>
                      <TableCell>{rec.odds_home_team}</TableCell>
                      <TableCell>{rec.odds_away_team}</TableCell>
                      <TableCell>{rec.player_type === "batter" ? "B" : "P"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Find candidates */}
              <Button
                variant="outlined"
                size="small"
                onClick={() => handleFindCandidates(group.player_id)}
                disabled={state.loadingCandidates}
              >
                {state.loadingCandidates ? (
                  <CircularProgress size={16} sx={{ mr: 1 }} />
                ) : null}
                Find Candidates
              </Button>

              {state.candidatesError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {state.candidatesError}
                </Alert>
              )}

              {/* Candidate list */}
              {state.candidates !== null && (
                <Box sx={{ mt: 1.5 }}>
                  {state.espnEventId && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontFamily: "monospace" }}>
                      ESPN event ID: <strong>{state.espnEventId}</strong>
                    </Typography>
                  )}
                  {state.candidates.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No candidates found.
                    </Typography>
                  ) : (
                    <RadioGroup
                      value={state.selectedCandidate}
                      onChange={(e) =>
                        updateCardState(group.player_id, { selectedCandidate: e.target.value })
                      }
                    >
                      {state.candidates.map((c) => (
                        <FormControlLabel
                          key={c.espn_player_id}
                          value={c.espn_player_id}
                          control={<Radio size="small" />}
                          label={
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                              <Typography variant="body2">
                                {c.espn_display_name}{" "}
                                <Typography component="span" variant="body2" color="text.secondary">
                                  (ID: {c.espn_player_id}) — score: {c.similarity_score.toFixed(2)}
                                </Typography>
                              </Typography>
                              {(c as any).source === "db_search" && (
                                <Chip label="DB" size="small" color="info" sx={{ height: 18, fontSize: "0.65rem" }} />
                              )}
                            </Box>
                          }
                        />
                      ))}
                    </RadioGroup>
                  )}

                  {state.selectedCandidate && (
                    <Button
                      variant="contained"
                      size="small"
                      sx={{ mt: 1 }}
                      onClick={() => handleConfirmMatch(group)}
                      disabled={state.resolving}
                    >
                      {state.resolving ? (
                        <CircularProgress size={16} sx={{ mr: 1 }} />
                      ) : null}
                      Confirm Match: {selectedCandidate?.espn_display_name}
                    </Button>
                  )}
                </Box>
              )}

              {/* Manual ESPN ID override */}
              <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid #eee" }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Enter ESPN player ID manually:
                </Typography>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                  <TextField
                    size="small"
                    label="ESPN Player ID"
                    value={state.manualEspnId}
                    onChange={(e) => updateCardState(group.player_id, { manualEspnId: e.target.value })}
                    sx={{ width: 160 }}
                    placeholder="e.g. 32129"
                  />
                  <TextField
                    size="small"
                    label="Player name (optional)"
                    value={state.manualEspnName}
                    onChange={(e) => updateCardState(group.player_id, { manualEspnName: e.target.value })}
                    sx={{ flex: 1, minWidth: 160 }}
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleManualResolve(group)}
                    disabled={!state.manualEspnId.trim() || state.resolving}
                  >
                    {state.resolving ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                    Resolve
                  </Button>
                </Box>
              </Box>

              {state.resolveSuccess && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  {state.resolveSuccess}
                </Alert>
              )}
              {state.resolveError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {state.resolveError}
                </Alert>
              )}
            </CardContent>
          </Card>
        );
      })}

      {/* ------------------------------------------------------------------ */}
      {/* Placeholder Players section                                         */}
      {/* ------------------------------------------------------------------ */}
      <Box sx={{ mt: 4, mb: 2, display: "flex", alignItems: "center", gap: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Unlinked Players
        </Typography>
        {!loadingPlaceholders && (
          <Chip
            label={`${placeholders.length} unlinked`}
            color={placeholders.length > 0 ? "warning" : "success"}
            size="small"
          />
        )}
        <Button size="small" variant="outlined" onClick={loadPlaceholders} disabled={loadingPlaceholders}>
          Refresh
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Players in <code>mlb_players</code> with no ESPN ID — accent issues, hyphenated names, Jr. suffixes, etc.
      </Typography>

      {loadingPlaceholders && <CircularProgress />}
      {placeholdersError && <Alert severity="error">{placeholdersError}</Alert>}
      {!loadingPlaceholders && placeholders.length === 0 && !placeholdersError && (
        <Typography color="text.secondary">No unlinked players.</Typography>
      )}

      {placeholders.map((group) => {
        const state = placeholderCardStates[group.player_id] || makeCardState();
        const selectedCandidate = state.candidates?.find(
          (c) => c.espn_player_id === state.selectedCandidate
        );

        return (
          <Card key={group.player_id} sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <Typography variant="h6" fontWeight={600}>
                  {group.normalized_name}
                </Typography>
                <Chip label={`${group.total_props} props`} size="small" />
                {group.batter_props > 0 && <Chip label={`${group.batter_props}B`} size="small" variant="outlined" />}
                {group.pitcher_props > 0 && <Chip label={`${group.pitcher_props}P`} size="small" variant="outlined" />}
                <Typography variant="body2" color="text.secondary">
                  player_id: {group.player_id}
                </Typography>
              </Box>
              {group.first_game && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {group.first_game} – {group.last_game}
                </Typography>
              )}

              <Button
                variant="outlined"
                size="small"
                onClick={() => handleFindPlaceholderCandidates(group.player_id)}
                disabled={state.loadingCandidates}
              >
                {state.loadingCandidates ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                Find Candidates
              </Button>

              {state.candidatesError && (
                <Alert severity="error" sx={{ mt: 1 }}>{state.candidatesError}</Alert>
              )}

              {state.candidates !== null && (
                <Box sx={{ mt: 1.5 }}>
                  {state.candidates.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No candidates found.</Typography>
                  ) : (
                    <RadioGroup
                      value={state.selectedCandidate}
                      onChange={(e) => updatePlaceholderCardState(group.player_id, { selectedCandidate: e.target.value })}
                    >
                      {state.candidates.map((c) => (
                        <FormControlLabel
                          key={c.espn_player_id}
                          value={c.espn_player_id}
                          control={<Radio size="small" />}
                          label={
                            <Typography variant="body2">
                              {c.espn_display_name}{" "}
                              <Typography component="span" variant="body2" color="text.secondary">
                                (ID: {c.espn_player_id}) — score: {c.similarity_score.toFixed(2)}
                              </Typography>
                            </Typography>
                          }
                        />
                      ))}
                    </RadioGroup>
                  )}
                  {state.selectedCandidate && (
                    <Button
                      variant="contained"
                      size="small"
                      sx={{ mt: 1 }}
                      onClick={() => handleConfirmPlaceholderMatch(group)}
                      disabled={state.resolving}
                    >
                      {state.resolving ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                      Confirm Match: {selectedCandidate?.espn_display_name}
                    </Button>
                  )}
                </Box>
              )}

              <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid #eee" }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Enter ESPN player ID manually:
                </Typography>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                  <TextField
                    size="small"
                    label="ESPN Player ID"
                    value={state.manualEspnId}
                    onChange={(e) => updatePlaceholderCardState(group.player_id, { manualEspnId: e.target.value })}
                    sx={{ width: 160 }}
                    placeholder="e.g. 32129"
                  />
                  <TextField
                    size="small"
                    label="Player name (optional)"
                    value={state.manualEspnName}
                    onChange={(e) => updatePlaceholderCardState(group.player_id, { manualEspnName: e.target.value })}
                    sx={{ flex: 1, minWidth: 160 }}
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleManualPlaceholderResolve(group)}
                    disabled={!state.manualEspnId.trim() || state.resolving}
                  >
                    {state.resolving ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                    Resolve
                  </Button>
                </Box>
              </Box>

              {state.resolveSuccess && (
                <Alert severity="success" sx={{ mt: 1 }}>{state.resolveSuccess}</Alert>
              )}
              {state.resolveError && (
                <Alert severity="error" sx={{ mt: 1 }}>{state.resolveError}</Alert>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
}
