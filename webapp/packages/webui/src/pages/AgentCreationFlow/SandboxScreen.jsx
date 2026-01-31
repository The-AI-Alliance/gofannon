import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAgentFlow } from './AgentCreationFlowContextValue';
import agentService from '../../services/agentService';
import {
  Box,
  Typography,
  Button,
  Paper,
  TextField,
  CircularProgress,
  Alert,
  Divider,
  IconButton,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import observabilityService from '../../services/observabilityService';

const SandboxScreen = () => {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const agentFlowContext = useAgentFlow();
  
  // Local state for agent data (used when fetching by ID)
  const [agentData, setAgentData] = useState(null);
  const [loadingAgent, setLoadingAgent] = useState(false);
  const [loadError, setLoadError] = useState(null);
  
  // Determine data source - use context if available, otherwise fetch
  const inputSchema = agentData?.inputSchema || agentFlowContext.inputSchema;
  const tools = agentData?.tools || agentFlowContext.tools;
  const generatedCode = agentData?.code || agentFlowContext.generatedCode;
  const gofannonAgents = agentData?.gofannonAgents || agentFlowContext.gofannonAgents;

  console.log('[SandboxScreen] Render - agentData:', !!agentData, 'generatedCode:', !!generatedCode, 'loadingAgent:', loadingAgent);

  // Fetch agent data if we have an agentId and context is empty
  useEffect(() => {
    const needsToFetch = agentId && !agentFlowContext.generatedCode;
    console.log('[SandboxScreen] agentId:', agentId, 'contextCode:', !!agentFlowContext.generatedCode, 'needsToFetch:', needsToFetch);
    
    if (needsToFetch) {
      const fetchAgent = async () => {
        setLoadingAgent(true);
        setLoadError(null);
        try {
          console.log('[SandboxScreen] Fetching agent:', agentId);
          const data = await agentService.getAgent(agentId);
          console.log('[SandboxScreen] Fetched agent data:', data);
          console.log('[SandboxScreen] Agent code exists:', !!data.code);
          // Transform gofannonAgents if needed
          if (data.gofannonAgents && data.gofannonAgents.length > 0) {
            const allAgents = await agentService.getAgents();
            const agentMap = new Map(allAgents.map(a => [a._id, a.name]));
            data.gofannonAgents = data.gofannonAgents.map(id => ({
              id: id,
              name: agentMap.get(id) || `Unknown Agent (ID: ${id})`
            }));
          } else {
            data.gofannonAgents = [];
          }
          setAgentData(data);
        } catch (err) {
          console.error('[SandboxScreen] Fetch error:', err);
          setLoadError(err.message || 'Failed to load agent data.');
        } finally {
          setLoadingAgent(false);
        }
      };
      fetchAgent();
    }
  }, [agentId, agentFlowContext.generatedCode]);

  const [formData, setFormData] = useState({});
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Update formData when inputSchema changes
  useEffect(() => {
    if (inputSchema) {
      const newFormState = Object.keys(inputSchema).reduce((acc, key) => {
        acc[key] = ''; // default to empty string
        return acc;
      }, {});
      setFormData(newFormState);
    }
  }, [inputSchema]);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleRun = async () => {
    setIsLoading(true);
    setError(null);
    setOutput(null);
    observabilityService.log({ eventType: 'user-action', message: 'User running agent in sandbox.' });

    try {
      // Extract LLM settings from agent's invokable models
      const invokableModel = agentData?.invokableModels?.[0] || agentFlowContext.invokableModels?.[0];
      const llmSettings = invokableModel?.parameters ? {
        maxTokens: invokableModel.parameters.max_tokens || invokableModel.parameters.maxTokens,
        temperature: invokableModel.parameters.temperature,
        reasoningEffort: invokableModel.parameters.reasoning_effort || invokableModel.parameters.reasoningEffort,
      } : undefined;

      const response = await agentService.runCodeInSandbox(generatedCode, formData, tools, gofannonAgents, llmSettings);
      if (response.error) {
        setError(response.error);
      } else {
        setOutput(response.result);
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
      observabilityService.logError(err, { context: 'Agent Sandbox Execution' });
    } finally {
      setIsLoading(false);
    }
  };

  // Renders form fields based on the input schema.
  const renderFormFields = () => {
    if (!inputSchema || Object.keys(inputSchema).length === 0) {
      return <Typography color="text.secondary">No input schema defined.</Typography>;
    }
    return Object.entries(inputSchema).map(([key, type]) => {
      // Simple implementation for string types as per the default schema.
      if (type === 'string') {
        return (
          <TextField
            key={key}
            fullWidth
            multiline
            minRows={3}
            maxRows={10}
            label={key}
            value={formData[key] || ''}
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
      {/* Header with back button */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <IconButton size="small" onClick={() => navigate(-1)} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" component="h2">
          Sandbox
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Test your agent by providing input and running the generated code.
      </Typography>

      {loadingAgent && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>
      )}

      {!loadingAgent && !loadError && !generatedCode && !agentId && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No agent data found. If you refreshed the page during agent creation, the unsaved data was lost. 
          Please <a href="/create-agent/tools">start over</a> or <a href="/agents">load a saved agent</a>.
        </Alert>
      )}

      {!loadingAgent && !loadError && (
        <Box component="form" noValidate autoComplete="off">
          <Typography variant="h6" sx={{ mb: 1 }}>Input</Typography>
          {renderFormFields()}
          <Button
            variant="contained"
            onClick={handleRun}
            disabled={isLoading || !generatedCode}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
          >
            {isLoading ? 'Running...' : 'Run Agent'}
          </Button>
        </Box>
      )}

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
          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' }}>
            <pre style={{ whiteSpace: 'pre', wordBreak: 'keep-all', color: 'lightgreen', margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
              {typeof output === 'object' && output.outputText 
                ? output.outputText 
                : JSON.stringify(output, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}
    </Paper>
  );
};

export default SandboxScreen;