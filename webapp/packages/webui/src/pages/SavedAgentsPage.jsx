import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Container,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AddIcon from '@mui/icons-material/Add';
import agentService from '../services/agentService';

const SavedAgentsPage = () => {
  const navigate = useNavigate();
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
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Saved Agents
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/create-agent')}
        >
          Create New Agent
        </Button>
      </Box>
      
      <Paper sx={{ p: 3 }}>
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>}
        {error && <Alert severity="error">{error}</Alert>}
        {!loading && !error && (
          <List>
            {agents.length === 0 ? (
              <Typography color="text.secondary" textAlign="center">
                You haven't saved any agents yet. Click "Create New Agent" to get started.
              </Typography>
            ) : (
              agents.map((agent, index) => (
                <React.Fragment key={agent._id}>
                  <ListItem button onClick={() => navigate(`/agent/${agent._id}`)}>
                    <ListItemIcon><SmartToyIcon /></ListItemIcon>
                    <ListItemText primary={agent.name} secondary={agent.description} />
                  </ListItem>
                  {index < agents.length - 1 && <Divider />}
                </React.Fragment>
              ))
            )}
          </List>
        )}
      </Paper>
    </Container>
  );
};

export default SavedAgentsPage;
