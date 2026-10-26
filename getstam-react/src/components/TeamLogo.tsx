import React from 'react';
import { Box } from '@mui/material';
import { convertTeamNameBySport } from '../utils/teamNameConverter';
import { getSportType } from '../types/gameTypes';
import { getTeamColors } from '../utils/teamColors';

interface TeamLogoProps {
  // Odds-API-style ("baseball_mlb") or short db-style ("mlb") sport key — both work,
  // since convertTeamNameBySport/getSportType already support either.
  sportKey: string;
  // Full odds-API team name ("Milwaukee Brewers") or an already-short name
  // ("Brewers") — convertTeamNameBySport passes short names through unchanged.
  teamName: string;
  size: number;
  border?: string;
}

const TeamLogo: React.FC<TeamLogoProps> = ({ sportKey, teamName, size, border }) => {
  const dbSport = getSportType(sportKey);
  const shortName = convertTeamNameBySport(sportKey, teamName);
  const { primary, secondary, abbr } = getTeamColors(dbSport, shortName);

  return (
    <Box
      sx={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        backgroundColor: primary,
        color: secondary,
        fontWeight: 800,
        fontSize: Math.round(size * 0.3),
        border,
      }}
    >
      {abbr}
    </Box>
  );
};

export default TeamLogo;
