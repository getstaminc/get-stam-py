import React from "react";
import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TabsNavigation from "./components/TabsNavigation";
import SiteFooter from "./components/SiteFooter";
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from './css/theme';
import { usePageView } from "./hooks/usePageView";
import { GameProvider } from "./contexts/GameContext";

// Import your sport and other pages
// import NBA from "./pages/NBA";
// import NFL from "./pages/NFL";
import FeatureRequestsPage from "./pages/FeatureRequestsPage";
import ContactUsPage from "./pages/ContactUsPage";
import AboutUsPage from "./pages/AboutUsPage";
import BettingGuidePage from "./pages/BettingGuidePage";
import PrivacyPolicyPage from "./pages/PrivacyPolicyPage";
import GamesPage from "./pages/GamesPage";
import GameDetailsPage from "./pages/GameDetailsPage";

// Betting 101 Pages
import Betting101Page from "./pages/betting101/Betting101Page";
import MoneylinePage from "./pages/betting101/MoneylinePage";
import SpreadsPage from "./pages/betting101/SpreadsPage";
import TotalsPage from "./pages/betting101/TotalsPage";
import ParlaysPage from "./pages/betting101/ParlaysPage";

function AppContent() {
  usePageView();
  return (
    <>
      <Box sx={{ textAlign: "center", mt: 2 }}>
        <Link
          to="/"
          style={{
            textDecoration: 'none',
            cursor: 'pointer',
            display: 'inline-block',
          }}
        >
          <Typography variant="h4" sx={{ fontWeight: 400, color: "#007bff", letterSpacing: 1 }}>
            <span style={{ fontWeight: 400, color: "#888" }}>get</span>
            <Box component="span" sx={{ fontWeight: 900, color: "#007bff", fontSize: "2.8rem", letterSpacing: 2, ml: 1 }}>
              STAM
            </Box>
          </Typography>
        </Link>
        <Typography variant="subtitle1" sx={{ color: "#007bff" }}>
          Stats That Actually Matter
        </Typography>
      </Box>
      <TabsNavigation />
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Routes>
          <Route path="/" element={<Navigate to="/nba" replace />} />
          <Route path="/nfl" element={<GamesPage />} />
          <Route path="/nfl/trends" element={<GamesPage />} />
          <Route path="/mlb" element={<GamesPage />} />
          <Route path="/mlb/trends" element={<GamesPage />} />
          <Route path="/nba" element={<GamesPage />} />
          <Route path="/nba/trends" element={<GamesPage />} />
          <Route path="/nhl" element={<GamesPage />} />
          <Route path="/nhl/trends" element={<GamesPage />} />
          <Route path="/ncaaf" element={<GamesPage />} />
          <Route path="/ncaaf/trends" element={<GamesPage />} />
          <Route path="/ncaab" element={<GamesPage />} />
          <Route path="/ncaab/trends" element={<GamesPage />} />
          <Route path="/laliga" element={<GamesPage />} />
          <Route path="/laliga/trends" element={<GamesPage />} />
          <Route path="/bundesliga" element={<GamesPage />} />
          <Route path="/bundesliga/trends" element={<GamesPage />} />
          <Route path="/ligue1" element={<GamesPage />} />
          <Route path="/ligue1/trends" element={<GamesPage />} />
          <Route path="/seriea" element={<GamesPage />} />
          <Route path="/seriea/trends" element={<GamesPage />} />
          <Route path="/epl" element={<GamesPage />} />
          <Route path="/epl/trends" element={<GamesPage />} />
          <Route path="/game-details/:sport" element={<GameDetailsPage />} />
          <Route path="/about-us" element={<AboutUsPage />} />
          <Route path="/feature-requests" element={<FeatureRequestsPage />} />
          <Route path="/contact-us" element={<ContactUsPage />} />
          <Route path="/betting-guide" element={<BettingGuidePage />} />
          <Route path="/betting101" element={<Betting101Page />} />
          <Route path="/betting101/moneyline" element={<MoneylinePage />} />
          <Route path="/betting101/spreads" element={<SpreadsPage />} />
          <Route path="/betting101/totals" element={<TotalsPage />} />
          <Route path="/betting101/parlays" element={<ParlaysPage />} />
          <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </Box>
  <SiteFooter />
    </>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <GameProvider>
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Router>
            <AppContent />
          </Router>
        </Box>
      </GameProvider>
    </ThemeProvider>
  );
}

export default App;