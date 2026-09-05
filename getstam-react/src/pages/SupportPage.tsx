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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  MenuItem,
  Divider,
  Link as MuiLink,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Link as RouterLink } from "react-router-dom";
import SEO from "../components/SEO";
import AuthDialog from "../components/AuthDialog";
import { useAuth } from "../contexts/AuthContext";

// Reuses the Contact Us Formspree form. Swap in a dedicated form ID here if you
// want billing tickets triaged separately from general contact.
const FORMSPREE_ENDPOINT = "https://formspree.io/f/xkgvkonz";

const TOPICS = [
  "Charged but no Pro access",
  "Cancel my subscription",
  "Refund request",
  "Free trial question",
  "Access code problem",
  "Didn't receive login code",
  "Change my account email",
  "Other",
];

const FAQS: { q: string; a: React.ReactNode }[] = [
  {
    q: "I was charged but I don't have Pro access",
    a: (
      <>
        This almost always means you're signed in with a different email than the
        one used at checkout. Log out, then log back in with the email on your
        payment receipt. If it still doesn't show Pro, send us a message below
        with that email address and we'll fix it.
      </>
    ),
  },
  {
    q: "How do I cancel my subscription?",
    a: (
      <>
        Use the <strong>Manage subscription</strong> button above to open the
        secure billing portal, then choose <em>Cancel plan</em>. Your Pro access
        stays active until the end of the current billing period.
      </>
    ),
  },
  {
    q: "How do I update my card or download an invoice?",
    a: (
      <>
        The <strong>Manage subscription</strong> button opens the billing portal
        where you can update your payment method and download every past invoice.
      </>
    ),
  },
  {
    q: "When does my free trial end and when am I billed?",
    a: (
      <>
        The trial runs for 7 days. We only charge your card when the trial ends,
        and you can cancel any time before then from the billing portal with no
        charge.
      </>
    ),
  },
  {
    q: "What's your refund policy?",
    a: (
      <>
        If you were charged unexpectedly or aren't happy, message us within 14
        days of the charge and we'll sort out a refund. Include the email used at
        checkout.
      </>
    ),
  },
  {
    q: "I have an access code",
    a: (
      <>
        Log in, open your account menu, and enter the code under{" "}
        <em>Redeem access code</em>. Codes can only be redeemed once.
      </>
    ),
  },
  {
    q: "I didn't get my login code email",
    a: (
      <>
        Check your spam folder and confirm you typed the address correctly. Codes
        expire after a few minutes, so request a fresh one if needed. Still
        nothing? Message us below.
      </>
    ),
  },
];

const SupportPage: React.FC = () => {
  const { user, isPro, openBillingPortal } = useAuth();

  const [authOpen, setAuthOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalError, setPortalError] = useState<string | null>(null);

  const [email, setEmail] = useState(user?.email ?? "");
  const [topic, setTopic] = useState(TOPICS[0]);
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const handleManageSubscription = async () => {
    if (!user) {
      setAuthOpen(true);
      return;
    }
    setPortalLoading(true);
    setPortalError(null);
    const result = await openBillingPortal();
    if (!result.success) {
      setPortalError(
        result.error === "no_stripe_customer"
          ? "We couldn't find a subscription on this account. If you paid with a different email, log in with that one."
          : "Couldn't open the billing portal. Please try again in a moment."
      );
      setPortalLoading(false);
    }
    // On success the browser is redirected to Stripe.
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(false);

    const formData = new FormData();
    formData.append("email", email);
    formData.append("topic", topic);
    formData.append("message", message);
    formData.append("_subject", `Support: ${topic}`);
    if (user) formData.append("account_id", String(user.id));

    try {
      const response = await fetch(FORMSPREE_ENDPOINT, {
        method: "POST",
        body: formData,
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        setSubmitted(true);
        setMessage("");
        setTimeout(() => setSubmitted(false), 6000);
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
    <Box sx={{ maxWidth: 640, mx: "auto", mt: 6, mb: 8, px: 2 }}>
      <SEO
        title="Support"
        description="Get help with your GetSTAM subscription, billing, and account."
        canonicalPath="/support"
      />

      <Typography variant="h4" fontWeight={800} mb={1}>
        Support
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Having trouble with your subscription or account? Most issues can be
        solved in a minute below. If not, send us a message and we'll help.
      </Typography>

      {/* Subscription self-service */}
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight={700} mb={1}>
          Manage your subscription
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={2}>
          Cancel, resume, update your card, or download invoices in the secure
          billing portal.
        </Typography>
        {portalError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {portalError}
          </Alert>
        )}
        <Button
          variant="contained"
          onClick={handleManageSubscription}
          disabled={portalLoading}
          startIcon={
            portalLoading ? <CircularProgress size={18} color="inherit" /> : null
          }
        >
          {user ? "Manage subscription" : "Log in to manage subscription"}
        </Button>
        {user && !isPro && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
            Signed in as {user.email}. If you were charged on a different email,
            log out and back in with that address.
          </Typography>
        )}
      </Paper>

      {/* FAQ */}
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight={700} mb={1.5}>
          Common questions
        </Typography>
        {FAQS.map((faq, i) => (
          <Accordion key={i} disableGutters elevation={0} sx={{ "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight={600}>{faq.q}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary">
                {faq.a}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ))}
        <Divider sx={{ my: 2 }} />
        <Typography variant="body2" color="text.secondary">
          See also our{" "}
          <MuiLink component={RouterLink} to="/terms-of-service">
            Terms of Service
          </MuiLink>{" "}
          and{" "}
          <MuiLink component={RouterLink} to="/privacy-policy">
            Privacy Policy
          </MuiLink>
          .
        </Typography>
      </Paper>

      {/* Contact fallback */}
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" fontWeight={700} mb={1}>
          Still need help?
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={2}>
          Send us the details and we'll get back to you by email, usually within
          a day.
        </Typography>
        {submitted && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Thanks — we've got your message and will be in touch soon.
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Sorry, something went wrong sending that. Please try again.
          </Alert>
        )}
        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Your Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              fullWidth
              helperText="Use the email associated with your subscription."
            />
            <TextField
              label="Topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              select
              fullWidth
            >
              {TOPICS.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="How can we help?"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              multiline
              minRows={4}
              fullWidth
              inputProps={{ maxLength: 2000 }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={!email.trim() || !message.trim() || loading}
              startIcon={
                loading ? <CircularProgress size={20} color="inherit" /> : null
              }
            >
              {loading ? "Sending..." : "Send Message"}
            </Button>
          </Stack>
        </form>
      </Paper>

      <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} />
    </Box>
  );
};

export default SupportPage;
