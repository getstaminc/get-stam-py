import React from "react";
import { Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

type HistoricalGame = {
  game_id: number;
  game_date: string;
  home_team_name: string;
  away_team_name: string;
  home_points: number;
  away_points: number;
  total_points: number;
  home_line: number;
  away_line: number;
  home_money_line: number;
  away_money_line: number;
  start_time: string;
  team_side?: string; // Only present for team-specific games
  total?: number; // The betting total/over-under line
};

type HistoricalGamesProps = {
  title: string;
  games: HistoricalGame[];
  loading?: boolean;
  teamName?: string; // The team we're showing data for
  isHeadToHead?: boolean; // Whether this is a head-to-head table
};

const HistoricalGames: React.FC<HistoricalGamesProps> = ({ 
  title, 
  games, 
  loading = false, 
  teamName = "",
  isHeadToHead = false 
}) => {
  // Helper function to safely calculate line results
  const calculateLineResult = (points: number | null, line: number | null, opponentPoints: number | null) => {
    try {
      if (points === null || line === null || opponentPoints === null) {
        return { result: null, bgColor: 'inherit' };
      }
      
      const lineResult = (points + line) > opponentPoints;
      if (lineResult) {
        return { result: true, bgColor: '#c8e6c9' }; // Light green
      } else if ((points + line) < opponentPoints) {
        return { result: false, bgColor: '#ffcdd2' }; // Light red
      } else {
        return { result: false, bgColor: '#e0e0e0' }; // Grey for push
      }
    } catch (error) {
      return { result: null, bgColor: 'inherit' };
    }
  };

  // Helper function to get win/loss background color
  const getWinLossColor = (teamPoints: number | null, opponentPoints: number | null) => {
    if (teamPoints === null || opponentPoints === null) {
      return 'inherit';
    }
    
    if (teamPoints > opponentPoints) {
      return '#c8e6c9'; // Light green
    } else if (teamPoints < opponentPoints) {
      return '#ffcdd2'; // Light red
    } else {
      return '#e0e0e0'; // Grey for tie
    }
  };

  // Helper function to get total background color
  const getTotalColor = (actualTotal: number | null, bettingTotal: number | null) => {
    if (actualTotal === null || bettingTotal === null) {
      return 'inherit';
    }
    
    if (actualTotal > bettingTotal) {
      return '#c8e6c9'; // Light green (over hit)
    } else if (actualTotal < bettingTotal) {
      return '#ffcdd2'; // Light red (under hit)
    } else {
      return '#e0e0e0'; // Grey for exact total
    }
  };

  // Helper function to get team-specific data
  const getTeamData = (game: HistoricalGame) => {
    const isTeamHome = game.home_team_name === teamName;
    const isTeamAway = game.away_team_name === teamName;
    
    if (isTeamHome) {
      return {
        site: 'home',
        teamPoints: game.home_points,
        teamLine: game.home_line,
        opponentName: game.away_team_name,
        opponentPoints: game.away_points,
        opponentLine: game.away_line
      };
    } else if (isTeamAway) {
      return {
        site: 'away',
        teamPoints: game.away_points,
        teamLine: game.away_line,
        opponentName: game.home_team_name,
        opponentPoints: game.home_points,
        opponentLine: game.home_line
      };
    } else {
      // Fallback for when team name doesn't match
      return {
        site: game.team_side || 'unknown',
        teamPoints: game.team_side === 'home' ? game.home_points : game.away_points,
        teamLine: game.team_side === 'home' ? game.home_line : game.away_line,
        opponentName: game.team_side === 'home' ? game.away_team_name : game.home_team_name,
        opponentPoints: game.team_side === 'home' ? game.away_points : game.home_points,
        opponentLine: game.team_side === 'home' ? game.away_line : game.home_line
      };
    }
  };

  if (loading) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography>Loading...</Typography>
      </Paper>
    );
  }

  if (!games || games.length === 0) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography color="text.secondary">No games found</Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Date</strong></TableCell>
              <TableCell><strong>Site</strong></TableCell>
              <TableCell><strong>Team</strong></TableCell>
              <TableCell><strong>Points</strong></TableCell>
              <TableCell><strong>Spread</strong></TableCell>
              <TableCell><strong>Opponent</strong></TableCell>
              <TableCell><strong>Opponent Points</strong></TableCell>
              {isHeadToHead && <TableCell><strong>Opponent Spread</strong></TableCell>}
              <TableCell><strong>Total</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {games.map((game, index) => {
              const teamData = getTeamData(game);
              const teamLineResult = calculateLineResult(teamData.teamPoints, teamData.teamLine, teamData.opponentPoints);
              const opponentLineResult = calculateLineResult(teamData.opponentPoints, teamData.opponentLine, teamData.teamPoints);
              const totalColor = getTotalColor(game.total_points, game.total ?? null);
              
              return (
                <TableRow key={game.game_id || index}>
                  <TableCell>
                    {new Date(game.game_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {teamData.site}
                  </TableCell>
                  <TableCell 
                    sx={{ 
                      backgroundColor: getWinLossColor(teamData.teamPoints, teamData.opponentPoints),
                      fontWeight: 'bold'
                    }}
                  >
                    {teamName || (teamData.site === 'home' ? game.home_team_name : game.away_team_name)}
                  </TableCell>
                  <TableCell 
                    sx={{ 
                      backgroundColor: getWinLossColor(teamData.teamPoints, teamData.opponentPoints),
                      fontWeight: 'bold'
                    }}
                  >
                    {teamData.teamPoints ?? 'None'}
                  </TableCell>
                  <TableCell 
                    sx={{ 
                      backgroundColor: teamLineResult.bgColor,
                      fontWeight: 'bold'
                    }}
                  >
                    {teamData.teamLine !== null ? teamData.teamLine : 'None'}
                  </TableCell>
                  <TableCell>
                    {teamData.opponentName}
                  </TableCell>
                  <TableCell>
                    {teamData.opponentPoints ?? 'None'}
                  </TableCell>
                  {isHeadToHead && (
                    <TableCell 
                      sx={{ 
                        backgroundColor: opponentLineResult.bgColor,
                        fontWeight: 'bold'
                      }}
                    >
                      {teamData.opponentLine !== null ? teamData.opponentLine : 'None'}
                    </TableCell>
                  )}
                  <TableCell 
                    sx={{ 
                      backgroundColor: totalColor,
                      fontWeight: 'bold'
                    }}
                  >
                    {game.total_points ?? 'None'}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default HistoricalGames;
