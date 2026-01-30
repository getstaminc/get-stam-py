import React from "react";
import { Box, Typography, Paper, Container, Card, CardContent, Divider } from "@mui/material";

const ParlaysPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Betting 101: Parlay Bets
        </Typography>
        
        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          What is a Parlay Bet?
        </Typography>
        <Typography variant="body1" paragraph>
          A parlay bet combines multiple individual bets into one single wager. All selections in the parlay 
          must win for the bet to pay out. If even one selection loses, the entire parlay loses. The trade-off 
          is that parlays offer much higher payouts than individual bets.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          How Parlays Work
        </Typography>
        
        <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Example: 3-Team Parlay
            </Typography>
            <Typography>• Lakers -7.5 vs Warriors (-110)</Typography>
            <Typography>• Chiefs -3.5 vs Bills (-110)</Typography>
            <Typography>• Over 215.5 in Celtics vs Heat (-110)</Typography>
            <Typography sx={{ mt: 2, fontWeight: 'bold' }}>
              Individual bets: $100 each would win ~$91 each
            </Typography>
            <Typography sx={{ fontWeight: 'bold' }}>
              3-team parlay: $100 bet would win ~$596
            </Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          <strong>All three bets must win</strong> for the parlay to pay out. If Lakers cover, Chiefs cover, 
          but the Celtics/Heat game goes under 215.5, the entire parlay loses.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Parlay Payouts
        </Typography>

        <Typography variant="body1" paragraph>
          Parlay odds multiply together, which is why payouts grow exponentially:
        </Typography>

        <Card sx={{ mb: 3, backgroundColor: '#f9f9f9' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Standard Parlay Payouts (All -110)
            </Typography>
            <Typography>2-team parlay: ~2.6 to 1 (+260)</Typography>
            <Typography>3-team parlay: ~6 to 1 (+600)</Typography>
            <Typography>4-team parlay: ~12.3 to 1 (+1230)</Typography>
            <Typography>5-team parlay: ~24.4 to 1 (+2440)</Typography>
            <Typography>6-team parlay: ~47.4 to 1 (+4740)</Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          These payouts assume all legs are -110. If you include favorites with shorter odds or underdogs 
          with longer odds, the payout will adjust accordingly.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Types of Parlays
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Traditional Parlays
        </Typography>
        <Typography variant="body1" paragraph>
          Combine different bets from different games. You can mix and match:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">Point spreads</Typography>
          <Typography component="li">Moneylines</Typography>
          <Typography component="li">Totals (Over/Under)</Typography>
          <Typography component="li">Different sports</Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Same Game Parlays (SGP)
        </Typography>
        <Typography variant="body1" paragraph>
          Combine multiple bets within the same game:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">Lakers -7.5 + Over 215.5 + LeBron Over 25.5 points</Typography>
          <Typography component="li">Correlated bets that can boost or hurt each other</Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Teasers
        </Typography>
        <Typography variant="body1" paragraph>
          Move the point spreads or totals in your favor for all selections, but accept lower payouts:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">6-point teaser: Lakers -7.5 becomes Lakers -1.5</Typography>
          <Typography component="li">Lower risk, lower reward</Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          The Mathematics of Parlays
        </Typography>

        <Typography variant="body1" paragraph>
          Understanding why parlays are difficult to win consistently:
        </Typography>

        <Card sx={{ mb: 3, backgroundColor: '#fff3e0', border: '1px solid #ff9800' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Win Probability Example
            </Typography>
            <Typography>If each individual bet has a 50% chance of winning:</Typography>
            <Typography>• 2-team parlay: 50% × 50% = 25% chance</Typography>
            <Typography>• 3-team parlay: 50% × 50% × 50% = 12.5% chance</Typography>
            <Typography>• 4-team parlay: 6.25% chance</Typography>
            <Typography>• 5-team parlay: 3.125% chance</Typography>
          </CardContent>
        </Card>

        <Typography variant="body1" paragraph>
          Even with what seems like favorable odds on individual bets, parlays become exponentially harder to hit.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Parlay Strategy
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Smart Parlay Approaches
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Small Stakes, Big Dreams:</strong> Use parlays for entertainment with small amounts you can afford to lose
          </Typography>
          <Typography component="li" paragraph>
            <strong>Correlated Plays:</strong> In same-game parlays, look for bets that help each other (team winning + over total)
          </Typography>
          <Typography component="li" paragraph>
            <strong>Heavy Favorites:</strong> Parlaying multiple heavy favorites can create decent payouts with "safer" bets
          </Typography>
          <Typography component="li" paragraph>
            <strong>Limit Legs:</strong> The more legs you add, the less likely you are to win
          </Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          What to Avoid
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li" paragraph>
            <strong>Parlaying Bad Bets:</strong> Combining several -EV bets makes an even worse bet
          </Typography>
          <Typography component="li" paragraph>
            <strong>Chasing Losses:</strong> Don't increase parlay size to make up for previous losses
          </Typography>
          <Typography component="li" paragraph>
            <strong>Over-Confidence:</strong> Winning one parlay doesn't mean you've figured out a system
          </Typography>
          <Typography component="li" paragraph>
            <strong>Making Parlays Your Primary Strategy:</strong> The math works against you long-term
          </Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h4" component="h2" gutterBottom sx={{ color: '#1976d2' }}>
          Parlay Variations
        </Typography>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          Round Robin
        </Typography>
        <Typography variant="body1" paragraph>
          Creates multiple smaller parlays from your selections. If you pick 4 teams, you can make:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <Typography component="li">Six 2-team parlays</Typography>
          <Typography component="li">Four 3-team parlays</Typography>
          <Typography component="li">One 4-team parlay</Typography>
        </Box>

        <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 3, fontWeight: 'bold' }}>
          If-Bets
        </Typography>
        <Typography variant="body1" paragraph>
          Your second bet only happens if your first bet wins, but you don't need all to win like a parlay.
        </Typography>

        <Card sx={{ mt: 4, backgroundColor: '#ffebee', border: '1px solid #f44336' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
              Important Warning
            </Typography>
            <Typography variant="body1">
              Parlays are fun and can create big payouts, but they should not be your primary betting strategy. 
              The house edge increases with each leg you add. Use them sparingly for entertainment, not as 
              a consistent way to make money. Many professional bettors avoid parlays entirely.
            </Typography>
          </CardContent>
        </Card>

        <Card sx={{ mt: 3, backgroundColor: '#e3f2fd', border: '1px solid #1976d2' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
              Bottom Line
            </Typography>
            <Typography variant="body1">
              Parlays offer the excitement of big payouts but come with exponentially lower win rates. 
              Treat them as entertainment, keep stakes small, and never bet more than you can afford to lose. 
              Focus on making good individual bets rather than trying to hit the lottery with large parlays.
            </Typography>
          </CardContent>
        </Card>
      </Paper>
    </Container>
  );
};

export default ParlaysPage;