import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import CodeIcon from '@mui/icons-material/Code';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useAuth } from '../contexts/AuthContext';
import agentService from '../services/agentService';

const HomePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        setLoading(true);
        setError(null);
        const savedAgents = await agentService.getAgents();
        setAgents(savedAgents);
      } catch (err) {
        setError('Failed to load saved agents.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, []);

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
            onClick={() => navigate('/create-agent/tools')}
          >
            <CodeIcon sx={{ fontSize: 48, mb: 2, color: 'secondary.main' }} /> {/* Using CodeIcon for agent creation */}
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
                navigate('/create-agent/tools');
              }}
            >
              Start Agent Creation
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3, mt: 4 }}>
            <Typography variant="h5" gutterBottom>
              My Saved Agents
            </Typography>
            <Divider sx={{ mb: 2 }} />
            {loading && (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </Box>
            )}
            {error && <Alert severity="error">{error}</Alert>}
            {!loading && !error && (
              <List>
                {agents.length === 0 ? (
                  <Typography color="text.secondary">
                    You haven't saved any agents yet. Click "Create New Agent" to get started.
                  </Typography>
                ) : (
                  agents.map((agent) => (
                    <ListItem
                      key={agent._id}
                      button
                      // onClick={() => navigate(`/agent/${agent._id}`)} // Future feature
                    >
                      <ListItemIcon>
                        <SmartToyIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={agent.name}
                        secondary={agent.description}
                      />
                    </ListItem>
                  ))
                )}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default HomePage;
