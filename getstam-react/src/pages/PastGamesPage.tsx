import React, { useState } from "react";
import {
  Box,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Container,
  Button,
  ButtonGroup
} from "@mui/material";
import PastGamesDisplay from "../components/PastGamesDisplay";

const PastGamesPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    // Default to yesterday
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toISOString().split('T')[0];
  });
  
  const [selectedSport, setSelectedSport] = useState<'mlb' | 'nfl' | 'ncaaf' | 'soccer'>('mlb');

  const getQuickDateOptions = () => {
    const today = new Date();
    const options = [];
    
    for (let i = 1; i <= 7; i++) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const label = i === 1 ? 'Yesterday' : `${i} days ago`;
      options.push({ value: dateStr, label });
    }
    
    return options;
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header and Controls */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ textAlign: 'center', mb: 3 }}>
          Historical Games
        </Typography>
        
        <Box display="flex" flexWrap="wrap" gap={3} justifyContent="center" alignItems="center">
          {/* Date Picker */}
          <TextField
            type="date"
            label="Select Date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 150 }}
          />

          {/* Quick Date Options */}
          <ButtonGroup variant="outlined" size="small">
            {getQuickDateOptions().slice(0, 3).map((option) => (
              <Button
                key={option.value}
                onClick={() => setSelectedDate(option.value)}
                variant={selectedDate === option.value ? "contained" : "outlined"}
              >
                {option.label}
              </Button>
            ))}
          </ButtonGroup>

          {/* Sport Selector */}
          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel id="sport-select-label">Sport</InputLabel>
            <Select
              labelId="sport-select-label"
              value={selectedSport}
              label="Sport"
              onChange={(e) => setSelectedSport(e.target.value as typeof selectedSport)}
            >
              <MenuItem value="mlb">MLB</MenuItem>
              <MenuItem value="nfl">NFL</MenuItem>
              <MenuItem value="ncaaf">NCAAF</MenuItem>
              <MenuItem value="soccer">Soccer</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Selected Info */}
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Showing {selectedSport.toUpperCase()} games for {new Date(selectedDate).toLocaleDateString('en-US', { 
              weekday: 'long', 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}
          </Typography>
        </Box>
      </Paper>

      {/* Games Display */}
      <PastGamesDisplay
        selectedDate={selectedDate}
        sportType={selectedSport}
      />
    </Container>
  );
};

export default PastGamesPage;
