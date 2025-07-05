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

// Import your sport and other pages
// import NBA from "./pages/NBA";
// import NFL from "./pages/NFL";
import FeatureRequestsPage from "./pages/FeatureRequestsPage";
import ContactUsPage from "./pages/ContactUsPage";
import BettingGuidePage from "./pages/BettingGuidePage";

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
          {/* <Route path="/nba" element={<NBA />} />
          <Route path="/nfl" element={<NFL />} /> */}
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
    </ThemeProvider>
  );
}

export default App;