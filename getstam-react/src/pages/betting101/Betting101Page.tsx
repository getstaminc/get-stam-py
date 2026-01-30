import React from "react";
import { Box, Typography, Paper, Container, Grid, Card, CardContent, CardActionArea } from "@mui/material";
import { useNavigate } from "react-router-dom";
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TimelineIcon from '@mui/icons-material/Timeline';
import CombineIcon from '@mui/icons-material/AccountTree';

const Betting101Page: React.FC = () => {
  const navigate = useNavigate();

  const bettingTopics = [
    {
      title: "Moneyline Bets",
      description: "Learn the basics of picking winners with moneyline betting. Perfect for beginners.",
      icon: <TrendingUpIcon sx={{ fontSize: 40, color: '#1976d2' }} />,
      path: "/betting101/moneyline",
      difficulty: "Beginner"
    },
    {
      title: "Point Spreads",
      description: "Understand how point spreads work and level the playing field between teams.",
      icon: <ShowChartIcon sx={{ fontSize: 40, color: '#1976d2' }} />,
      path: "/betting101/spreads",
      difficulty: "Beginner"
    },
    {
      title: "Over/Under Totals",
      description: "Master totals betting by predicting high or low-scoring games.",
      icon: <TimelineIcon sx={{ fontSize: 40, color: '#1976d2' }} />,
      path: "/betting101/totals",
      difficulty: "Beginner"
    },
    {
      title: "Parlay Bets",
      description: "Combine multiple bets for bigger payouts, but understand the risks involved.",
      icon: <CombineIcon sx={{ fontSize: 40, color: '#1976d2' }} />,
      path: "/betting101/parlays",
      difficulty: "Intermediate"
    }
  ];

  const handleCardClick = (path: string) => {
    navigate(path);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold', textAlign: 'center' }}>
          Betting 101: Complete Guide
        </Typography>
        
        <Typography variant="h6" component="p" sx={{ textAlign: 'center', color: '#666', mb: 4 }}>
          Master the fundamentals of sports betting with our comprehensive guides
        </Typography>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 4 }}>
          {bettingTopics.map((topic, index) => (
            <Box key={index}>
              <Card 
                sx={{ 
                  height: '100%', 
                  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4
                  }
                }}
              >
                <CardActionArea 
                  onClick={() => handleCardClick(topic.path)}
                  sx={{ height: '100%', p: 3 }}
                >
                  <CardContent sx={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box sx={{ mb: 2 }}>
                      {topic.icon}
                    </Box>
                    
                    <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                      {topic.title}
                    </Typography>
                    
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        backgroundColor: topic.difficulty === 'Beginner' ? '#e8f5e8' : '#fff3e0',
                        color: topic.difficulty === 'Beginner' ? '#2e7d32' : '#f57c00',
                        px: 2, 
                        py: 0.5, 
                        borderRadius: 1,
                        fontWeight: 'bold',
                        mb: 2
                      }}
                    >
                      {topic.difficulty}
                    </Typography>
                    
                    <Typography variant="body1" sx={{ color: '#666', flexGrow: 1 }}>
                      {topic.description}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Box>
          ))}
        </Box>

        <Box sx={{ mt: 6, p: 3, backgroundColor: '#f5f5f5', borderRadius: 2 }}>
          <Typography variant="h5" component="h3" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
            Getting Started
          </Typography>
          <Typography variant="body1" paragraph>
            If you're new to sports betting, we recommend starting with <strong>Moneyline Bets</strong> - they're the simplest 
            form of sports betting where you just pick the winner of a game.
          </Typography>
          <Typography variant="body1" paragraph>
            Once you're comfortable with moneylines, move on to <strong>Point Spreads</strong> and <strong>Totals</strong>. 
            These add more complexity but also more opportunities to find value.
          </Typography>
          <Typography variant="body1" paragraph>
            <strong>Parlays</strong> should be saved for last - they're exciting but mathematically challenging. 
            Use them sparingly for entertainment rather than as a primary strategy.
          </Typography>
        </Box>

        <Box sx={{ mt: 4, p: 3, backgroundColor: '#e3f2fd', borderRadius: 2, border: '1px solid #1976d2' }}>
          <Typography variant="h6" component="h3" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
            Important Reminder
          </Typography>
          <Typography variant="body1">
            Sports betting should be done responsibly. Never bet more than you can afford to lose, 
            and always remember that even the best bettors lose frequently. Focus on making informed 
            decisions and managing your bankroll properly. Consider reading our 
            <strong> Exponential Betting Guide</strong> for bankroll management strategies.
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default Betting101Page;