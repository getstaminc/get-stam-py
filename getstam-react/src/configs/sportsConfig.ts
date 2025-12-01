export interface Sport {
  name: string;
  path: string;
  inSeason: boolean;
}

export const sports: Sport[] = [
  { name: "MLB", path: "/mlb", inSeason: false },
  { name: "NBA", path: "/nba", inSeason: true },
  { name: "NHL", path: "/nhl", inSeason: true },
  { name: "NFL", path: "/nfl", inSeason: true },
  { name: "NCAAF", path: "/ncaaf", inSeason: true },
  { name: "EPL", path: "/epl", inSeason: true },
  { name: "NCAAB", path: "/ncaab", inSeason: true },
];