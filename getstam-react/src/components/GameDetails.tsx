import React, { useState, useEffect } from "react";
import { Box, Typography, Paper, FormControl, InputLabel, Select, MenuItem, Tabs, Tab, Accordion, AccordionSummary, AccordionDetails, CircularProgress, Button } from "@mui/material";
import GameOdds from "./GameOdds";
import HistoricalGames from "./HistoricalGames";
import { getSportType } from "../types/gameTypes";
import TeamRankings from "./TeamRankings";
import { convertTeamNameBySport } from "../utils/teamNameConverter";
import { TeamOdds, TeamData, TotalsData } from "../types/gameTypes";
import PlayerPropsTable from "./PlayerPropsTable";

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
  const [historicalSubTab, setHistoricalSubTab] = useState<number>(0); // 0: Last N, 1: Home Last N, 2: Away Last N
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
    
    // Track tab clicks in Google Analytics
    if (newValue === 1 && sportKey === 'basketball_nba') {
      // For GA4 (gtag)
      if (typeof window !== 'undefined' && window.gtag) {
        window.gtag('event', 'tab_click', {
          event_category: 'User Interaction',
          event_label: 'Player Props Tab',
          sport: sportKey,
          custom_parameter: 'player_props_tab_click'
        });
      }
      
      // For Universal Analytics (ga) - if you're still using it
      if (typeof window !== 'undefined' && window.ga) {
        window.ga('send', 'event', 'User Interaction', 'Tab Click', 'Player Props Tab');
      }
    }
  };

  const handleHistoricalSubTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setHistoricalSubTab(newValue);
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

// PlayerPropsTable component is now imported from './PlayerPropsTable'

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
        {sportKey === 'basketball_nba' ? (
          <Tabs value={activeTab} onChange={handleTabChange} variant="fullWidth" sx={{ mb: 2 }}>
            <Tab label="Recent Performance" />
            <Tab label="Player Props" />
          </Tabs>
        ) : null}

        {/* Tab 0: Recent Performance (Historical Games) */}
        {(activeTab === 0 || sportKey !== 'basketball_nba') && (
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

            {/* Historical Games Sub-Tabs */}
            <Paper sx={{ mt: 3 }}>
              <Tabs
                value={historicalSubTab}
                onChange={handleHistoricalSubTabChange}
                variant="fullWidth"
                sx={{
                  borderBottom: 1,
                  borderColor: 'divider',
                  '& .MuiTab-root': {
                    minWidth: { xs: 'auto', sm: 160 },
                    fontSize: { xs: '0.8rem', sm: '0.875rem' },
                    padding: { xs: '8px 4px', sm: '12px 16px' },
                    borderRight: { xs: '1px solid #e0e0e0', sm: 'none' },
                    '&:last-child': {
                      borderRight: 'none'
                    },
                    '&.Mui-selected': {
                      backgroundColor: { xs: '#f5f5f5', sm: 'transparent' },
                      borderRight: { xs: '1px solid #1976d2', sm: 'none' }
                    }
                  },
                  '& .MuiTabs-flexContainer': {
                    borderBottom: { xs: '1px solid #e0e0e0', sm: 'none' }
                  }
                }}
              >
                <Tab label={`Last ${gamesLimit}`} />
                <Tab 
                  label={
                    <Box sx={{ textAlign: 'center' }}>
                      <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                        {`${homeTeamName} Home Last ${gamesLimit}`}
                      </Box>
                      <Box sx={{ display: { xs: 'block', sm: 'none' } }}>
                        {`${homeTeamName.length > 10 ? homeTeamName.substring(0, 10) + '...' : homeTeamName} Home`}
                      </Box>
                    </Box>
                  }
                />
                <Tab 
                  label={
                    <Box sx={{ textAlign: 'center' }}>
                      <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                        {`${awayTeamName} Away Last ${gamesLimit}`}
                      </Box>
                      <Box sx={{ display: { xs: 'block', sm: 'none' } }}>
                        {`${awayTeamName.length > 10 ? awayTeamName.substring(0, 10) + '...' : awayTeamName} Away`}
                      </Box>
                    </Box>
                  }
                />
              </Tabs>

              <Box sx={{ p: { xs: 2, sm: 3 } }}>
                {/* Tab 0: Last N Games (Original) */}
                {historicalSubTab === 0 && (
                  <>
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
                  </>
                )}

                {/* Tab 1: Home Team Home Games */}
                {historicalSubTab === 1 && (
                  <>
                    <HistoricalGames
                      title={`${homeTeamName} - Last ${gamesLimit} Home Games`}
                      games={homeTeamHomeGames?.games || []}
                      loading={homeTeamHomeGames === null}
                      teamName={convertTeamNameBySport(sportKey, homeTeamName)}
                      sportType={getSportType(sportKey)}
                    />
                    <HistoricalGames
                      title={`${homeTeamName} vs ${awayTeamName} - Last ${gamesLimit} Home H2H`}
                      games={homeTeamHomeVsAway?.games || []}
                      loading={homeTeamHomeVsAway === null}
                      teamName={convertTeamNameBySport(sportKey, homeTeamName)}
                      isHeadToHead={true}
                      sportType={getSportType(sportKey)}
                    />
                  </>
                )}

                {/* Tab 2: Away Team Away Games */}
                {historicalSubTab === 2 && (
                  <>
                    <HistoricalGames
                      title={`${awayTeamName} - Last ${gamesLimit} Away Games`}
                      games={awayTeamAwayGames?.games || []}
                      loading={awayTeamAwayGames === null}
                      teamName={convertTeamNameBySport(sportKey, awayTeamName)}
                      sportType={getSportType(sportKey)}
                    />
                    <HistoricalGames
                      title={`${awayTeamName} vs ${homeTeamName} - Last ${gamesLimit} Away H2H`}
                      games={awayTeamAwayVsHome?.games || []}
                      loading={awayTeamAwayVsHome === null}
                      teamName={convertTeamNameBySport(sportKey, awayTeamName)}
                      isHeadToHead={true}
                      sportType={getSportType(sportKey)}
                    />
                  </>
                )}
              </Box>
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
        {activeTab === 1 && sportKey === 'basketball_nba' && (
          playerPropsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
              <CircularProgress />
            </Box>
          ) : playerPropsData && playerPropsData.error ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
              <Typography variant="body1" color="text.secondary">
                {playerPropsData.error}
              </Typography>
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