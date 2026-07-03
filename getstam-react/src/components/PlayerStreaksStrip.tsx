import React, { useState } from "react";
import { Box, Chip, Typography } from "@mui/material";

export interface PlayerStreak {
  player_name: string;
  stat: "hits" | "hr" | "rbi" | "hits_cover" | "hr_cover" | "rbi_cover";
  streak_count: number;
  line?: number;
  continuation_rate?: number;
  sample_size?: number;
}

export interface TeamStreaks {
  team: string;
  streaks: PlayerStreak[];
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

function StreakPill({ s }: { s: PlayerStreak }) {
  const emoji = STAT_EMOJI[s.stat] ?? "";
  const label = getStatLabel(s.stat, s.line);
  const isCover = s.stat.endsWith("_cover");
  const pct = s.continuation_rate != null ? `${Math.round(s.continuation_rate * 100)}%` : null;
  const continued = s.continuation_rate != null && s.sample_size != null
    ? Math.round(s.continuation_rate * s.sample_size)
    : null;
  return (
    <Box sx={{
      fontSize: "0.78rem",
      color: "#334155",
      bgcolor: isCover ? "#f0fdf4" : "#fff",
      border: `1px solid ${isCover ? "#bbf7d0" : "#e2e8f0"}`,
      borderRadius: "999px",
      px: 1.25,
      py: 0.3,
      whiteSpace: "nowrap",
    }}>
      {emoji} <strong>{s.player_name}</strong>:{" "}
      <span style={{ color: "#64748b" }}>{s.streak_count} straight {label}</span>
      {pct && continued != null && s.sample_size != null && (
        <span style={{ color: "#94a3b8", marginLeft: 4 }}>
          · continues {pct} ({continued}/{s.sample_size})
        </span>
      )}
    </Box>
  );
}

interface PlayerStreaksStripProps {
  groups: TeamStreaks[];
  showAll?: boolean;
}

const PlayerStreaksStrip: React.FC<PlayerStreaksStripProps> = ({ groups, showAll = false }) => {
  const [expandedTeams, setExpandedTeams] = useState<Record<string, boolean>>({});

  const nonEmpty = groups.filter(g => g.streaks.length > 0);
  if (nonEmpty.length === 0) return null;

  const toggle = (team: string) =>
    setExpandedTeams(prev => ({ ...prev, [team]: !prev[team] }));

  const hasRates = nonEmpty.some(g => g.streaks.some(s => s.continuation_rate != null));

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {nonEmpty.map(({ team, streaks }) => {
        const expanded = showAll || (expandedTeams[team] ?? false);
        const shown = expanded ? streaks : streaks.slice(0, 1);
        const extra = streaks.length - 1;
        return (
          <Box key={team}>
            <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, color: "#94a3b8", mb: 0.5 }}>
              {team}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
              {shown.map((s, i) => <StreakPill key={i} s={s} />)}
              {!showAll && !expandedTeams[team] && extra > 0 && (
                <Chip
                  label={`+${extra} more`}
                  size="small"
                  onClick={() => toggle(team)}
                  sx={{ fontSize: "0.7rem", height: 22, bgcolor: "#e2e8f0", color: "#64748b", cursor: "pointer" }}
                />
              )}
              {!showAll && expandedTeams[team] && (
                <Chip
                  label="Show less"
                  size="small"
                  onClick={() => toggle(team)}
                  sx={{ fontSize: "0.7rem", height: 22, bgcolor: "#e2e8f0", color: "#64748b", cursor: "pointer" }}
                />
              )}
            </Box>
          </Box>
        );
      })}
      {hasRates && (
        <Typography sx={{ fontSize: "0.76rem", color: "#64748b", mt: 0.25 }}>
          * Continuation rate calculated from each player's own historical game records (data from 2015–present).
        </Typography>
      )}
    </Box>
  );
};

export default PlayerStreaksStrip;
