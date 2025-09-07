import React from "react";
import { Box, Typography, Container, Paper } from "@mui/material";

const AboutUsPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography 
          variant="h3" 
          component="h1" 
          gutterBottom
          sx={{ 
            color: "#1976d2", 
            fontWeight: "bold"
          }}
        >
          About Us
        </Typography>
        
        <Typography 
          variant="body1" 
          paragraph
          sx={{ 
            fontSize: "1.1rem", 
            lineHeight: 1.7
          }}
        >
          GetStam was born out of necessity. As lifelong sports bettors we kept running into the same 
          frustrating problem. We would look at a team's recent games but couldn't easily find how they 
          were performing against the spread or how often they were going over or under the total. We 
          searched every stat site and tool available but nothing gave us exactly what we needed. So we 
          built it ourselves.
        </Typography>
        
        <Typography 
          variant="body1" 
          paragraph
          sx={{ 
            fontSize: "1.1rem", 
            lineHeight: 1.7
          }}
        >
          We knew our way around a keyboard and just like that GetStam.com was created. A site built by 
          bettors for bettors.
        </Typography>
        
        <Typography 
          variant="body1" 
          paragraph
          sx={{ 
            fontSize: "1.1rem", 
            lineHeight: 1.7
          }}
        >
          Our goal is to keep evolving. We're building the tools we always wanted but we are just as 
          interested in what you want. If there are stats, insights, or tools you would like to see 
          added to the site, let us know. We're all ears and all in.
        </Typography>
      </Paper>
    </Container>
  );
};

export default AboutUsPage;
