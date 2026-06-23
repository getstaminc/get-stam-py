export interface Sport {
  name: string;
  path?: string;
  inSeason: boolean;
  // Optional child leagues for grouped sports (e.g., Soccer)
  leagues?: { name: string; path: string }[];
}

export const sports: Sport[] = [
  { name: "MLB", path: "/mlb", inSeason: true },
  { name: "NBA", path: "/nba", inSeason: false },
  { name: "NCAAB", path: "/ncaab", inSeason: false },
  { name: "NHL", path: "/nhl", inSeason: false },
  { name: "NFL", path: "/nfl", inSeason: false },
  { name: "NCAAF", path: "/ncaaf", inSeason: false },
  { name: "WORLD CUP", path: "/worldcup", inSeason: true },
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

