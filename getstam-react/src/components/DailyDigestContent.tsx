import React from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { Link } from "react-router-dom";

export interface TrendItem {
  description: string;
}

export interface TeamSection {
  label: string;
  trends: TrendItem[];
}

export interface GameCard {
  matchup: string;
  gameUrl?: string;
  teams: TeamSection[];
}

export interface SportSection {
  name: string;
  games: GameCard[];
}

export interface PlayerStreakItem {
  text: string;
}

export function parseDailyDigest(markdown: string): { intro: string; sports: SportSection[]; playerStreaks: PlayerStreakItem[] } {
  const lines = markdown.split("\n");
  let intro = "";
  const sports: SportSection[] = [];
  const playerStreaks: PlayerStreakItem[] = [];
  let currentSport: SportSection | null = null;
  let currentGame: GameCard | null = null;
  let currentTeam: TeamSection | null = null;
  let inPlayerStreaks = false;

  const flushTeam = () => {
    if (currentTeam && currentGame) { currentGame.teams.push(currentTeam); currentTeam = null; }
  };
  const flushGame = () => {
    flushTeam();
    if (currentGame && currentSport) { currentSport.games.push(currentGame); currentGame = null; }
  };
  const flushSport = () => {
    flushGame();
    if (currentSport) { sports.push(currentSport); currentSport = null; }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("# ")) continue;
    if (line.startsWith("### Player Streaks")) {
      flushGame();
      inPlayerStreaks = true;
      continue;
    }
    if (inPlayerStreaks) {
      if (line.startsWith("•")) {
        playerStreaks.push({ text: line.slice(1).trim() });
      } else if (line.startsWith("## ")) {
        // new sport section resets player streaks mode
        inPlayerStreaks = false;
        flushSport();
        currentSport = { name: line.slice(3).trim(), games: [] };
      }
      continue;
    }
    if (line.startsWith("## ")) {
      flushSport();
      currentSport = { name: line.slice(3).trim(), games: [] };
    } else if (line.startsWith("### ")) {
      flushGame();
      currentGame = { matchup: line.slice(4).trim(), teams: [] };
    } else if (/^\[.*\]\(\/game-details\/[^)]+\)$/.test(line) && currentGame) {
      const urlMatch = line.match(/\]\(([^)]+)\)/);
      if (urlMatch) currentGame.gameUrl = urlMatch[1];
    } else if (/^\*\*[^*]+\*\*:/.test(line)) {
      flushTeam();
      const label = line.match(/^\*\*([^*]+)\*\*:/)?.[1] || "";
      currentTeam = { label, trends: [] };
    } else if (line.startsWith("- ") && currentTeam) {
      currentTeam.trends.push({ description: line.slice(2).trim() });
    } else if (!currentSport && line.trim() && !line.startsWith("#")) {
      intro = intro ? intro + " " + line.trim() : line.trim();
    }
  }
  flushSport();
  return { intro, sports, playerStreaks };
}

export const SPORT_COLORS: Record<string, { bg: string; text: string; light: string }> = {
  MLB: { bg: "#1565c0", text: "#fff", light: "#e3f2fd" },
  NHL: { bg: "#00695c", text: "#fff", light: "#e0f2f1" },
  NBA: { bg: "#bf360c", text: "#fff", light: "#fbe9e7" },
};

function getTrendStyle(description: string) {
  const d = description.toLowerCase();
  if (d.includes("won") || d.includes("win")) return { bg: "#e8f5e9", color: "#2e7d32", border: "#a5d6a7", icon: <TrendingUpIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("lost") || d.includes("loss")) return { bg: "#ffebee", color: "#c62828", border: "#ef9a9a", icon: <TrendingDownIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("over")) return { bg: "#e8f5e9", color: "#2e7d32", border: "#a5d6a7", icon: <TrendingUpIcon sx={{ fontSize: 14 }} /> };
  if (d.includes("under")) return { bg: "#ffebee", color: "#c62828", border: "#ef9a9a", icon: <TrendingDownIcon sx={{ fontSize: 14 }} /> };
  return { bg: "#f5f5f5", color: "#424242", border: "#e0e0e0", icon: undefined };
}

