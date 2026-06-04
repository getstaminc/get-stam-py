import React, { useState } from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:5000"
    : "https://www.getstam.com");

interface Props {
  compact?: boolean;
}

export default function EmailSubscribeForm({ compact = false }: Props) {
  const [email, setEmail] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/subscribers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (res.status === 409) {
        setError("You're already subscribed!");
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || "Something went wrong. Please try again.");
        return;
      }
      setSubmittedEmail(email.trim());
      setSuccess(true);
      setEmail("");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isGmail = submittedEmail.toLowerCase().endsWith("@gmail.com");

  if (success) {
    return (
      <Alert severity="success" sx={{ mt: compact ? 0 : 1 }}>
        You're subscribed! Check your inbox tomorrow morning.
        {isGmail && (
          <Box sx={{ mt: 1, fontSize: "0.85em", lineHeight: 1.5 }}>
            <strong>Gmail tip:</strong> Your first email may land in Promotions.
            Drag it to Primary and click <em>"Do this for future messages?"</em> → <strong>Yes</strong> so you never miss it.
          </Box>
        )}
      </Alert>
    );
  }

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        display: "flex",
        flexDirection: compact ? "row" : "column",
        gap: 1,
        alignItems: compact ? "center" : "stretch",
      }}
    >
      <TextField
        size="small"
        type="email"
        placeholder="your@email.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        disabled={loading}
        sx={{
          flex: compact ? 1 : undefined,
          bgcolor: "white",
          borderRadius: 1,
          "& .MuiOutlinedInput-root": {
            "& fieldset": { borderColor: compact ? "rgba(255,255,255,0.5)" : undefined },
            "&:hover fieldset": { borderColor: compact ? "white" : undefined },
          },
          input: { color: compact ? "#000" : undefined },
        }}
      />
      <Button
        type="submit"
        variant="contained"
        disabled={loading}
        sx={{
          whiteSpace: "nowrap",
          bgcolor: compact ? "white" : undefined,
          color: compact ? "#1976d2" : undefined,
          "&:hover": { bgcolor: compact ? "#e3f2fd" : undefined },
          fontWeight: 700,
          px: 3,
        }}
      >
        {loading ? <CircularProgress size={20} color="inherit" /> : "Subscribe"}
      </Button>
      {error && (
        <Alert
          severity={error.includes("already subscribed") ? "info" : "error"}
          sx={{ mt: 0.5, width: "100%" }}
        >
          {error}
        </Alert>
      )}
    </Box>
  );
}
