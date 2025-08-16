import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
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
import BettingGuidePage from "./pages/BettingGuidePage";
import GamesPage from "./pages/GamesPage";
import GameDetailsPage from "./pages/GameDetailsPage";

function AppContent() {
  usePageView();
  return (
    <>
      <Box sx={{ textAlign: "center", mt: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 400, color: "#007bff", letterSpacing: 1 }}>
          <span style={{ fontWeight: 400, color: "#888" }}>get</span>
          <Box component="span" sx={{ fontWeight: 900, color: "#007bff", fontSize: "2.8rem", letterSpacing: 2, ml: 1 }}>
            STAM
          </Box>
        </Typography>
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
          <Route path="/feature-requests" element={<FeatureRequestsPage />} />
          <Route path="/contact-us" element={<ContactUsPage />} />
          <Route path="/betting-guide" element={<BettingGuidePage />} />
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