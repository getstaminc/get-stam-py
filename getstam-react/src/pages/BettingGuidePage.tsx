import React, { useState } from "react";
import { Box, Typography, Button, Paper, TextField, Link, Container } from "@mui/material";

const BettingGuidePage: React.FC = () => {
  const [bankroll, setBankroll] = useState<string>("");
  const [percentages, setPercentages] = useState<number[] | null>(null);
  const [error, setError] = useState<string>("");

  const handleCalculate = (e: React.FormEvent) => {
    e.preventDefault();
    const value = parseFloat(bankroll);
    if (isNaN(value) || value < 0 || value > 1000000) {
      setError("Please enter a valid number between 0 and 1,000,000.");
      setPercentages(null);
      return;
    }
    setError("");
    setPercentages([1, 2, 3, 4, 5].map(percent => parseFloat((value * percent / 100).toFixed(2))));
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <main>
          <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
            Exponential Betting Guide
          </Typography>
          <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>What is exponential betting?</Typography>
          <Typography variant="body1" paragraph>
            Exponential betting is all about bankroll management, and ensuring that a bettor has a game plan for their bets. In the long run, this strategy helps you make more as you win. First, when we say ‘bankroll,’ we’re referring to how much money we are dedicating to sports betting. It could be twenty dollars, or it could be twenty thousand – we all start somewhere. The important part is to set a boundary on what we’re starting with and not to assume that we can keep adding to it if needed. That’s where you can get into trouble.
          </Typography>
          <Typography paragraph>
            Once we’ve set our starting point, we then classify bets into five categories: 1%, 2%, 3%, 4%, and 5%. These percentages correlate to how much we’ll place on a bet, with 5% of your bankroll being the most you should ever lay on a single bet at one time. How do you determine how much to place on each bet? That’s up to you, or you can consult experts (disclaimer: look at real pros who know what they're doing, not social media hacks claiming they always win – spoiler alert: no one does). I highly recommend <Link href="https://www.wagertalk.com" target="_blank" rel="noopener">wagertalk.com</Link>.
          </Typography>
          <Typography paragraph>
            To circle back, your confidence in the bet should determine its classification. You’ll most likely find yourself in the 2% to 3% range most of the time. 5% bets should not be common – you should not be maxing out your bets every time you place one.
          </Typography>
          <Typography paragraph>
            The benefit of this strategy is twofold: it helps grow your account when things are going well, and it also helps manage losses more effectively. When I’m winning, I’ll update my spreadsheet daily. This way, my 3% bet today is bigger than it was yesterday, meaning I win more. Conversely, when I’m hitting a skid and missing a lot of games, I make sure to update my numbers so I’m risking less. <strong>Do not chase losing bets.</strong> Don’t lose a 3% bet and then place a 6% bet thinking you’ll make it all back – you won’t. Stay disciplined and stick to this strategy to grow your bankroll steadily.
          </Typography>

          <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>Bankroll Calculator</Typography>
          <form onSubmit={handleCalculate}>
            <label htmlFor="numberInput" style={{ fontWeight: "bold" }}>Enter your Bankroll:</label>
            <TextField
              id="numberInput"
              type="number"
              value={bankroll}
              onChange={e => setBankroll(e.target.value)}
              inputProps={{ max: 1000000, min: 0, required: true }}
              sx={{ my: 2, width: "100%" }}
              size="small"
            />
            <Button type="submit" variant="contained" color="primary">Calculate</Button>
          </form>
          {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
          {percentages && (
            <Box id="result" sx={{ mt: 2 }}>
              {percentages.map((val, idx) => (
                <Typography key={idx}>{idx + 1}%: {val}</Typography>
              ))}
            </Box>
          )}
        </main>
      </Paper>
    </Container>
  );
};

export default BettingGuidePage;