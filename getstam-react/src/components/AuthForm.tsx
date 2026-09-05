import React, { useState } from "react";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import CheckIcon from "@mui/icons-material/Check";
import { useAuth, SignupIntent } from "../contexts/AuthContext";

type Mode = "login" | "signup";
type Step = "plan" | "nudge" | "email" | "code";

const FREE_FEATURES = ["Trend filters up to 5+ games", "Full scores & odds", "Access to all sports"];
const PRO_FEATURES = ["Everything in Free", "Extended trend filters (7+, 10+ games)"];
const PRO_COMING_SOON = ["AI GetSTAM Analysis for games"];

interface AuthFormProps {
  /** Called when the user cancels/closes, and by default after a successful code verification too. */
  onClose: () => void;
  /** Overrides what happens after a successful code verification. Pass a no-op when this form is
   * embedded inside another dialog (e.g. UpgradeDialog) that should stay open and just switch
   * views once `user` becomes truthy, rather than closing. Defaults to onClose (plain standalone). */
  onLoginSuccess?: () => void;
  /** Which screen to open on. Defaults to "login" (the plain "Log In" nav entry point) — starts
   * directly at the email step. UpgradeDialog passes "signup" so a locked-feature click lands on
   * "Choose Your Plan" first — an existing user can still get to login from there. */
  defaultMode?: Mode;
}

const FeatureList: React.FC<{ features: string[]; comingSoon?: string[] }> = ({ features, comingSoon }) => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, my: 1.5 }}>
    {features.map((f) => (
      <Box key={f} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <CheckIcon fontSize="small" color="success" />
        <Typography variant="body2">{f}</Typography>
      </Box>
    ))}
    {comingSoon?.map((f) => (
      <Box key={f} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <CheckIcon fontSize="small" color="disabled" />
        <Typography variant="body2" color="text.secondary">{f}</Typography>
        <Chip label="Coming Soon" size="small" variant="outlined" />
      </Box>
    ))}
  </Box>
);

/** The passwordless login/signup form, as the DialogTitle+DialogContent+DialogActions of
 * whatever Dialog renders it — reused by AuthDialog (the plain "Log In" entry point) and
 * UpgradeDialog (which shows this inline instead of popping a second dialog when logged out).
 * Signup is a short flow: pick a plan, optionally get nudged toward a Pro trial if Free was
 * picked, then email -> emailed 6-digit code. Entering the code is the only verification step —
 * there's no separate email-link flow, since receiving the code already proves inbox ownership. */
