import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import CodeIcon from '@mui/icons-material/Code';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useAuth } from '../contexts/AuthContext';


const HomePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h3" component="h1" gutterBottom>
        Welcome Home{user?.email ? `, ${user.email}` : ''}!
      </Typography>
      
      <Typography variant="body1" color="text.secondary" paragraph>
        Your AI-powered workspace awaits.
      </Typography>

      <Grid container spacing={3} sx={{ mt: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Paper 
            sx={{ 
              p: 3, 
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: 'action.hover'
              }
            }}
            onClick={() => navigate('/chat')}
          >
            <ChatIcon sx={{ fontSize: 48, mb: 2, color: 'primary.main' }} />
            <Typography variant="h6">Start Chatting</Typography>
            <Typography variant="body2" color="text.secondary">
              Chat with AI models powered by LiteLLM
            </Typography>
            <Button 
              variant="contained" 
              sx={{ mt: 2 }}
              onClick={(e) => {
                e.stopPropagation();
                navigate('/chat');
              }}
            >
              Open Chat
            </Button>
          </Paper>
        </Grid>

        {/* New Grid Item for Create Agent Flow */}
        <Grid item xs={12} sm={6} md={4}>
          <Paper 
            sx={{ 
              p: 3, 
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: 'action.hover'
              }
            }}
            onClick={() => navigate('/create-agent')}
          >
            <CodeIcon sx={{ fontSize: 48, mb: 2, color: 'secondary.main' }} /> 
            <Typography variant="h6">Create New Agent</Typography>
            <Typography variant="body2" color="text.secondary">
              Define tools and behavior for a new AI agent
            </Typography>
            <Button 
              variant="contained" 
              color="secondary"
              sx={{ mt: 2 }}
              onClick={(e) => {
                e.stopPropagation();
                navigate('/create-agent');
              }}
            >
              Start Agent Creation
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Paper 
            sx={{ 
              p: 3, 
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: 'action.hover'
              }
            }}
            onClick={() => navigate('/agents')}
          >
            <SmartToyIcon sx={{ fontSize: 48, mb: 2, color: 'success.main' }} />
            <Typography variant="h6">View Saved Agents</Typography>
            <Typography variant="body2" color="text.secondary">
              Browse and manage your previously created agents
            </Typography>
            <Button 
              variant="contained" 
              color="success"
              sx={{ mt: 2 }}
              onClick={(e) => { e.stopPropagation(); navigate('/agents'); }}
            >
              Browse Agents
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default HomePage;
