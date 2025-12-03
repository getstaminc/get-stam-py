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
  { name: "LA LIGA", path: "/laliga", inSeason: true },
  { name: "BUNDESLIGA", path: "/bundesliga", inSeason: true },
  { name: "LIGUE 1", path: "/ligue1", inSeason: true },
  { name: "SERIE A", path: "/seriea", inSeason: true },
  { name: "NCAAB", path: "/ncaab", inSeason: true },
];