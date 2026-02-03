import React from "react";
import { Box, Typography, Paper, Container, Card, CardContent, Divider } from "@mui/material";

const MoneylinePage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Betting 101: Moneyline Bets
        </Typography>
        
        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          What is a Moneyline Bet?
        </Typography>
        <Typography variant="body1" paragraph> 
          If you are brand new to sports betting, the first term you will run into is moneyline.
          A moneyline bet is the simplest form of sports betting. You're simply picking which team will win the game, 
          regardless of the final score or margin of victory. No point spreads, no totals - just pick the winner.
           If your team wins, your bet wins. If they lose, your bet loses. That’s it.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          How to Read Moneyline Odds
        </Typography>
        
        <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example: Lakers vs Warriors
            </Typography>
            <Typography>Lakers: -150</Typography>
            <Typography>Warriors: +130</Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          <strong>Negative numbers indicate the favorite. (-150)</strong>  You need to bet $150 to win $100.
          The Lakers are favored to win this game.
        </Typography>
        
        <Typography variant="body1" paragraph> 
          <strong>Positive numbersindicate the underdog. (+130)</strong>  A $100 bet wins $130.
          The Warriors are the underdog in this matchup.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Calculating Payouts
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Favorites (Negative Odds)
        </Typography>
        <Typography variant="body1" paragraph>
          Formula: <strong>Bet Amount ÷ (Odds ÷ 100) = Profit</strong>
        </Typography>
        <Typography variant="body1" paragraph>
          Example: $150 bet on Lakers -150<br />
          $150 ÷ (150 ÷ 100) = $150 ÷ 1.5 = $100 profit<br />
          <strong>Total return: $250 (your $150 bet + $100 profit)</strong>
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Underdogs (Positive Odds)
        </Typography>
        <Typography variant="body1" paragraph>
          Formula: <strong>(Odds ÷ 100) × Bet Amount = Profit</strong>
        </Typography>
        <Typography variant="body1" paragraph>
          Example: $100 bet on Warriors +130<br />
          (130 ÷ 100) × $100 = 1.3 × $100 = $130 profit<br />
          <strong>Total return: $230 (your $100 bet + $130 profit)</strong>
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Moneyline Strategy Tips
        </Typography>
        
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Value Betting:</strong> Look for situations where you believe the underdog has a better chance 
            of winning than the odds suggest.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Favorites vs Underdogs:</strong> Betting favorites gives you a higher win percentage but lower payouts. 
            Underdogs offer bigger payouts but win less frequently.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Shop for Lines:</strong> Different sportsbooks may offer slightly different moneyline odds. 
            Always compare to get the best value.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Consider Context:</strong> Injuries, weather, home/away, and recent form can all impact 
            which team is more likely to win straight up.
          </Typography>
        </Box>

        <Card sx={{ mt: 4, backgroundColor: '#e3f2fd', border: '1px solid #1976d2' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
              Remember
            </Typography>
            <Typography variant="body1">
              Always practice proper bankroll management and never bet more than you can afford to lose.
            </Typography>
          </CardContent>
        </Card>
      </Paper>
    </Container>
  );
};

export default MoneylinePage;