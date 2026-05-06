import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Chip,
  Tooltip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CloudIcon from '@mui/icons-material/Cloud';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
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
        const data = await agentService.getAgents();
        const withDeployment = await Promise.all(
          data.map(async (agent) => {
            try {
              const deployment = await agentService.getDeployment(agent._id);
              return { ...agent, isDeployed: deployment?.is_deployed, deployedName: deployment?.friendly_name };
            } catch {
              return { ...agent, isDeployed: false };
            }
          })
        );
        setAgents(
          withDeployment.sort((a, b) =>
            (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
          )
        );
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
    event.stopPropagation();
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
      setAgents(prev => prev.filter(agent => agent._id !== agentId));
    } catch (err) {
      setError(`Failed to delete agent: ${err.message}`);
    } finally {
      handleCancelDelete();
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, margin: '0 auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton size="small" onClick={() => navigate('/')} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 600, flexGrow: 1 }}>
          Saved Agents
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/create-agent', { state: { fresh: true } })}
        >
          Create Agent
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      
      <Paper sx={{ overflow: 'hidden' }}>
        <TableContainer>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : agents.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary" variant="body2">
                No agents yet
              </Typography>
              <Button 
                size="small" 
                onClick={() => navigate('/create-agent', { state: { fresh: true } })}
                sx={{ mt: 1 }}
              >
                Create your first agent
              </Button>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#fafafa' }}>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {agents.map((agent) => (
                  <TableRow 
                    key={agent._id} 
                    hover 
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/agent/${agent._id}`)}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {agent.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" sx={{ 
                        maxWidth: 300,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {agent.description || 'No description'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {agent.isDeployed ? (
                        <Tooltip title={`/rest/${agent.deployedName}`} arrow>
                          <Chip 
                            icon={<CloudIcon sx={{ fontSize: '14px !important' }} />}
                            label="Deployed" 
                            size="small" 
                            sx={{ 
                              bgcolor: '#dcfce7', 
                              color: '#166534',
                              fontWeight: 500,
                              fontSize: '0.7rem',
                              '& .MuiChip-icon': { color: '#166534' }
                            }}
                          />
                        </Tooltip>
                      ) : (
                        <Chip 
                          label="Draft" 
                          size="small" 
                          sx={{ 
                            bgcolor: '#f4f4f5', 
                            color: '#71717a',
                            fontWeight: 500,
                            fontSize: '0.7rem'
                          }}
                        />
                      )}
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="View" arrow>
                        <IconButton size="small" onClick={() => navigate(`/agent/${agent._id}`)}>
                          <VisibilityIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Run" arrow>
                        <IconButton size="small" onClick={() => navigate(`/agent/${agent._id}/runs`)}>
                          <PlayArrowIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete" arrow>
                        <IconButton size="small" onClick={(e) => handleDeleteClick(agent._id, agent.name, e)}>
                          <DeleteIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      </Paper>
      
      <Dialog open={deleteConfirmation.open} onClose={handleCancelDelete}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to permanently delete "{deleteConfirmation.agentName}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDelete}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>      
    </Box>
  );
};

export default SavedAgentsPage;