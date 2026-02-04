import React, { useState, useEffect } from "react";
import { Box, Typography, Paper, FormControl, InputLabel, Select, MenuItem, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Accordion, AccordionSummary, AccordionDetails, CircularProgress, Button } from "@mui/material";
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GameOdds from "./GameOdds";
import HistoricalGames from "./HistoricalGames";
import { getSportType } from "../types/gameTypes";
import TeamRankings from "./TeamRankings";
import { convertTeamNameBySport } from "../utils/teamNameConverter";
import { TeamOdds, TeamData, TotalsData } from "../types/gameTypes";

type Game = {
  home: TeamData;
  away: TeamData;
  totals: TotalsData;
  home_team_name?: string; // For database games
  away_team_name?: string; // For database games
};

type HistoricalData = {
  games: any[];
  count: number;
  sport: string;
  team_name?: string;
  home_team?: string;
  away_team?: string;
  limit: number;
};

type RankingsData = {
  offense: {
    Total: string;
    "Total Rank": string;
    Passing: string;
    "Passing Rank": string;
    Rushing: string;
    "Rushing Rank": string;
    Scoring: string;
    "Scoring Rank": string;
  };
  defense: {
    Total: string;
    "Total Rank": string;
    Passing: string;
    "Passing Rank": string;
    Rushing: string;
    "Rushing Rank": string;
    Scoring: string;
    "Scoring Rank": string;
  };
};

type GameDetailsProps = {
  game: Game;
  homeTeamHistory?: HistoricalData | null;
  awayTeamHistory?: HistoricalData | null;
  headToHeadHistory?: HistoricalData | null;
  // New venue-specific props
  homeTeamHomeGames?: HistoricalData | null;
  homeTeamHomeVsAway?: HistoricalData | null;
  awayTeamAwayGames?: HistoricalData | null;
  awayTeamAwayVsHome?: HistoricalData | null;
  onLimitChange?: (limit: number) => void;
  currentLimit?: number;
  sportKey?: string; // Add sport key to determine which converter to use
  homeRankings?: RankingsData | null;
  awayRankings?: RankingsData | null;
  rankingsLoading?: boolean;
  pitcherData?: {
    home_pitcher?: string;
    away_pitcher?: string;
    home_pitcher_stats?: string;
    away_pitcher_stats?: string;
  };
};

