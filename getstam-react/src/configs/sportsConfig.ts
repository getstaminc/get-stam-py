export interface Sport {
  name: string;
  path?: string;
  inSeason: boolean;
  // Set to false to hide a sport from nav/homepage without deleting its code (e.g. World Cup between tournaments)
  enabled?: boolean;
  // Optional child leagues for grouped sports (e.g., Soccer)
  leagues?: { name: string; path: string }[];
}

const allSports: Sport[] = [
  { name: "MLB", path: "/mlb", inSeason: true },
  { name: "NBA", path: "/nba", inSeason: false },
  { name: "NCAAB", path: "/ncaab", inSeason: false },
  { name: "NHL", path: "/nhl", inSeason: false },
  { name: "NFL", path: "/nfl", inSeason: false },
  { name: "NCAAF", path: "/ncaaf", inSeason: false },
  // Next World Cup is 2030 — flip `enabled` to true to bring it back
  { name: "WORLD CUP", path: "/worldcup", inSeason: true, enabled: false },
  // Group soccer leagues under a single Soccer nav item to reduce clutter
  {
    name: "SOCCER",
    inSeason: true,
    leagues: [
      { name: "EPL", path: "/epl" },
      { name: "LA LIGA", path: "/laliga" },
      { name: "BUNDESLIGA", path: "/bundesliga" },
      { name: "LIGUE 1", path: "/ligue1" },
      { name: "SERIE A", path: "/seriea" },
    ],
  },
];

export const sports: Sport[] = allSports.filter((s) => s.enabled !== false);

