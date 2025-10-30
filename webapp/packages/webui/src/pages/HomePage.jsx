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
import ApiIcon from '@mui/icons-material/Api';
import WebIcon from '@mui/icons-material/Web';
import { useAuth } from '../contexts/AuthContext';
import ActionCard from '../components/ActionCard';


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

      <Grid container spacing={3} sx={{ mt: 4 }} alignItems="stretch">
        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<ChatIcon />}
            title="Start Chatting"
            description="Chat with AI models powered by LiteLLM"
            buttonText="Open Chat"
            onClick={() => navigate('/chat')}
            iconColor="primary.main"
            buttonColor="primary"
          />            
          
        </Grid>

        {/* New Grid Item for Create Agent Flow */}
        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<CodeIcon />}
            title="Create New Agent"
            description="Define tools and behavior for a new AI agent"
            buttonText="Start Agent Creation"
            onClick={() => navigate('/create-agent')}
            iconColor="secondary.main"
            buttonColor="secondary"
          />          
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<SmartToyIcon />}
            title="View Saved Agents"
            description="Browse and manage your previously created agents"
            buttonText="Browse Agents"
            onClick={() => navigate('/agents')}
            iconColor="success.main"
            buttonColor="success"
          />          
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<ApiIcon />}
            title="View Deployed APIs"
            description="Browse all agents deployed as REST endpoints."
            buttonText="Browse APIs"
            onClick={() => navigate('/deployed-apis')}
            iconColor="info.main"
            buttonColor="info"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<WebIcon />}
            title="Create Demo App"
            description="Build a web UI that uses your deployed agents."
            buttonText="Create Demo"
            onClick={() => navigate('/create-demo')}
            iconColor="warning.main"
            buttonColor="warning"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <ActionCard
            icon={<WebIcon />}
            title="View Demo Apps"
            description="View and manage your saved demo applications."
            buttonText="View Demos"
            onClick={() => navigate('/demo-apps')}
            iconColor="secondary.light"
            buttonColor="secondary"
          />          
        </Grid>
        
      </Grid>
    </Box>
  );
};

export default HomePage;