const GameDetails: React.FC<GameDetailsProps> = ({ 
  game, 
  homeTeamHistory, 
  awayTeamHistory, 
  headToHeadHistory,
  homeTeamHomeGames,
  homeTeamHomeVsAway,
  awayTeamAwayGames,
  awayTeamAwayVsHome,
  onLimitChange,
  currentLimit = 5,
  sportKey = "americanfootball_nfl", // Default to NFL if not provided
  homeRankings,
  awayRankings,
  rankingsLoading = false,
  pitcherData
}) => {
  const { home, away } = game;
  const [gamesLimit, setGamesLimit] = useState<number>(currentLimit);
  const [activeTab, setActiveTab] = useState<number>(0); // 0: Recent Performance, 1: Player Props
  const [playerPropsData, setPlayerPropsData] = useState<any>(null);
  const [playerPropsLoading, setPlayerPropsLoading] = useState<boolean>(false);

  useEffect(() => {
    const fetchPlayerProps = async () => {
      setPlayerPropsLoading(true);
      const urlParams = new URLSearchParams(window.location.search);
      const gameId = urlParams.get('game_id');
      if (gameId) {
        const res = await fetch(`/api/odds/nba/player-props/${gameId}`, {
          headers: {
            "X-API-KEY": process.env.REACT_APP_API_KEY || "",
          },
        });
        const data = await res.json();
        setPlayerPropsData(data);
      }
      setPlayerPropsLoading(false);
    };
    fetchPlayerProps();
  }, []);

  const handleLimitChange = (newLimit: number) => {
    setGamesLimit(newLimit);
    if (onLimitChange) {
      onLimitChange(newLimit);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const hasScore =
    home.score !== null &&
    home.score !== undefined &&
    away.score !== null &&
    away.score !== undefined;

  const scoreDisplay = hasScore ? `${home.score} - ${away.score}` : "— —";
  const gameStatus = hasScore ? "" : "Scheduled";

  // Get team names for historical data titles
  const homeTeamName = home.team || game.home_team_name || "Home Team";
  const awayTeamName = away.team || game.away_team_name || "Away Team";

// PlayerPropsTable component
const PlayerPropsTable: React.FC<{ players: any }> = ({ players }) => {
  // Helper to get color for stat
  const [openPlayers, setOpenPlayers] = useState<Set<string>>(() => new Set(Object.keys(players)));
  const allPlayerNames = Object.keys(players);
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
    if (Number(actual) > Number(odds)) return { bgColor: '#c8e6c9', color: '#000' }; // Light green, black text
    if (Number(actual) < Number(odds)) return { bgColor: '#ffcdd2', color: '#000' }; // Light red, black text
    return { bgColor: '#e0e0e0', color: '#000' }; // Grey for push, black text
  };
  // For scroll indicator
  const [showScrollIndicator, setShowScrollIndicator] = React.useState(false);
  const tableContainerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
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
                <TableCell sx={{ width: 40, px: { xs: 1, sm: 2 } }}></TableCell>
                <TableCell sx={{ fontSize: { xs: '0.9em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>Player</TableCell>
                <TableCell sx={{ fontSize: { xs: '0.9em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>Points</TableCell>
                <TableCell sx={{ fontSize: { xs: '0.9em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>Assists</TableCell>
                <TableCell sx={{ fontSize: { xs: '0.9em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>Rebounds</TableCell>
                <TableCell sx={{ fontSize: { xs: '0.9em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>Threes</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(players).map(([name, data]: [string, any]) => (
                <React.Fragment key={name}>
                  {/* Main player prop row, clickable for collapse/expand */}
                  <TableRow
                    hover
                    style={{ cursor: 'pointer' }}
                  >
                    <TableCell sx={{ p: 0, textAlign: 'center', px: { xs: 1, sm: 2 } }}>
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
                    <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>{name}</TableCell>
                    <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>
                      {data.player_points && typeof data.player_points === 'object' && data.player_points.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span>{data.player_points.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>
                      {data.player_assists && typeof data.player_assists === 'object' && data.player_assists.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span>{data.player_assists.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>
                      {data.player_rebounds && typeof data.player_rebounds === 'object' && data.player_rebounds.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span>{data.player_rebounds.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}>
                      {data.player_threes && typeof data.player_threes === 'object' && data.player_threes.point !== undefined ? (
                        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' } }}>
                          <span>{data.player_threes.point}</span>
                          <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 4, marginTop: 2 }}>{'O/U'}</span>
                        </Box>
                      ) : '—'}
                    </TableCell>
                  </TableRow>
                  {/* Collapsible historical rows directly under player row, no player name */}
                  {openPlayers.has(name) && Array.isArray(data.historical) && data.historical.length > 0 && data.historical.map((h: any, idx: number) => (
                    <TableRow key={name + '-history-' + idx}>
                      <TableCell sx={{ fontSize: { xs: '0.95em', sm: '1em' }, px: { xs: 1, sm: 2 } }}></TableCell>
                      <TableCell sx={{ fontSize: '0.85em', color: '#888', px: { xs: 1, sm: 2 } }}></TableCell>
                      {(() => { const c = getColor(h.actual_player_points, h.odds_player_points); return (
                        <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 } }}>{h.odds_player_points != null ? h.odds_player_points : '—'}</TableCell>
                      ); })()}
                      {(() => { const c = getColor(h.actual_player_assists, h.odds_player_assists); return (
                        <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 } }}>{h.odds_player_assists != null ? h.odds_player_assists : '—'}</TableCell>
                      ); })()}
                      {(() => { const c = getColor(h.actual_player_rebounds, h.odds_player_rebounds); return (
                        <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 } }}>{h.odds_player_rebounds != null ? h.odds_player_rebounds : '—'}</TableCell>
                      ); })()}
                      {(() => { const c = getColor(h.actual_player_threes, h.odds_player_threes); return (
                        <TableCell sx={{ backgroundColor: c.bgColor, color: c.color, px: { xs: 1, sm: 2 } }}>{h.odds_player_threes != null ? h.odds_player_threes : '—'}</TableCell>
                      ); })()}
                    </TableRow>
                  ))}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </Box>
        {/* Scroll Indicator */}
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
)};

  return (
    <Box sx={{ px: { xs: 1, sm: 0 } }}>
      <Paper elevation={3} sx={{ 
        p: { xs: 2, sm: 3 }, 
        mt: 4, 
        maxWidth: 900, 
        mx: { xs: 1, sm: "auto" },
        backgroundColor: "#f9f9f9"
      }}>
        {/* Odds section */}
        <GameOdds game={game} pitcherData={pitcherData} />
      </Paper>

      {/* Tabs for Recent Performance and Player Props */}
      <Box sx={{ maxWidth: 900, mx: "auto", mt: 3, px: { xs: 1, sm: 0 } }}>
        <Tabs value={activeTab} onChange={handleTabChange} variant="fullWidth" sx={{ mb: 2 }}>
          <Tab label="Recent Performance" />
          <Tab label="Player Props" />
        </Tabs>

        {/* Tab 0: Recent Performance (Historical Games) */}
        {activeTab === 0 && (
          <>
            <Box sx={{ 
              display: 'flex', 
              flexDirection: { xs: 'column', sm: 'row' },
              justifyContent: 'space-between', 
              alignItems: { xs: 'flex-start', sm: 'center' }, 
              mb: 3,
              gap: { xs: 2, sm: 0 }
            }}>
              <Typography variant="h5" gutterBottom sx={{ mb: 0, fontSize: { xs: '1.25rem', sm: '1.5rem' } }}>
                Recent Performance
              </Typography>
              <FormControl size="small" sx={{ minWidth: 120, width: { xs: '100%', sm: 'auto' } }}>
                <InputLabel id="games-limit-label">Show Games</InputLabel>
                <Select
                  labelId="games-limit-label"
                  id="games-limit-select"
                  value={gamesLimit}
                  label="Show Games"
                  onChange={(e) => handleLimitChange(e.target.value as number)}
                >
                  <MenuItem value={3}>Last 3</MenuItem>
                  <MenuItem value={5}>Last 5</MenuItem>
                  <MenuItem value={10}>Last 10</MenuItem>
                  <MenuItem value={15}>Last 15</MenuItem>
                  <MenuItem value={20}>Last 20</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Paper sx={{ mt: 3 }}>
              <HistoricalGames
                title={`${homeTeamName} - Last ${gamesLimit} Games`}
                games={homeTeamHistory?.games || []}
                loading={homeTeamHistory === null}
                teamName={convertTeamNameBySport(sportKey, homeTeamName)}
                sportType={getSportType(sportKey)}
              />

              <HistoricalGames
                title={`${awayTeamName} - Last ${gamesLimit} Games`}
                games={awayTeamHistory?.games || []}
                loading={awayTeamHistory === null}
                teamName={convertTeamNameBySport(sportKey, awayTeamName)}
                sportType={getSportType(sportKey)}
              />

              <HistoricalGames
                title={`${awayTeamName} vs ${homeTeamName} - Last ${gamesLimit} H2H`}
                games={headToHeadHistory?.games || []}
                loading={headToHeadHistory === null}
                teamName={convertTeamNameBySport(sportKey, homeTeamName)}
                isHeadToHead={true}
                sportType={getSportType(sportKey)}
              />
            </Paper>
            {/* Team Rankings for NFL and NCAAF */}
            {(sportKey === 'americanfootball_nfl' || sportKey === 'americanfootball_ncaaf') && (
              <TeamRankings 
                homeTeam={homeTeamName}
                awayTeam={awayTeamName}
                homeRankings={homeRankings || null}
                awayRankings={awayRankings || null}
                loading={rankingsLoading}
              />
            )}
          </>
        )}

        {/* Tab 1: Player Props */}
        {activeTab === 1 && (
          playerPropsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
              <CircularProgress />
            </Box>
          ) : playerPropsData ? (
            <Box>
              <Typography variant="h6" sx={{ mt: 2 }}>{playerPropsData.home_team.name} Player Props</Typography>
              <PlayerPropsTable players={playerPropsData.home_team.players} />
              <Typography variant="h6" sx={{ mt: 4 }}>{playerPropsData.away_team.name} Player Props</Typography>
              <PlayerPropsTable players={playerPropsData.away_team.players} />
            </Box>
          ) : null
        )}
      </Box>
    </Box>
  );
}

export default GameDetails;