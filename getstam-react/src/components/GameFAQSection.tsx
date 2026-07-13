import React from "react";
import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { getTeamPageLink, MATCHUP_SLUG_SPORTS } from "../utils/teamSlugUtils";
import { convertTeamNameBySport } from "../utils/teamNameConverter";

// Per-sport score field names on historical game records (mirrors the same mapping
// used server-side in api/services/game_service.py's _get_matchup_db_service).
const SCORE_FIELDS: { [key: string]: [string, string] } = {
  baseball_mlb: ["away_runs", "home_runs"],
  basketball_nba: ["away_points", "home_points"],
  americanfootball_nfl: ["away_points", "home_points"],
  icehockey_nhl: ["away_goals", "home_goals"],
  americanfootball_ncaaf: ["away_points", "home_points"],
  basketball_ncaab: ["away_points", "home_points"],
};

interface GameFAQSectionProps {
  sportKey: string;
  sport: string; // URL sport key, e.g. "mlb"
  homeTeam: string;
  awayTeam: string;
  headToHeadHistory: { games?: any[] } | null;
}

const GameFAQSection: React.FC<GameFAQSectionProps> = ({ sportKey, sport, homeTeam, awayTeam, headToHeadHistory }) => {
  const games = headToHeadHistory?.games || [];
  if (games.length === 0) return null;

  const [awayField, homeField] = SCORE_FIELDS[sportKey] || ["away_points", "home_points"];

  // Historical game records store short/DB team names (e.g. "Red Sox"), not the full
  // Odds-API names ("Boston Red Sox") this component receives — convert once up front,
  // mirroring the same conversion already used elsewhere in GameDetailsPage.tsx.
  const homeTeamShort = convertTeamNameBySport(sportKey, homeTeam);
  const awayTeamShort = convertTeamNameBySport(sportKey, awayTeam);

  const sorted = [...games].sort(
    (a, b) => new Date(b.game_date).getTime() - new Date(a.game_date).getTime()
  );

  let homeWins = 0;
  let awayWins = 0;
  let homeCovers = 0;
  let awayCovers = 0;
  let scoredMeetings = 0;

  for (const g of sorted) {
    const gHome = g.home_team_name || g.home_team;
    const homeScore = g[homeField];
    const awayScore = g[awayField];
    if (homeScore == null || awayScore == null) continue;
    if (gHome !== homeTeamShort && gHome !== awayTeamShort) continue;
    scoredMeetings++;

    // Whichever page-team (home/away as shown today) was the home team in this
    // historical meeting determines which raw score/line belongs to them.
    const pageHomeWasHome = gHome === homeTeamShort;
    const pageHomeScore = pageHomeWasHome ? homeScore : awayScore;
    const pageAwayScore = pageHomeWasHome ? awayScore : homeScore;

    if (pageHomeScore > pageAwayScore) homeWins++;
    else if (pageAwayScore > pageHomeScore) awayWins++;

    // MLB's home_line/away_line columns are historically populated as a straight
    // duplicate of the moneyline (not a real point spread) — see mlb_games seed
    // migrations. Adding a moneyline-sized number to a run total is meaningless,
    // so skip ATS entirely for MLB rather than show a fabricated cover record.
    const pageHomeLine = pageHomeWasHome ? g.home_line : g.away_line;
    if (sportKey !== "baseball_mlb" && typeof pageHomeLine === "number") {
      const covered = pageHomeScore + pageHomeLine > pageAwayScore;
      if (covered) homeCovers++;
      else if (pageHomeScore + pageHomeLine < pageAwayScore) awayCovers++;
    }
  }

  if (scoredMeetings === 0) return null;

  const last = sorted[0];
  const lastDate = last.game_date
    ? new Date(last.game_date).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })
    : null;

  const leader = homeWins > awayWins ? homeTeam : awayWins > homeWins ? awayTeam : null;
  const winRecordAnswer = leader
    ? `${leader} has won more of the last ${scoredMeetings} meetings (${homeTeam} ${homeWins}-${awayWins} ${awayTeam}).`
    : `The last ${scoredMeetings} meetings are split evenly (${homeWins}-${awayWins}).`;

  const atsAnswer =
    homeCovers + awayCovers > 0
      ? `${homeTeam} is ${homeCovers}-${awayCovers} against the spread in this head-to-head matchup's recent history.`
      : null;

  const teamLink = (name: string) =>
    MATCHUP_SLUG_SPORTS.has(sport) ? (
      <Link to={getTeamPageLink(sport, name)}>{name}</Link>
    ) : (
      name
    );

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", mt: 3, px: { xs: 1, sm: 0 } }}>
      <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600 }}>
        {awayTeam} vs {homeTeam}: Frequently Asked Questions
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Who has won more meetings recently?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {winRecordAnswer}
          </Typography>
        </Box>
        {atsAnswer && (
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              What's the ATS record in this matchup?
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {atsAnswer}
            </Typography>
          </Box>
        )}
        {lastDate && (
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              When did these teams last play?
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {teamLink(awayTeam)} vs {teamLink(homeTeam)} last met on {lastDate}.
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default GameFAQSection;
