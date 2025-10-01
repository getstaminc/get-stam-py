import React from "react";
import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
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
          <Route path="/" element={<GamesPage />} />
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
          <Route path="/epl" element={<GamesPage />} />
          <Route path="/epl/trends" element={<GamesPage />} />
          <Route path="/game-details/:sport" element={<GameDetailsPage />} />
          <Route path="/about-us" element={<AboutUsPage />} />
          <Route path="/feature-requests" element={<FeatureRequestsPage />} />
          <Route path="/contact-us" element={<ContactUsPage />} />
          <Route path="/betting-guide" element={<BettingGuidePage />} />
          <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </Box>
      {/* Adsterra NativeBanner above SiteFooter */}
      <div id="container-84c8772b3011daf3282d61f7f820fbc4"></div>
  <SiteFooter />
    </>
  );
}

function App() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = '//pl27749833.revenuecpmgate.com/84c8772b3011daf3282d61f7f820fbc4/invoke.js';
    script.async = true;
    script.setAttribute('data-cfasync', 'false');
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);
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
          {/* Adsterra NativeBanner at bottom of all pages */}
          <div id="container-84c8772b3011daf3282d61f7f820fbc4" style={{ margin: '24px auto', minHeight: 120 }}></div>
        </Box>
      </GameProvider>
    </ThemeProvider>
  );
}

export default App;