const AuthForm: React.FC<AuthFormProps> = ({ onClose, onLoginSuccess, defaultMode = "login" }) => {
  const { requestCode, verifyCode } = useAuth();
  const [mode, setMode] = useState<Mode>(defaultMode);
  const [step, setStep] = useState<Step>(defaultMode === "signup" ? "plan" : "email");
  const [intent, setIntent] = useState<SignupIntent>(null);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeSent, setCodeSent] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setCodeSent(false);
    setAgreedToTerms(false);
    if (next === "signup") {
      setStep("plan");
      setIntent(null);
    } else {
      setStep("email");
    }
  };

  const choosePro = () => {
    setIntent("trial");
    setStep("email");
  };
  const chooseFree = () => setStep("nudge");
  const acceptTrialNudge = () => {
    setIntent("trial");
    setStep("email");
  };
  const declineTrialNudge = () => {
    setIntent(null);
    setStep("email");
  };
  const backToPlan = () => {
    setStep("plan");
    setError(null);
  };
  const backToEmail = () => {
    setStep("email");
    setCode("");
    setError(null);
    setCodeSent(false);
  };

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "signup" && !agreedToTerms) return;
    setError(null);
    setLoading(true);
    const result = await requestCode(email, intent, mode === "login");
    setLoading(false);
    if (result.success) {
      setCodeSent(true);
      setStep("code");
    } else if (result.error === "account_not_found") {
      setError("account_not_found");
    } else {
      setError(result.error || "Something went wrong");
    }
  };

  const handleResend = async () => {
    setError(null);
    setLoading(true);
    const result = await requestCode(email, intent, mode === "login");
    setLoading(false);
    if (!result.success) {
      setError(result.error || "Something went wrong");
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const result = await verifyCode(email, code);
    setLoading(false);
    if (result.success) {
      if (!result.redirectingToCheckout) {
        (onLoginSuccess || onClose)();
      }
    } else {
      setError(result.error === "expired_code" ? "That code has expired — request a new one."
        : result.error === "too_many_attempts" ? "Too many attempts — request a new code."
        : "That code isn't valid.");
    }
  };

  // Signup starts with a plan-picker step before asking for an email at all.
  if (mode === "signup" && step === "plan") {
    return (
      <>
        <DialogTitle>Choose Your Plan</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Box sx={{ border: "2px solid", borderColor: "primary.main", borderRadius: 1, p: 2 }}>
              <Typography variant="subtitle1" fontWeight={700}>Pro</Typography>
              <Typography variant="body2" color="text.secondary">$4.99/month · 7-day free trial</Typography>
              <FeatureList features={PRO_FEATURES} comingSoon={PRO_COMING_SOON} />
              <Button fullWidth variant="contained" onClick={choosePro}>Continue with Pro</Button>
            </Box>
            <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }}>
              <Typography variant="subtitle1" fontWeight={700}>Free</Typography>
              <Typography variant="body2" color="text.secondary">$0</Typography>
              <FeatureList features={FREE_FEATURES} />
              <Button fullWidth variant="outlined" onClick={chooseFree}>Continue with Free</Button>
            </Box>
            <Link component="button" type="button" variant="body2" onClick={() => switchMode("login")} sx={{ alignSelf: "flex-start" }}>
              Already have an account? Log in
            </Link>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={onClose}>Cancel</Button>
        </DialogActions>
      </>
    );
  }

  if (mode === "signup" && step === "nudge") {
    return (
      <>
        <DialogTitle>Try Pro Free for 7 Days?</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="body1">
              Free works great, but you can try everything in Pro — extended trend filters and more — free for 7 days. No charge until the trial ends, cancel anytime.
            </Typography>
            <Button variant="contained" onClick={acceptTrialNudge}>Try Pro Free for 7 Days</Button>
            <Button variant="outlined" onClick={declineTrialNudge}>No Thanks, Continue with Free</Button>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={backToPlan}>Back</Button>
        </DialogActions>
      </>
    );
  }

  if (step === "code") {
    return (
      <>
        <DialogTitle>Enter Your Code</DialogTitle>
        <Box component="form" onSubmit={handleVerifyCode}>
          <DialogContent dividers>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {codeSent && (
                <Alert severity="success">
                  We sent a 6-digit code to {email}. It expires in 10 minutes.
                  {intent === "trial" ? " Verifying will take you straight to checkout to start your trial." : ""}
                </Alert>
              )}
              <TextField
                label="6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
                autoFocus
                required
                fullWidth
              />
              <Link component="button" type="button" variant="body2" onClick={handleResend} disabled={loading} sx={{ alignSelf: "flex-start" }}>
                Resend code
              </Link>
              <Link component="button" type="button" variant="body2" onClick={backToEmail} sx={{ alignSelf: "flex-start" }}>
                Use a different email
              </Link>
              {error && <Alert severity="error">{error}</Alert>}
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={loading || code.length !== 6}>
              {loading ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
              Verify
            </Button>
          </DialogActions>
        </Box>
      </>
    );
  }

  // step === "email"
  return (
    <>
      <DialogTitle>{mode === "signup" ? (intent === "trial" ? "Start Your Pro Trial" : "Create an Account") : "Log In"}</DialogTitle>
      <Box component="form" onSubmit={handleSendCode}>
        <DialogContent dividers>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              We'll email you a 6-digit code — no password needed.
            </Typography>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              required
              fullWidth
            />
            {mode === "signup" && (
              <Link component="button" type="button" variant="body2" onClick={backToPlan} sx={{ alignSelf: "flex-start" }}>
                ← Back to plans
              </Link>
            )}
            <Link component="button" type="button" variant="body2" onClick={() => switchMode(mode === "signup" ? "login" : "signup")} sx={{ alignSelf: "flex-start" }}>
              {mode === "signup" ? "Already have an account? Log in" : "Need an account? Sign up"}
            </Link>
            {mode === "signup" && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                  />
                }
                label={
                  <Typography variant="body2" color="text.secondary">
                    I agree to the{" "}
                    <Link href="/terms-of-service" target="_blank" rel="noopener noreferrer">
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link href="/privacy-policy" target="_blank" rel="noopener noreferrer">
                      Privacy Policy
                    </Link>
                    .
                  </Typography>
                }
              />
            )}
            {error === "account_not_found" ? (
              <Alert severity="warning">
                No account found for that email.{" "}
                <Link component="button" type="button" onClick={() => switchMode("signup")}>Sign up instead?</Link>
              </Alert>
            ) : error ? (
              <Alert severity="error">{error}</Alert>
            ) : null}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading || (mode === "signup" && !agreedToTerms)}>
            {loading ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
            Send Code
          </Button>
        </DialogActions>
      </Box>
    </>
  );
};

export default AuthForm;
