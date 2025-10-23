import React, { useState } from 'react';
import { useAgentFlow } from './AgentCreationFlowContext';
import agentService from '../../services/agentService';
import {
  Box,
  Typography,
  Button,
  Paper,
  TextField,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

const SandboxScreen = () => {
  const { inputSchema, tools, generatedCode, gofannonAgents } = useAgentFlow();
  // Create initial form state from schema.
  const initialFormState = Object.keys(inputSchema).reduce((acc, key) => {
    acc[key] = ''; // default to empty string
    return acc;
  }, {});

  const [formData, setFormData] = useState(initialFormState);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleRun = async () => {
    setIsLoading(true);
    setError(null);
    setOutput(null);

    try {
      const response = await agentService.runCodeInSandbox(generatedCode, formData, tools, gofannonAgents);
      if (response.error) {
        setError(response.error);
      } else {
        setOutput(response.result);
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // Renders form fields based on the input schema.
  const renderFormFields = () => {
    return Object.entries(inputSchema).map(([key, type]) => {
      // Simple implementation for string types as per the default schema.
      if (type === 'string') {
        return (
          <TextField
            key={key}
            fullWidth
            label={key}
            value={formData[key]}
            onChange={(e) => handleInputChange(key, e.target.value)}
            sx={{ mb: 2 }}
          />
        );
      }
      return <Typography key={key}>Unsupported input type: {type} for key: {key}</Typography>;
    });
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 800, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 5: Sandbox
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Test your agent by providing input and running the generated code.
      </Typography>

      <Box component="form" noValidate autoComplete="off">
        <Typography variant="h6" sx={{ mb: 1 }}>Input</Typography>
        {renderFormFields()}
        <Button
          variant="contained"
          onClick={handleRun}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
        >
          {isLoading ? 'Running...' : 'Run Agent'}
        </Button>
      </Box>

      {(output || error) && <Divider sx={{ my: 3 }} />}

      {error && (
        <Box>
          <Typography variant="h6" color="error" sx={{ mb: 1 }}>Error</Typography>
          <Alert severity="error" sx={{ maxHeight: '200px', overflowY: 'auto' }}>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{error}</pre>
          </Alert>
        </Box>
      )}

      {output && (
        <Box>
          <Typography variant="h6" sx={{ mb: 1 }}>Output</Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '300px' }}>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'lightgreen' }}>
              {JSON.stringify(output, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}
    </Paper>
  );
};

export default SandboxScreen;