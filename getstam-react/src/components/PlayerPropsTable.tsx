import React, { useState, useRef, useEffect } from "react";
import { Box, Paper, Button, Table, TableBody, TableCell, TableHead, TableRow, Tooltip, Typography } from "@mui/material";
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
// Legend for player props columns
const PlayerPropsLegend = () => (
  <Box sx={{ p: 1 }}>
    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
      Color Meanings:
    </Typography>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ width: 16, height: 16, backgroundColor: '#c8e6c9', border: '1px solid #ccc' }} />
        <Typography variant="body2">Covered</Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ width: 16, height: 16, backgroundColor: '#ffcdd2', border: '1px solid #ccc' }} />
        <Typography variant="body2">Didn't Cover</Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ width: 16, height: 16, backgroundColor: '#e0e0e0', border: '1px solid #ccc' }} />
        <Typography variant="body2">Pushed</Typography>
      </Box>
    </Box>
  </Box>
);

const PlayerPropsTable: React.FC<{ players: any }> = ({ players }) => {
  // Debug logging
  console.log('PlayerPropsTable received players:', players);
  console.log('Players type:', typeof players);
  console.log('Is array:', Array.isArray(players));
  
  // Handle both array and object formats
  let playersData: { [key: string]: any };
  
  if (Array.isArray(players)) {
    // Convert array to object using player_name as key
    playersData = {};
    players.forEach((player, index) => {
      const playerName = player.player_name || `Player ${index + 1}`;
      playersData[playerName] = player;
    });
  } else if (players && typeof players === 'object') {
    // Already an object
    playersData = players;
  } else {
    // Invalid format or no data
    console.error('Invalid players format:', players);
    playersData = {};
  }

  // Check if we have any valid data
  const hasData = Object.keys(playersData).length > 0;
  
  const [openPlayers, setOpenPlayers] = useState<Set<string>>(() => new Set(Object.keys(playersData)));
  const allPlayerNames = Object.keys(playersData);
  const allExpanded = openPlayers.size === allPlayerNames.length;

  const handleTogglePlayer = (name: string) => {
    setOpenPlayers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(name)) {
        newSet.delete(name);
      } else {
        newSet.add(name);
      }
      return newSet;
    });
  };

  const handleExpandCollapseAll = () => {
    if (allExpanded) {
      setOpenPlayers(new Set());
    } else {
      setOpenPlayers(new Set(allPlayerNames));
    }
  };

  const getColor = (actual: any, odds: any) => {
    if (actual == null || odds == null || isNaN(Number(actual)) || isNaN(Number(odds))) return { bgColor: undefined, color: undefined };
    if (Number(actual) > Number(odds)) return { bgColor: '#c8e6c9', color: '#000' };
    if (Number(actual) < Number(odds)) return { bgColor: '#ffcdd2', color: '#000' };
    return { bgColor: '#e0e0e0', color: '#000' };
  };

  const [showScrollIndicator, setShowScrollIndicator] = useState(false);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkScrollable = () => {
      if (tableContainerRef.current) {
        const { scrollWidth, clientWidth } = tableContainerRef.current;
        setShowScrollIndicator(scrollWidth > clientWidth);
      }
    };
    checkScrollable();
    window.addEventListener('resize', checkScrollable);
    return () => window.removeEventListener('resize', checkScrollable);
  }, [players]);

  // If no data, show empty state
  if (!hasData) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2, border: '1px solid #e0e0e0' }}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No player data available
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This could be due to server issues or no historical data for these players
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper elevation={2} sx={{ p: 2, mb: 2, border: '1px solid #e0e0e0' }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1 }}>
        <Button
          onClick={handleExpandCollapseAll}
          variant="contained"
          color="primary"
          size="small"
          startIcon={allExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{
            textTransform: 'none',
            borderRadius: 2,
            boxShadow: 'none',
            fontWeight: 500,
            fontSize: '1em',
            px: 2,
            py: 1,
            minWidth: 120,
          }}
        >
          {allExpanded ? 'Collapse All' : 'Expand All'}
        </Button>
      </Box>
      <Box sx={{ position: 'relative' }}>
        <Box
          ref={tableContainerRef}
          sx={{
            overflowX: 'auto',
            borderRadius: 1,
            '&::-webkit-scrollbar': {
              height: '8px',
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: '#f1f1f1',
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#c1c1c1',
              borderRadius: '4px',
              '&:hover': {
                backgroundColor: '#a8a8a8',
              },
            },
          }}
        >
          <Table size="small" sx={{ mt: 2, minWidth: 600 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 40, px: { xs: 1, sm: 2 }, fontWeight: 700, fontSize: '0.875rem' }}></TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>Player</TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Points
                    <Tooltip title={<PlayerPropsLegend />} arrow placement="top">
                      <InfoOutlinedIcon sx={{ fontSize: 16, color: '#666', cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Assists
                    <Tooltip title={<PlayerPropsLegend />} arrow placement="top">
                      <InfoOutlinedIcon sx={{ fontSize: 16, color: '#666', cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Rebounds
                    <Tooltip title={<PlayerPropsLegend />} arrow placement="top">
                      <InfoOutlinedIcon sx={{ fontSize: 16, color: '#666', cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Threes
                    <Tooltip title={<PlayerPropsLegend />} arrow placement="top">
                      <InfoOutlinedIcon sx={{ fontSize: 16, color: '#666', cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(playersData).map(([name, data]: [string, any]) => (
                <React.Fragment key={name}>
                  <TableRow hover style={{ cursor: 'pointer' }}>
                    <TableCell sx={{ p: 0, textAlign: 'center', px: { xs: 1, sm: 1 } }}>
                      <ExpandMoreIcon
                        sx={{
                          transform: openPlayers.has(name) ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.2s',
                          cursor: 'pointer',
                        }}
                        onClick={e => {
                          e.stopPropagation();
                          handleTogglePlayer(name);
                        }}
                        aria-label={openPlayers.has(name) ? 'Collapse' : 'Expand'}
                      />
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: 500,
                        fontSize: '0.875rem',
                        px: { xs: 0.5, sm: 1 },
                        maxWidth: { xs: 80, sm: 80 },
                        wordBreak: 'break-word',
                        whiteSpace: { xs: 'pre-line', sm: 'normal' },
                      }}
                    >
                      <Box
                        sx={{
                          display: 'inline',
                          wordBreak: 'break-word',
                          whiteSpace: { xs: 'pre-line', sm: 'normal' },
                        }}
                      >
                        {typeof name === 'string' && name.includes(' ')
                          ? name.replace(' ', '\n')
                          : (name || 'Unknown Player')}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontWeight: data.player_points && typeof data.player_points === 'object' && data.player_points.point !== undefined ? 700 : 400, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                      {data.player_points && typeof data.player_points === 'object' && data.player_points.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span style={{ fontWeight: 500 }}>{data.player_points.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontWeight: data.player_assists && typeof data.player_assists === 'object' && data.player_assists.point !== undefined ? 700 : 400, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                      {data.player_assists && typeof data.player_assists === 'object' && data.player_assists.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span style={{ fontWeight: 500 }}>{data.player_assists.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontWeight: data.player_rebounds && typeof data.player_rebounds === 'object' && data.player_rebounds.point !== undefined ? 700 : 400, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                      {data.player_rebounds && typeof data.player_rebounds === 'object' && data.player_rebounds.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span style={{ fontWeight: 500 }}>{data.player_rebounds.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontWeight: data.player_threes && typeof data.player_threes === 'object' && data.player_threes.point !== undefined ? 700 : 400, fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}>
                      {data.player_threes && typeof data.player_threes === 'object' && data.player_threes.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span style={{ fontWeight: 500 }}>{data.player_threes.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                  </TableRow>
                  {openPlayers.has(name) && (
                    data.historical && Array.isArray(data.historical) && data.historical.length > 0 ? (
                      data.historical.map((h: any, idx: number) => (
                        <TableRow key={name + '-history-' + idx}>
                          <TableCell sx={{ fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}></TableCell>
                          <TableCell sx={{ fontSize: '0.85em', color: '#888', px: { xs: 1, sm: 2 } }}>
                            {h.short_game_date ? h.short_game_date : ''} - 
                            {h.opponent_team_name ?
                              ' ' + h.opponent_team_name.split(' ').slice(-1)[0] : ''}
                          </TableCell>
                          {(() => { const c = getColor(h.actual_player_points, h.odds_player_points); return (
                            <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 }, fontWeight: 700 }}>
                              {h.odds_player_points != null ? h.odds_player_points : '—'}
                            </TableCell>
                          ); })()}
                          {(() => { const c = getColor(h.actual_player_assists, h.odds_player_assists); return (
                            <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 }, fontWeight: 700 }}>
                              {h.odds_player_assists != null ? h.odds_player_assists : '—'}
                            </TableCell>
                          ); })()}
                          {(() => { const c = getColor(h.actual_player_rebounds, h.odds_player_rebounds); return (
                            <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 }, fontWeight: 700 }}>
                              {h.odds_player_rebounds != null ? h.odds_player_rebounds : '—'}
                            </TableCell>
                          ); })()}
                          {(() => { const c = getColor(h.actual_player_threes, h.odds_player_threes); return (
                            <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 }, fontWeight: 700 }}>
                              {h.odds_player_threes != null ? h.odds_player_threes : '—'}
                            </TableCell>
                          ); })()}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell sx={{ fontSize: '0.875rem', px: { xs: 1, sm: 2 } }}></TableCell>
                        <TableCell colSpan={5} sx={{ fontSize: '0.85em', color: '#888', px: { xs: 1, sm: 2 }, textAlign: 'center', py: 2 }}>
                          No historical data available
                        </TableCell>
                      </TableRow>
                    )
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </Box>
        {showScrollIndicator && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: '20px',
              background: 'linear-gradient(to left, rgba(224,224,224,0.85) 0%, rgba(224,224,224,0.4) 50%, transparent 100%)',
              pointerEvents: 'none',
              borderRadius: '0 4px 4px 0',
            }}
          />
        )}
      </Box>
    </Paper>
  );
};

export default PlayerPropsTable;
