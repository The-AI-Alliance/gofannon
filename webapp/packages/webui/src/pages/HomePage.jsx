import React, { useMemo} from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Grid } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import ActionCard from '../components/ActionCard';
import { cards as extensionCards } from '../extensions';

const HomePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const cards = useMemo(() => {
    const seen = new Set();

    return extensionCards
      .filter((card) => {
        if (!card?.id || seen.has(card.id)) {
          return false;
        }
        seen.add(card.id);
        return card.enabled !== false;
      })
      .sort((a, b) => (a.defaultOrder ?? Number.MAX_SAFE_INTEGER) - (b.defaultOrder ?? Number.MAX_SAFE_INTEGER));
  }, []);

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h3" component="h1" gutterBottom>
        Welcome Home{user?.email ? `, ${user.email}` : ''}!
      </Typography>
      
      <Typography variant="body1" color="text.secondary" paragraph>
        Your AI-powered workspace awaits.
      </Typography>

      <Grid container spacing={3} sx={{ mt: 4 }} alignItems="stretch">
        {cards.map((card) => (
          <Grid item xs={12} sm={6} md={4} key={card.id}>
            <ActionCard
              icon={card.icon}
              title={card.title}
              description={card.description}
              buttonText={card.buttonText}
              onClick={() => card.onAction({ navigate })}
              iconColor={card.iconColor}
              buttonColor={card.buttonColor}
            />
          </Grid>
        ))}        
        
      </Grid>
    </Box>
  );
};

export default HomePage;
