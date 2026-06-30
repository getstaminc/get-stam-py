import React, { useState } from "react";
import { Box, Chip } from "@mui/material";

export interface PlayerStreak {
  player_name: string;
  stat: "hits" | "hr" | "rbi" | "hits_cover" | "hr_cover" | "rbi_cover";
  streak_count: number;
  line?: number;
}

const STAT_EMOJI: Record<string, string> = {
  hits: "🔥",
  hr: "⚡",
  rbi: "💪",
  hits_cover: "📈",
  hr_cover: "📈",
  rbi_cover: "📈",
};

function getStatLabel(stat: string, line?: number): string {
  const lineStr = line != null ? line : "?";
  if (stat === "hits_cover") return `Over ${lineStr} Hits`;
  if (stat === "hr_cover")   return `Over ${lineStr} HR`;
  if (stat === "rbi_cover")  return `Over ${lineStr} RBI`;
  if (stat === "hits") return "1+ Hit";
  if (stat === "hr")   return "1+ HR";
  if (stat === "rbi")  return "1+ RBI";
  return stat;
}

const MAX_SHOWN = 1;

interface PlayerStreaksStripProps {
  streaks: PlayerStreak[];
}

const PlayerStreaksStrip: React.FC<PlayerStreaksStripProps> = ({ streaks }) => {
  const [expanded, setExpanded] = useState(false);
  if (!streaks || streaks.length === 0) return null;

  const shown = expanded ? streaks : streaks.slice(0, MAX_SHOWN);
  const extra = streaks.length - MAX_SHOWN;

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
      {shown.map((s, i) => {
        const emoji = STAT_EMOJI[s.stat] ?? "";
        const label = getStatLabel(s.stat, s.line);
        const isCover = s.stat.endsWith("_cover");
        return (
          <Box
            key={i}
            sx={{
              fontSize: "0.78rem",
              color: "#334155",
              bgcolor: isCover ? "#f0fdf4" : "#fff",
              border: `1px solid ${isCover ? "#bbf7d0" : "#e2e8f0"}`,
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
      {!expanded && extra > 0 && (
        <Chip
          label={`+${extra} more`}
          size="small"
          onClick={() => setExpanded(true)}
          sx={{ fontSize: "0.7rem", height: 22, bgcolor: "#e2e8f0", color: "#64748b", cursor: "pointer" }}
        />
      )}
      {expanded && (
        <Chip
          label="Show less"
          size="small"
          onClick={() => setExpanded(false)}
          sx={{ fontSize: "0.7rem", height: 22, bgcolor: "#e2e8f0", color: "#64748b", cursor: "pointer" }}
        />
      )}
    </Box>
  );
};

export default PlayerStreaksStrip;
