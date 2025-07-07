export interface Sport {
  name: string;
  path: string;
  inSeason: boolean;
}

export const sports: Sport[] = [
  { name: "MLB", path: "/mlb", inSeason: true },
  { name: "NBA", path: "/nba", inSeason: false },
  { name: "NHL", path: "/nhl", inSeason: false },
  { name: "NFL", path: "/nfl", inSeason: true },
  { name: "NCAAF", path: "/ncaaf", inSeason: false },
  { name: "EPL", path: "/epl", inSeason: true },
];