import React from "react";
import { Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Box } from "@mui/material";
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

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
  // Color legend tooltip content for Team/Points columns
  const WinLossLegend = () => (
    <Box sx={{ p: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
        Color Meanings:
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#c8e6c9', border: '1px solid #ccc' }} />
          <Typography variant="body2">Win</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#ffcdd2', border: '1px solid #ccc' }} />
          <Typography variant="body2">Loss</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#e0e0e0', border: '1px solid #ccc' }} />
          <Typography variant="body2">Tie</Typography>
        </Box>
      </Box>
    </Box>
  );

  // Color legend tooltip content for Spread column
  const SpreadLegend = () => (
    <Box sx={{ p: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
        Color Meanings:
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#c8e6c9', border: '1px solid #ccc' }} />
          <Typography variant="body2">Cover</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#ffcdd2', border: '1px solid #ccc' }} />
          <Typography variant="body2">Not Cover</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#e0e0e0', border: '1px solid #ccc' }} />
          <Typography variant="body2">Push</Typography>
        </Box>
      </Box>
    </Box>
  );

  // Color legend tooltip content for Total column
  const TotalLegend = () => (
    <Box sx={{ p: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
        Color Meanings:
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#c8e6c9', border: '1px solid #ccc' }} />
          <Typography variant="body2">Over</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#ffcdd2', border: '1px solid #ccc' }} />
          <Typography variant="body2">Under</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, backgroundColor: '#e0e0e0', border: '1px solid #ccc' }} />
          <Typography variant="body2">Push</Typography>
        </Box>
      </Box>
    </Box>
  );

  // Simple header components with info icons
  const HeaderWithWinLossInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip title={<WinLossLegend />} arrow placement="top">
        <InfoOutlinedIcon sx={{ 
          fontSize: 16, 
          color: '#666', 
          cursor: 'help'
        }} />
      </Tooltip>
    </Box>
  );

  const HeaderWithSpreadInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip title={<SpreadLegend />} arrow placement="top">
        <InfoOutlinedIcon sx={{ 
          fontSize: 16, 
          color: '#666', 
          cursor: 'help'
        }} />
      </Tooltip>
    </Box>
  );

  const HeaderWithTotalInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip title={<TotalLegend />} arrow placement="top">
        <InfoOutlinedIcon sx={{ 
          fontSize: 16, 
          color: '#666', 
          cursor: 'help'
        }} />
      </Tooltip>
    </Box>
  );
  // Helper function to format date from YYYY-MM-DD to MM/DD/YYYY
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    
    try {
      // Handle PostgreSQL date type (YYYY-MM-DD format)
      // Split by '-' and ensure we have exactly 3 parts
      const dateParts = dateString.split('-');
      if (dateParts.length === 3) {
        const [year, month, day] = dateParts;
        // Remove any leading zeros and ensure valid date parts
        const monthNum = parseInt(month, 10);
        const dayNum = parseInt(day, 10);
        const yearNum = parseInt(year, 10);
        
        if (monthNum > 0 && monthNum <= 12 && dayNum > 0 && dayNum <= 31 && yearNum > 1900) {
          return `${monthNum}/${dayNum}/${yearNum}`;
        }
      }
      
      // If it's not in expected format, return as is
      return dateString;
    } catch (error) {
      return dateString;
    }
  };

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
    
    // For head-to-head tables, always show from the perspective of the teamName
    if (isHeadToHead && teamName) {
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
      }
    }
    
    // For individual team tables or when not head-to-head
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
              <TableCell><HeaderWithWinLossInfo>Team</HeaderWithWinLossInfo></TableCell>
              <TableCell><HeaderWithWinLossInfo>Points</HeaderWithWinLossInfo></TableCell>
              <TableCell><HeaderWithSpreadInfo>Spread</HeaderWithSpreadInfo></TableCell>
              <TableCell><strong>Opponent</strong></TableCell>
              <TableCell><strong>Opponent Points</strong></TableCell>
              <TableCell><HeaderWithTotalInfo>Total</HeaderWithTotalInfo></TableCell>
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
                    {formatDate(game.game_date)}
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
                  <TableCell 
                    sx={{ 
                      backgroundColor: totalColor,
                      fontWeight: 'bold'
                    }}
                  >
                    {game.total ?? 'None'}
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
