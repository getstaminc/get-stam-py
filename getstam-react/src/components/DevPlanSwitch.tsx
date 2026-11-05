import React from "react";
import { Box, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { useAuth, DevPlanOverride } from "../contexts/AuthContext";

/** Floating free/Pro preview switch. Renders only when the backend has FLASK_ENV=development. */
const DevPlanSwitch: React.FC = () => {
  const { devTools, devPlan, setDevPlan } = useAuth();
  if (!devTools) return null;
  return (
    <Box sx={{
      position: "fixed", left: 12, bottom: 12, zIndex: 2000,
      display: "flex", alignItems: "center", gap: 1,
      px: 1, py: 0.5, borderRadius: "999px",
      bgcolor: "#14171c", boxShadow: "0 4px 14px rgba(0,0,0,.25)",
    }}>
      <Typography sx={{ fontSize: "0.65rem", fontWeight: 800, letterSpacing: "0.08em", color: "#fbbf24", pl: 0.5 }}>DEV</Typography>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={devPlan}
        onChange={(_, v: DevPlanOverride | null) => v && setDevPlan(v)}
        aria-label="Preview plan"
        sx={{
          "& .MuiToggleButton-root": {
            color: "#cbd5e1", border: "none", px: 1.25, py: 0.25,
            fontSize: "0.7rem", fontWeight: 700, textTransform: "none", borderRadius: "999px !important",
          },
          "& .Mui-selected": { bgcolor: "#ffffff !important", color: "#14171c !important" },
        }}
      >
        <ToggleButton value="real">Real</ToggleButton>
        <ToggleButton value="free">Free</ToggleButton>
        <ToggleButton value="pro">Pro</ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
};

export default DevPlanSwitch;
