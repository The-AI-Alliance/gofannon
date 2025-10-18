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
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import agentService from '../services/agentService';

const SavedAgentsPage = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState({ open: false, agentId: null, agentName: '' });

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

  const handleDeleteClick = (agentId, agentName, event) => {
    event.stopPropagation(); // Prevent navigation when clicking the delete icon
    setDeleteConfirmation({ open: true, agentId, agentName });
  };

  const handleCancelDelete = () => {
    setDeleteConfirmation({ open: false, agentId: null, agentName: '' });
  };

  const handleConfirmDelete = async () => {
    const { agentId } = deleteConfirmation;
    if (!agentId) return;

    try {
      await agentService.deleteAgent(agentId);
      // Remove the agent from the local state to update the UI
      setAgents(prev => prev.filter(agent => agent._id !== agentId));
    } catch (err) {
      setError(`Failed to delete agent: ${err.message}`);
    } finally {
      // Close the dialog regardless of success or failure
      handleCancelDelete();
    }
  };

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
                  <ListItem
                    button
                    onClick={() => navigate(`/agent/${agent._id}`)}
                    secondaryAction={
                      <IconButton edge="end" aria-label="delete" onClick={(e) => handleDeleteClick(agent._id, agent.name, e)}>
                        <DeleteIcon />
                      </IconButton>
                    }
                  >
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
      
      <Dialog
        open={deleteConfirmation.open}
        onClose={handleCancelDelete}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {"Confirm Agent Deletion"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Are you sure you want to permanently delete the agent "{deleteConfirmation.agentName}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDelete}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>      
    </Container>
  );
};

export default SavedAgentsPage;
