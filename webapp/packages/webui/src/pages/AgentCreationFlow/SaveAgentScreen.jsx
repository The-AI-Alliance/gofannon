import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Stack,
  CircularProgress,
  Alert,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import { useAgentFlow } from './AgentCreationFlowContext';
import agentService from '../../services/agentService'; // Import agentService

const SaveAgentScreen = () => {
  const navigate = useNavigate();
  const {
    tools,
    swaggerSpecs,
    description: agentDescription, // Rename to avoid conflict with local state
    inputSchema,
    outputSchema,
    generatedCode,
    friendlyName,
    docstring,
    invokableModels,
    gofannonAgents,
  } = useAgentFlow();
  const [agentName, setAgentName] = useState(friendlyName || ''); // Pre-fill with existing friendly name if available
  const [description, setDescription] = useState(agentDescription); // Pre-fill with existing description
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSaveAgent = async () => {
    setError(null);
    setSuccess(false);
    setIsLoading(true);

    if (!agentName.trim()) {
      setError('Agent Name is required.');
      setIsLoading(false);
      return;
    }
    if (!description.trim()) {
      setError('Agent Description is required.');
      setIsLoading(false);
      return;
    }
    if (!generatedCode) {
        setError('Agent code has not been generated. Please go back to the code screen.');
        setIsLoading(false);
        return;
    }

    const agentData = {
      name: agentName,
      description: description,
      code: generatedCode,
      docstring,
      friendlyName: friendlyName,
      tools,
      swaggerSpecs: swaggerSpecs,
      inputSchema: inputSchema,
      outputSchema: outputSchema,
      invokableModels: invokableModels,
      gofannonAgents: (gofannonAgents || []).map(agent => agent.id),
    };

    try {
      await agentService.saveAgent(agentData);
      setSuccess(true);
      setTimeout(() => {
        navigate('/'); // Navigate to home page after successful save
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to save agent.');
      console.error('Error saving agent:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Save Your Agent
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Give your agent a name and refine its description before saving.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Agent saved successfully! Redirecting to home...
        </Alert>
      )}

      <TextField
        fullWidth
        label="Agent Name"
        variant="outlined"
        value={agentName}
        onChange={(e) => setAgentName(e.target.value)}
        sx={{ mb: 3 }}
        disabled={isLoading}
        required
      />

      <TextField
        fullWidth
        multiline
        rows={6}
        label="Agent Description"
        variant="outlined"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        sx={{ mb: 3 }}
        disabled={isLoading}
        required
      />

      <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ mt: 3 }}>
        <Button
          variant="outlined"
          onClick={() => navigate('/create-agent/deploy')} // Go back to deploy screen
          disabled={isLoading}
        >
          Back
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
          onClick={handleSaveAgent}
          disabled={isLoading || !agentName.trim() || !description.trim()}
        >
          {isLoading ? 'Saving...' : 'Save Agent'}
        </Button>
      </Stack>
    </Paper>
  );
};

export default SaveAgentScreen;