export function TrendPill({ trend }: { trend: TrendItem }) {
  // Descriptions are now "{streak} — {historical context} — {team role}"
  // Split on first " — " only so the pill shows just the streak, context below
  const sepIdx = trend.description.indexOf(" — ");
  const main = sepIdx >= 0 ? trend.description.slice(0, sepIdx) : trend.description;
  const context = sepIdx >= 0 ? trend.description.slice(sepIdx + 3) : "";
  const style = getTrendStyle(main);

  return (
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.5,
          px: 1.5,
          py: 0.5,
          borderRadius: 4,
          fontSize: "0.78rem",
          fontWeight: 600,
          bgcolor: style.bg,
          color: style.color,
          border: `1px solid ${style.border}`,
          lineHeight: 1.4,
          mb: context ? 0.5 : 0,
        }}
      >
        {style.icon}
        {main}
      </Box>
      {context && (
        <Typography
          variant="caption"
          sx={{ display: "block", color: "text.secondary", fontSize: "0.72rem", pl: 0.5, lineHeight: 1.5 }}
        >
          {context}
        </Typography>
      )}
    </Box>
  );
}

export default function DailyDigestContent({ content }: { content: string }) {
  const { intro, sports, playerStreaks } = parseDailyDigest(content);

  return (
    <Box>
      {intro && (
        <Typography variant="body1" sx={{ mb: 3, color: "text.secondary", fontSize: "1.05rem" }}>
          {intro}
        </Typography>
      )}

      {playerStreaks.length > 0 && (
        <Box sx={{ mb: 3, p: 2, bgcolor: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "10px" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, color: "#15803d", mb: 1.5, letterSpacing: 0.5 }}>
            MLB Player Streaks
          </Typography>
          <Stack spacing={0.75}>
            {playerStreaks.map((item, i) => (
              <Box
                key={i}
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.5,
                  px: 1.5,
                  py: 0.5,
                  borderRadius: 4,
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  bgcolor: "#dcfce7",
                  color: "#15803d",
                  border: "1px solid #a5d6a7",
                  width: "fit-content",
                }}
              >
                {item.text}
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      <Stack spacing={3}>
        {sports.map((sport) => {
          const colors = SPORT_COLORS[sport.name] || { bg: "#37474f", text: "#fff", light: "#eceff1" };
          return (
            <Box key={sport.name}>
              {/* Sport header */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  px: 2.5,
                  py: 1.5,
                  bgcolor: colors.bg,
                  borderRadius: "10px 10px 0 0",
                }}
              >
                <Typography variant="h6" sx={{ color: colors.text, fontWeight: 800, letterSpacing: 1 }}>
                  {sport.name}
                </Typography>
                <Chip
                  label={`${sport.games.length} game${sport.games.length !== 1 ? "s" : ""}`}
                  size="small"
                  sx={{ bgcolor: "rgba(255,255,255,0.2)", color: colors.text, fontWeight: 600, fontSize: "0.72rem" }}
                />
              </Box>

              {/* Games */}
              <Box
                sx={{
                  border: `2px solid ${colors.bg}`,
                  borderTop: "none",
                  borderRadius: "0 0 10px 10px",
                  overflow: "hidden",
                }}
              >
                {sport.games.map((game, gi) => (
                  <Box
                    key={gi}
                    sx={{
                      p: 2.5,
                      borderTop: gi > 0 ? "1px solid #f0f0f0" : "none",
                      bgcolor: gi % 2 === 0 ? "#fff" : "#fafafa",
                    }}
                  >
                    {/* Matchup header */}
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1.5 }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ width: 4, height: 20, bgcolor: colors.bg, borderRadius: 1 }} />
                        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#1a1a1a" }}>
                          {game.matchup}
                        </Typography>
                      </Box>
                      {game.gameUrl && (
                        <Button
                          component={Link}
                          to={game.gameUrl}
                          size="small"
                          variant="outlined"
                          sx={{
                            fontSize: "0.7rem",
                            py: 0.25,
                            px: 1,
                            borderRadius: 2,
                            whiteSpace: "nowrap",
                            borderColor: colors.bg,
                            color: colors.bg,
                            "&:hover": { bgcolor: colors.light },
                          }}
                        >
                          View Game →
                        </Button>
                      )}
                    </Box>

                    {/* Team trends */}
                    <Stack spacing={1.5}>
                      {game.teams.map((team, ti) => (
                        <Box key={ti}>
                          <Typography
                            variant="caption"
                            sx={{
                              display: "block",
                              fontWeight: 700,
                              color: colors.bg,
                              textTransform: "uppercase",
                              letterSpacing: 0.5,
                              mb: 0.75,
                              fontSize: "0.7rem",
                            }}
                          >
                            {team.label}
                          </Typography>
                          <Stack spacing={1}>
                            {team.trends.map((t, trendIdx) => (
                              <TrendPill key={trendIdx} trend={t} />
                            ))}
                          </Stack>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                ))}
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
