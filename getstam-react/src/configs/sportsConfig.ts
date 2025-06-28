export interface Sport {
  name: string;
  path: string;
  inSeason: boolean;
}

export const sports: Sport[] = [
  { name: "MLB", path: "/mlb", inSeason: true },
  { name: "NBA", path: "/nba", inSeason: true },
  { name: "NHL", path: "/nhl", inSeason: true },
  { name: "NFL", path: "/nfl", inSeason: false },
  { name: "NCAAF", path: "/ncaaf", inSeason: false },
  { name: "EPL", path: "/epl", inSeason: false },
];