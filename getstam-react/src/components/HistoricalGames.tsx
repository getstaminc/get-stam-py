import React, { useState } from "react";
import { Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Box, ClickAwayListener } from "@mui/material";
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { BaseGame, NFLGame, MLBGame, SoccerGame, HistoricalGame, SportType, HistoricalGamesProps, getSportType } from '../types/gameTypes';
import { MoneylineLegend, SpreadLegend, TotalLegend } from './common/Legend';

const HistoricalGames: React.FC<HistoricalGamesProps> = ({ 
  title, 
  games, 
  loading = false, 
  teamName = "",
  isHeadToHead = false,
  sportType 
}) => {
  const [openTooltip, setOpenTooltip] = useState<string | null>(null);

  // Helper function to detect if device is mobile
  const isMobile = () => {
    return window.innerWidth <= 768 || 'ontouchstart' in window;
  };

  const handleTooltipClick = (tooltipId: string) => {
    if (isMobile()) {
      setOpenTooltip(openTooltip === tooltipId ? null : tooltipId);
    }
  };

  const handleClickAway = () => {
    setOpenTooltip(null);
  };

  // Sport-specific data extractors
  const getGameData = (game: HistoricalGame) => {
    switch (sportType) {
      case 'nfl':
      case 'ncaaf':
      case 'nba': // Assume NBA has similar structure to NFL
        const nflGame = game as NFLGame;
        return {
          homeTeam: nflGame.home_team_name,
          awayTeam: nflGame.away_team_name,
          homeScore: nflGame.home_points,
          awayScore: nflGame.away_points,
          homeLine: nflGame.home_line,
          awayLine: nflGame.away_line,
          totalScore: nflGame.total_points,
          totalLine: nflGame.total || null,
          homeMoneyLine: nflGame.home_money_line,
          awayMoneyLine: nflGame.away_money_line
        };
      
      case 'mlb':
        const mlbGame = game as MLBGame;
        return {
          homeTeam: mlbGame.home_team,
          awayTeam: mlbGame.away_team,
          homeScore: mlbGame.home_runs,
          awayScore: mlbGame.away_runs,
          homeLine: mlbGame.home_line,
          awayLine: mlbGame.away_line,
          totalScore: mlbGame.home_runs + mlbGame.away_runs,
          totalLine: mlbGame.total,
          homeMoneyLine: null,
          awayMoneyLine: null,
          homeStartingPitcher: mlbGame.home_starting_pitcher,
          awayStartingPitcher: mlbGame.away_starting_pitcher
        };
      
      case 'soccer':
        const soccerGame = game as SoccerGame;
        return {
          homeTeam: soccerGame.home_team_name,
          awayTeam: soccerGame.away_team_name,
          homeScore: soccerGame.home_goals,
          awayScore: soccerGame.away_goals,
          homeLine: soccerGame.home_spread,
          awayLine: soccerGame.away_spread,
          totalScore: soccerGame.total_goals,
          totalLine: soccerGame.total_over_point,
          homeMoneyLine: soccerGame.home_money_line,
          awayMoneyLine: soccerGame.away_money_line,
          drawMoneyLine: soccerGame.draw_money_line
        };
      
      default:
        // Fallback for NHL - assume similar structure to NFL
        const defaultGame = game as NFLGame;
        return {
          homeTeam: defaultGame.home_team_name,
          awayTeam: defaultGame.away_team_name,
          homeScore: defaultGame.home_points,
          awayScore: defaultGame.away_points,
          homeLine: defaultGame.home_line,
          awayLine: defaultGame.away_line,
          totalScore: defaultGame.total_points,
          totalLine: defaultGame.total || null,
          homeMoneyLine: defaultGame.home_money_line,
          awayMoneyLine: defaultGame.away_money_line
        };
    }
  };

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

  // Generate unique tooltip IDs for this component instance
  const tooltipPrefix = `${title.replace(/\s+/g, '-').toLowerCase()}`;
  
  // Simple header components with info icons
  const HeaderWithWinLossInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip 
        title={<WinLossLegend />} 
        arrow 
        placement="top"
        open={isMobile() ? openTooltip === `${tooltipPrefix}-winloss` : undefined}
        disableHoverListener={isMobile()}
        disableFocusListener={isMobile()}
        disableTouchListener={!isMobile()}
      >
        <InfoOutlinedIcon 
          sx={{ 
            fontSize: 16, 
            color: '#666', 
            cursor: 'help'
          }}
          onClick={() => handleTooltipClick(`${tooltipPrefix}-winloss`)}
        />
      </Tooltip>
    </Box>
  );

  const HeaderWithSpreadInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip 
        title={<SpreadLegend />} 
        arrow 
        placement="top"
        open={isMobile() ? openTooltip === `${tooltipPrefix}-spread` : undefined}
        disableHoverListener={isMobile()}
        disableFocusListener={isMobile()}
        disableTouchListener={!isMobile()}
      >
        <InfoOutlinedIcon 
          sx={{ 
            fontSize: 16, 
            color: '#666', 
            cursor: 'help'
          }}
          onClick={() => handleTooltipClick(`${tooltipPrefix}-spread`)}
        />
      </Tooltip>
    </Box>
  );

  const HeaderWithTotalInfo = ({ children }: { children: React.ReactNode }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <strong>{children}</strong>
      <Tooltip 
        title={<TotalLegend />} 
        arrow 
        placement="top"
        open={isMobile() ? openTooltip === `${tooltipPrefix}-total` : undefined}
        disableHoverListener={isMobile()}
        disableFocusListener={isMobile()}
        disableTouchListener={!isMobile()}
      >
        <InfoOutlinedIcon 
          sx={{ 
            fontSize: 16, 
            color: '#666', 
            cursor: 'help'
          }}
          onClick={() => handleTooltipClick(`${tooltipPrefix}-total`)}
        />
      </Tooltip>
    </Box>
  );

  // Helper function to format date from YYYY-MM-DD to MM/DD/YYYY
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    
    try {
      const dateParts = dateString.split('-');
      if (dateParts.length === 3) {
        const [year, month, day] = dateParts;
        const monthNum = parseInt(month, 10);
        const dayNum = parseInt(day, 10);
        const yearNum = parseInt(year, 10);
        
        if (monthNum > 0 && monthNum <= 12 && dayNum > 0 && dayNum <= 31 && yearNum > 1900) {
          return `${monthNum}/${dayNum}/${yearNum}`;
        }
      }
      
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
    const gameData = getGameData(game);
    const isTeamHome = gameData.homeTeam === teamName;
    const isTeamAway = gameData.awayTeam === teamName;
    
    // For head-to-head tables, always show from the perspective of the teamName
    if (isHeadToHead && teamName) {
      if (isTeamHome) {
        return {
          site: 'home',
          teamPoints: gameData.homeScore,
          teamLine: gameData.homeLine,
          opponentName: gameData.awayTeam,
          opponentPoints: gameData.awayScore,
          opponentLine: gameData.awayLine
        };
      } else if (isTeamAway) {
        return {
          site: 'away',
          teamPoints: gameData.awayScore,
          teamLine: gameData.awayLine,
          opponentName: gameData.homeTeam,
          opponentPoints: gameData.homeScore,
          opponentLine: gameData.homeLine
        };
      }
    }
    
    // For individual team tables or when not head-to-head
    if (isTeamHome) {
      return {
        site: 'home',
        teamPoints: gameData.homeScore,
        teamLine: gameData.homeLine,
        opponentName: gameData.awayTeam,
        opponentPoints: gameData.awayScore,
        opponentLine: gameData.awayLine
      };
    } else if (isTeamAway) {
      return {
        site: 'away',
        teamPoints: gameData.awayScore,
        teamLine: gameData.awayLine,
        opponentName: gameData.homeTeam,
        opponentPoints: gameData.homeScore,
        opponentLine: gameData.homeLine
      };
    } else {
      // Fallback for when team name doesn't match
      return {
        site: game.team_side || 'unknown',
        teamPoints: game.team_side === 'home' ? gameData.homeScore : gameData.awayScore,
        teamLine: game.team_side === 'home' ? gameData.homeLine : gameData.awayLine,
        opponentName: game.team_side === 'home' ? gameData.awayTeam : gameData.homeTeam,
        opponentPoints: game.team_side === 'home' ? gameData.awayScore : gameData.homeScore,
        opponentLine: game.team_side === 'home' ? gameData.awayLine : gameData.homeLine
      };
    }
  };

  // Sport-specific score label
  const getScoreLabel = () => {
    switch (sportType) {
      case 'mlb':
        return 'Runs';
      case 'soccer':
        return 'Goals';
      case 'nhl':
        return 'Goals';
      default:
        return 'Points';
    }
  };

  // Sport-specific spread label
  const getSpreadLabel = () => {
    switch (sportType) {
      case 'soccer':
        return 'Spread';
      case 'mlb':
        return 'Line';
      default:
        return 'Spread';
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
    <ClickAwayListener onClickAway={handleClickAway}>
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
                <TableCell><HeaderWithWinLossInfo>{getScoreLabel()}</HeaderWithWinLossInfo></TableCell>
                <TableCell><HeaderWithSpreadInfo>{getSpreadLabel()}</HeaderWithSpreadInfo></TableCell>
                <TableCell><strong>Opponent</strong></TableCell>
                <TableCell><strong>Opponent {getScoreLabel()}</strong></TableCell>
                <TableCell><HeaderWithTotalInfo>Total</HeaderWithTotalInfo></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {games.map((game, index) => {
                const gameData = getGameData(game);
                const teamData = getTeamData(game);
                const teamLineResult = calculateLineResult(teamData.teamPoints, teamData.teamLine, teamData.opponentPoints);
                const totalColor = getTotalColor(gameData.totalScore, gameData.totalLine);
                
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
                      {teamName || (teamData.site === 'home' ? gameData.homeTeam : gameData.awayTeam)}
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
                        backgroundColor: sportType === 'mlb' ? 'transparent' : teamLineResult.bgColor,
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
                      {gameData.totalLine ?? 'None'}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </ClickAwayListener>
  );
};

export default HistoricalGames;
