import React from "react";
import { Box, Chip, Typography } from "@mui/material";

export interface PlayerStreak {
  player_name: string;
  stat: "hits" | "hr" | "rbi";
  streak_count: number;
}

const STAT_LABEL: Record<string, string> = {
  hits: "1+ Hit",
  hr: "1+ HR",
  rbi: "1+ RBI",
};

const STAT_EMOJI: Record<string, string> = {
  hits: "🔥",
  hr: "⚡",
  rbi: "💪",
};

const MAX_SHOWN = 5;

interface PlayerStreaksStripProps {
  streaks: PlayerStreak[];
}

const PlayerStreaksStrip: React.FC<PlayerStreaksStripProps> = ({ streaks }) => {
  if (!streaks || streaks.length === 0) return null;

  const shown = streaks.slice(0, MAX_SHOWN);
  const extra = streaks.length - MAX_SHOWN;

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 0.75,
        alignItems: "center",
      }}
    >
      {shown.map((s, i) => {
        const emoji = STAT_EMOJI[s.stat] ?? "";
        const label = STAT_LABEL[s.stat] ?? s.stat;
        return (
          <Box
            key={i}
            sx={{
              fontSize: "0.78rem",
              color: "#334155",
              bgcolor: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: "999px",
              px: 1.25,
              py: 0.3,
              whiteSpace: "nowrap",
            }}
          >
            {emoji} <strong>{s.player_name}</strong>:{" "}
            <span style={{ color: "#64748b" }}>
              {s.streak_count} straight {label}
            </span>
          </Box>
        );
      })}
      {extra > 0 && (
        <Chip
          label={`+${extra} more`}
          size="small"
          sx={{ fontSize: "0.7rem", height: 22, bgcolor: "#e2e8f0", color: "#64748b" }}
        />
      )}
    </Box>
  );
};

export default PlayerStreaksStrip;
