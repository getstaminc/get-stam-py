import React from "react";
import { Box, Typography, Paper, Container, Card, CardContent, Divider } from "@mui/material";

const TotalsPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Betting 101: Over/Under Totals
        </Typography>
        
        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          What is a Totals Bet?
        </Typography>
        <Typography variant="body1" paragraph>
          A totals bet, also known as an "Over/Under" bet, involves wagering on whether the combined final score 
          of both teams will be over or under a number set by the sportsbook. You're not picking a winner - 
          you're predicting if the game will be high-scoring or low-scoring.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          How to Read Totals
        </Typography>
        
        <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example: Lakers vs Warriors
            </Typography>
            <Typography>Total: 215.5</Typography>
            <Typography>Over 215.5: -110</Typography>
            <Typography>Under 215.5: -110</Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          The sportsbook has set the total at <strong>215.5 points</strong>. You can bet whether the combined 
          final score will be over or under this number.
        </Typography>
        
        <Typography variant="body1" paragraph>
          <strong>Over 215.5:</strong> You win if the combined score is 216 or higher.<br />
          <strong>Under 215.5:</strong> You win if the combined score is 215 or lower.
        </Typography>

        <Typography variant="body1" paragraph>
          The <strong>.5</strong> (called a "hook") ensures there's no tie - the total will always be either 
          over or under the line.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Examples in Action
        </Typography>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example 1: Over 215.5
            </Typography>
            <Typography>Final Score: Lakers 118, Warriors 102</Typography>
            <Typography>Combined Total: 118 + 102 = 220 points</Typography>
            <Typography sx={{ color: 'green', fontWeight: 'bold' }}>Result: OVER wins (220 {'>'} 215.5)</Typography>
          </CardContent>
        </Card>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example 2: Under 215.5
            </Typography>
            <Typography>Final Score: Lakers 105, Warriors 108</Typography>
            <Typography>Combined Total: 105 + 108 = 213 points</Typography>
            <Typography sx={{ color: 'green', fontWeight: 'bold' }}>Result: UNDER wins (213 {'<'} 215.5)</Typography>
          </CardContent>
        </Card>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Factors That Affect Totals
        </Typography>
        
        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Pace of Play
        </Typography>
        <Typography variant="body1" paragraph>
          Teams that play at a fast pace typically lead to higher-scoring games. Look for teams that:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">Play up-tempo offense</Typography>
          <Typography component="li">Take quick shots</Typography>
          <Typography component="li">Don't slow down the game</Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Defensive Strength
        </Typography>
        <Typography variant="body1" paragraph>
          Strong defensive teams tend to produce lower-scoring games:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">Good rim protection</Typography>
          <Typography component="li">Force turnovers</Typography>
          <Typography component="li">Contest shots effectively</Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Other Factors
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Injuries:</strong> Key player injuries can significantly impact scoring
          </Typography>
          <Typography component="li" paragraph>
            <strong>Weather:</strong> For outdoor sports, wind and rain can affect totals
          </Typography>
          <Typography component="li" paragraph>
            <strong>Back-to-back games:</strong> Teams on tired legs might score less
          </Typography>
          <Typography component="li" paragraph>
            <strong>Motivation:</strong> Meaningless late-season games might lack intensity
          </Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Totals Betting Strategy
        </Typography>
        
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Research Team Trends:</strong> Some teams consistently play in high or low-scoring games
          </Typography>
          <Typography component="li" paragraph>
            <strong>Consider Matchups:</strong> How do these specific teams match up against each other?
          </Typography>
          <Typography component="li" paragraph>
            <strong>Weather Matters:</strong> Especially important for outdoor sports like football
          </Typography>
          <Typography component="li" paragraph>
            <strong>Look for Line Movement:</strong> If a total moves significantly, find out why
          </Typography>
          <Typography component="li" paragraph>
            <strong>Don't Chase Steam:</strong> Just because a total is moving doesn't mean you should follow
          </Typography>
        </Box>

        <Card sx={{ mt: 4, backgroundColor: '#e3f2fd', border: '1px solid #1976d2' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
              Pro Tip
            </Typography>
            <Typography variant="body1">
              Totals can be great for bettors who prefer to analyze game flow and pace rather than picking winners. 
              They're also excellent for live betting as you can gauge the pace of the game in real time.
            </Typography>
          </CardContent>
        </Card>
      </Paper>
    </Container>
  );
};

export default TotalsPage;