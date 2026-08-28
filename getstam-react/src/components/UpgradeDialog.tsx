import React, { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Divider from "@mui/material/Divider";
import { useAuth } from "../contexts/AuthContext";
import AuthForm from "./AuthForm";

interface UpgradeDialogProps {
  open: boolean;
  onClose: () => void;
}

const UpgradeDialog: React.FC<UpgradeDialogProps> = ({ open, onClose }) => {
  const { user, startCheckout, redeemCode } = useAuth();
  const [loadingAction, setLoadingAction] = useState<"trial" | "purchase" | "code" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCodeField, setShowCodeField] = useState(false);
  const [code, setCode] = useState("");
  const [codeRedeemed, setCodeRedeemed] = useState(false);

  const reset = () => {
    setError(null);
    setLoadingAction(null);
    setShowCodeField(false);
    setCode("");
    setCodeRedeemed(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleCheckout = async (startTrial: boolean) => {
    setError(null);
    setLoadingAction(startTrial ? "trial" : "purchase");
    const result = await startCheckout(startTrial);
    setLoadingAction(null);
    if (!result.success) {
      setError(result.error || "Something went wrong");
    }
    // On success the browser is redirected to Stripe Checkout — nothing else to do here.
  };

  const handleRedeemCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoadingAction("code");
    const result = await redeemCode(code);
    setLoadingAction(null);
    if (result.success) {
      setCodeRedeemed(true);
    } else {
      setError(result.error === "already_redeemed" ? "You've already redeemed an access code."
        : result.error === "code_fully_redeemed" ? "This code has reached its redemption limit."
        : result.error === "expired_code" ? "This code has expired."
        : "That code isn't valid.");
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      {!user ? (
        // Logged out: show the login/signup form right here instead of a second dialog.
        // Successful login just flips `user` truthy and this re-renders into the plans below —
        // successful signup shows its own "check your email" message and stays put.
        <AuthForm onClose={handleClose} onLoginSuccess={() => {}} defaultMode="signup" />
      ) : (
        <>
          <DialogTitle>Upgrade to Pro</DialogTitle>
          <DialogContent dividers>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {codeRedeemed ? (
                <Alert severity="success">You're on Pro now — enjoy!</Alert>
              ) : (
                <>
                  <Typography variant="body1">
                    <strong>$4.99/month</strong> — unlock deeper trend filters and more. Cancel anytime.
                  </Typography>

                  <Button
                    variant="contained"
                    onClick={() => handleCheckout(true)}
                    disabled={loadingAction !== null}
                  >
                    {loadingAction === "trial" ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
                    Start 7-Day Free Trial
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => handleCheckout(false)}
                    disabled={loadingAction !== null}
                  >
                    {loadingAction === "purchase" ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
                    Subscribe Now
                  </Button>

                  <Divider sx={{ my: 1 }} />

                  {!showCodeField ? (
                    <Link component="button" type="button" variant="body2" onClick={() => setShowCodeField(true)} sx={{ alignSelf: "flex-start" }}>
                      Have an access code?
                    </Link>
                  ) : (
                    <Box component="form" onSubmit={handleRedeemCode} sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                      <TextField
                        label="Access code"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        size="small"
                        fullWidth
                        autoFocus
                      />
                      <Button type="submit" variant="text" disabled={loadingAction !== null || !code.trim()} sx={{ alignSelf: "flex-start" }}>
                        {loadingAction === "code" ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
                        Redeem
                      </Button>
                    </Box>
                  )}

                  {error && <Alert severity="error">{error}</Alert>}
                </>
              )}
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, py: 2 }}>
            <Button onClick={handleClose}>{codeRedeemed ? "Close" : "Cancel"}</Button>
          </DialogActions>
        </>
      )}
    </Dialog>
  );
};

export default UpgradeDialog;
