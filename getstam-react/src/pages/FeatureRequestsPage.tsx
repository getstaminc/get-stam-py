import React, { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Stack,
} from "@mui/material";

const FeatureRequestsPage: React.FC = () => {
  const [submitted, setSubmitted] = useState(false);

  // Reset form after submit
  const handleSubmit = () => {
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 5000);
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
            Thank you for your suggestion!
          </Alert>
        )}
        <form
          action="https://formspree.io/f/xpwrnrjp"
          method="POST"
          onSubmit={handleSubmit}
        >
          <Stack spacing={2}>
            <TextField
              label="Feature Request"
              name="feature"
              required
              multiline
              minRows={3}
              fullWidth
              inputProps={{ maxLength: 500 }} 
            />
            <TextField
              label="Your Email (optional)"
              name="email"
              type="email"
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
            >
              Submit
            </Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
};

export default FeatureRequestsPage;