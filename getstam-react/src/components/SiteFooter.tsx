import React from "react";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import InstagramIcon from "@mui/icons-material/Instagram";
import FacebookIcon from "@mui/icons-material/Facebook";
import MusicNoteIcon from "@mui/icons-material/MusicNote"; // TikTok substitute
import { Link as RouterLink } from "react-router-dom";


const SiteFooter: React.FC = () => (
  <Box
    component="footer"
    sx={{
      mt: 6,
      py: 3,
      px: 2,
      bgcolor: "#f7f7f7",
      borderTop: "1px solid #eee",
      textAlign: "center",
    }}
  >
    <Box sx={{ mb: 1 }}>
      <Link
        href="/contact-us"
        underline="none"
        color="inherit"
        sx={{
          mx: 1,
          transition: "color 0.2s",
          "&:hover": {
            color: "#007bff",
            textDecoration: "none",
          },
        }}
      >
        Contact Us
      </Link>
      <Link
        href="/betting-guide"
        underline="none"
        color="inherit"
        sx={{
            mx: 1,
            transition: "color 0.2s",
            "&:hover": {
            color: "#007bff",
            textDecoration: "none",
            },
        }}
        >
          Betting Guide
        </Link>
        <Link
          href="/privacy-policy"
          underline="none"
          color="inherit"
          sx={{
            mx: 1,
            transition: "color 0.2s",
            "&:hover": {
              color: "#007bff",
              textDecoration: "none",
            },
          }}
        >
          Privacy Policy
        </Link>
    </Box>
    <Box sx={{ mb: 1 }}>
      <Link href="https://instagram.com/yourhandle" target="_blank" rel="noopener" color="inherit" sx={{ mx: 0.5 }}>
        <InstagramIcon fontSize="medium" />
      </Link>
      <Link href="https://facebook.com/yourhandle" target="_blank" rel="noopener" color="inherit" sx={{ mx: 0.5 }}>
        <FacebookIcon fontSize="medium" />
      </Link>
      <Link href="https://tiktok.com/@yourhandle" target="_blank" rel="noopener" color="inherit" sx={{ mx: 0.5 }}>
        <MusicNoteIcon fontSize="medium" />
      </Link>
    </Box>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ display: "block", maxWidth: 600, mx: "auto", fontSize: "0.85rem" }}
    >
      © 2025 GetStam.com. All odds and betting information are for entertainment purposes only.
      We do not offer real-money gambling or betting services.{" "}
      <strong>Gamble responsibly</strong>. Must be 18+ (or 21+ in some jurisdictions).
      If you or someone you know has a gambling problem, visit{" "}
      <Link
        href="https://www.ncpgambling.org"
        target="_blank"
        rel="noopener"
        color="inherit"
        underline="always"
      >
        NCPGambling.org
      </Link>{" "}
      or call 1-800-GAMBLER.
    </Typography>
  </Box>
);

export default SiteFooter;