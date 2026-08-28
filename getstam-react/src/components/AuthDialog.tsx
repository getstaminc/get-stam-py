import React from "react";
import Dialog from "@mui/material/Dialog";
import AuthForm from "./AuthForm";

interface AuthDialogProps {
  open: boolean;
  onClose: () => void;
}

const AuthDialog: React.FC<AuthDialogProps> = ({ open, onClose }) => (
  <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
    <AuthForm onClose={onClose} />
  </Dialog>
);

export default AuthDialog;
