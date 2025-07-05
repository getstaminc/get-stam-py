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

const ContactUsPage: React.FC = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Replace with your API call or email integration
    setSubmitted(true);
    setName("");
    setEmail("");
    setMessage("");
  };

  return (
    <Box sx={{ maxWidth: 500, mx: "auto", mt: 6, mb: 6 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h5" fontWeight={700} mb={2}>
          Contact Us
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          Have a question, comment, or need support? Fill out the form below and we'll get back to you!
        </Typography>
        {submitted && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Thank you for reaching out! We'll be in touch soon.
          </Alert>
        )}
        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Your Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Your Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              fullWidth
            />
            <TextField
              label="Message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              multiline
              minRows={4}
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={!name.trim() || !email.trim() || !message.trim()}
            >
              Send Message
            </Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
};

export default ContactUsPage;