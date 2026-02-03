import React from "react";
import { Box, Typography, Paper, Container, Card, CardContent, Divider } from "@mui/material";

const SpreadsPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Betting 101: Point Spreads
        </Typography>
        
        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          What is a Point Spread?
        </Typography>
        <Typography variant="body1" paragraph>
          If you have ever heard someone say, “The Eagles are favored by 7 points,” they are talking about the spread.<br />
          <br />
          A point spread is designed to level the playing field between two teams. Instead of just picking 
          the winner, you're betting on whether a team will win by more than a certain number of points 
          (cover the spread) or keep the game closer than expected.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          How to Read Point Spreads
        </Typography>
        
        <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example: Lakers vs Warriors
            </Typography>
            <Typography>Lakers -7.5 (-110)</Typography>
            <Typography>Warriors +7.5 (-110)</Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          <strong>Lakers -7.5:</strong> The Lakers are favored by 7.5 points. They must win by 8 or more points 
          for your bet to win. This is called "covering the spread."
        </Typography>
        
        <Typography variant="body1" paragraph>
          <strong>Warriors +7.5:</strong> The Warriors are getting 7.5 points. They can lose by 7 or fewer points, 
          or win outright, and your bet still wins.
        </Typography>

        <Typography variant="body1" paragraph>
          The <strong>(-110)</strong> indicates the juice or vig - you typically need to bet $110 to win $100.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Examples in Action
        </Typography>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example 1: Lakers -7.5
            </Typography>
            <Typography>Final Score: Lakers 115, Warriors 102</Typography>
            <Typography>Margin: Lakers win by 13 points</Typography>
            <Typography sx={{ color: 'green', fontWeight: 'bold' }}>
              Result: Lakers cover -7.5 (13 {'>'}  7.5)
            </Typography>
          </CardContent>
        </Card>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example 2: Warriors +7.5
            </Typography>
            <Typography>Final Score: Lakers 108, Warriors 105</Typography>
            <Typography>Margin: Lakers win by 3 points</Typography>
            <Typography sx={{ color: 'green', fontWeight: 'bold' }}>
              Result: Warriors cover +7.5 (lost by only 3, which is less than 7.5)
            </Typography>
          </CardContent>
        </Card>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example 3: Warriors +7.5 (Outright Win)
            </Typography>
            <Typography>Final Score: Lakers 102, Warriors 108</Typography>
            <Typography>Margin: Warriors win by 6 points</Typography>
            <Typography sx={{ color: 'green', fontWeight: 'bold' }}>
              Result: Warriors cover +7.5 (they won outright!)
            </Typography>
          </CardContent>
        </Card>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Key Concepts
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          The Hook (.5)
        </Typography>
        <Typography variant="body1" paragraph>
          The half-point (.5) prevents ties (called "pushes"). Without it, if Lakers were -7 and won by exactly 7, 
          all bets would be returned. The hook ensures there's always a winner and loser.
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Key Numbers in Football
        </Typography>
        <Typography variant="body1" paragraph>
          In NFL betting, certain spreads are more common due to typical scoring:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li"><strong>3:</strong> Field goal (most common margin)</Typography>
          <Typography component="li"><strong>7:</strong> Touchdown + extra point</Typography>
          <Typography component="li"><strong>10:</strong> Touchdown + field goal</Typography>
          <Typography component="li"><strong>14:</strong> Two touchdowns</Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Spread Considerations
        </Typography>
        
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Line Shopping:</strong> Different sportsbooks may offer slightly different spreads. 
            Getting Lakers -7 instead of -7.5 can be the difference between winning and losing.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Timing:</strong> Spreads move based on betting action. Consider when to place your bet - 
            early for better lines or late for more information.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Injury Impact:</strong> Key player injuries can dramatically shift spreads and outcomes. Always check lineups.
          </Typography>
        </Box>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Common Mistakes
        </Typography>
        
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Confusing with Moneyline:</strong> Remember, you're not just picking the winner - 
            you need your team to cover the spread.
          </Typography>
          <Typography component="li" paragraph>
            <strong>Betting Favorites Blindly:</strong> Favorites don't always cover large spreads, 
            even when they win easily.
          </Typography>
        </Box>

        <Card sx={{ mt: 4, backgroundColor: '#e3f2fd', border: '1px solid #1976d2' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
              Remember
            </Typography>
            <Typography variant="body1">
              Point spread betting is about handicapping - finding value when you think the oddsmakers 
              have set the line incorrectly. It's not about picking the better team, but about finding 
              the better bet relative to the spread.
            </Typography>
          </CardContent>
        </Card>
      </Paper>
    </Container>
  );
};

export default SpreadsPage;