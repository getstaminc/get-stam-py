import React from "react";
import { Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

type TeamRankingsData = {
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

type TeamRankingsProps = {
  homeTeam: string;
  awayTeam: string;
  homeRankings: TeamRankingsData | null;
  awayRankings: TeamRankingsData | null;
  loading?: boolean;
};

const TeamRankings: React.FC<TeamRankingsProps> = ({
  homeTeam,
  awayTeam,
  homeRankings,
  awayRankings,
  loading = false
}) => {
  if (loading) {
    return (
      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Team Rankings
        </Typography>
        <Typography>Loading rankings...</Typography>
      </Paper>
    );
  }

  // Check if we have any ranking data
  const hasRankingData = homeRankings || awayRankings;

  if (!hasRankingData) {
    return null; // Don't render if no data
  }

  // Define the ranking categories we want to display
  const categories = [
    { key: "Total", label: "Total" },
    { key: "Passing", label: "Passing" },
    { key: "Rushing", label: "Rushing" },
    { key: "Scoring", label: "Scoring" }
  ];

  const formatValue = (value: string | number | undefined): string => {
    if (value === undefined || value === null) return "N/A";
    return value.toString();
  };

  const formatRank = (rank: string | number | undefined): string => {
    if (rank === undefined || rank === null) return "N/A";
    return `#${rank}`;
  };

  const RankingTable = ({ 
    team, 
    rankings, 
    title 
  }: { 
    team: string; 
    rankings: TeamRankingsData | null; 
    title: string; 
  }) => {
    if (!rankings) return null;
    
    return (
      <Paper elevation={1} sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom align="center" color="primary">
          {title}
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Category</strong></TableCell>
                <TableCell align="center"><strong>Offense</strong></TableCell>
                <TableCell align="center"><strong>Defense</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {categories.map((category) => (
                <TableRow key={category.key}>
                  <TableCell>
                    <strong>{category.label}</strong>
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                      <Typography variant="body2" color="primary" fontWeight="bold">
                        {formatRank(rankings.offense[`${category.key} Rank` as keyof typeof rankings.offense])}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {formatValue(rankings.offense[category.key as keyof typeof rankings.offense])}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                      <Typography variant="body2" color="primary" fontWeight="bold">
                        {formatRank(rankings.defense[`${category.key} Rank` as keyof typeof rankings.defense])}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {formatValue(rankings.defense[category.key as keyof typeof rankings.defense])}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    );
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom align="center" color="primary">
        Team Rankings
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box sx={{ flex: 1 }}>
          <RankingTable
            team={awayTeam}
            rankings={awayRankings}
            title={`${awayTeam} Rankings`}
          />
        </Box>
        
        <Box sx={{ flex: 1 }}>
          <RankingTable
            team={homeTeam}
            rankings={homeRankings}
            title={`${homeTeam} Rankings`}
          />
        </Box>
      </Box>
      
      <Box sx={{ mt: 2, textAlign: "center" }}>
        <Typography variant="caption" color="text.secondary">
          Rankings update every 4 hours • Offensive ranks are best-to-worst • Defensive ranks are best-to-worst (lower yards allowed = better)
        </Typography>
      </Box>
    </Paper>
  );
};

export default TeamRankings;
