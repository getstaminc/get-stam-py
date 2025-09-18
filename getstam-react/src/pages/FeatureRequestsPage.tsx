import React, { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Stack,
  CircularProgress,
} from "@mui/material";

const FeatureRequestsPage: React.FC = () => {
  const [feature, setFeature] = useState("");
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(false);

    const formData = new FormData();
    formData.append('feature', feature);
    formData.append('email', email);

    try {
      const response = await fetch('https://formspree.io/f/xpwrnrjp', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        },
      });

      if (response.ok) {
        setSubmitted(true);
        setFeature("");
        setEmail("");
        // Hide success message after 5 seconds
        setTimeout(() => setSubmitted(false), 5000);
      } else {
        setError(true);
      }
    } catch (err) {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 500, mx: "auto", mt: 6, mb: 6 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h5" fontWeight={700} mb={2}>
          Feature Requests
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          Have an idea to make getSTAM better? Let us know what features you'd like to see!
        </Typography>
        {submitted && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Thank you for your suggestion! We appreciate your feedback.
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Sorry, there was an error submitting your request. Please try again.
          </Alert>
        )}
        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Feature Request"
              value={feature}
              onChange={(e) => setFeature(e.target.value)}
              required
              multiline
              minRows={3}
              fullWidth
              inputProps={{ maxLength: 500 }} 
            />
            <TextField
              label="Your Email (optional)"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={!feature.trim() || loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {loading ? 'Submitting...' : 'Submit'}
            </Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
};

export default FeatureRequestsPage;