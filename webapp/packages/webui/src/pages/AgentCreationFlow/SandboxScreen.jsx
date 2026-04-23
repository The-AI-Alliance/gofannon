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
  AlertTitle,
  Divider,
  IconButton,
  FormControlLabel,
  Switch,
  Tooltip,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import observabilityService from '../../services/observabilityService';
import SandboxDataPanel from '../../components/SandboxDataPanel';

// Default value per schema type, used when initializing the form.
const defaultValueForType = (type) => {
  switch (type) {
    case 'integer':
    case 'float':
      return '';       // empty string lets the user clear the field; cast on submit
    case 'boolean':
      return false;
    case 'list':
    case 'json':
      return '';       // user types JSON; parse on submit
    default:
      return '';
  }
};

// Cast the form value to the declared type before sending to the backend.
// Throws on invalid input (caught by handleRun).
const castValueForType = (type, value) => {
  switch (type) {
    case 'integer': {
      if (value === '' || value === null || value === undefined) return null;
      const n = Number(value);
      if (!Number.isInteger(n)) throw new Error(`must be an integer, got "${value}"`);
      return n;
    }
    case 'float': {
      if (value === '' || value === null || value === undefined) return null;
      const n = Number(value);
      if (Number.isNaN(n)) throw new Error(`must be a number, got "${value}"`);
      return n;
    }
    case 'boolean':
      return Boolean(value);
    case 'list':
    case 'json': {
      if (value === '' || value === null || value === undefined) {
        return type === 'list' ? [] : null;
      }
      try {
        return JSON.parse(value);
      } catch (e) {
        throw new Error(`must be valid JSON, got parse error: ${e.message}`);
      }
    }
    default:
      return value ?? '';
  }
};

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
  // Warnings from the server-side output-schema validator. Advisory only —
  // the agent ran successfully, but its return value didn't match the
  // declared output_schema (e.g. returned {"outputText": ...} instead of
  // the declared keys). See validate_output_against_schema in dependencies.py.
  const [schemaWarnings, setSchemaWarnings] = useState(null);
  // Data-store ops log from the most recent sandbox run. Backend populates
  // RunCodeResponse.ops_log when the agent touched the data store.
  const [opsLog, setOpsLog] = useState(null);

  // Read the declared output schema so we can send it to the sandbox for
  // validation. Falls back to null when unavailable — the backend treats
  // a missing output_schema as "skip validation".
  const outputSchema = agentData?.outputSchema || agentFlowContext.outputSchema || null;

  // Update formData when inputSchema changes.
  // Default values per type so each control gets a sensible starting point.
  useEffect(() => {
    if (inputSchema) {
      const newFormState = Object.keys(inputSchema).reduce((acc, key) => {
        acc[key] = defaultValueForType(inputSchema[key]);
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
    setSchemaWarnings(null);
    setOpsLog(null);
    observabilityService.log({ eventType: 'user-action', message: 'User running agent in sandbox.' });

    try {
      // Cast each field per its declared schema type before sending to the
      // agent. Throws with a field-named message on parse failures.
      let castInput;
      try {
        castInput = Object.entries(inputSchema || {}).reduce((acc, [key, type]) => {
          acc[key] = castValueForType(type, formData[key]);
          return acc;
        }, {});
      } catch (castErr) {
        setError(`Input validation failed: ${castErr.message}`);
        setIsLoading(false);
        return;
      }

      // Extract LLM settings from agent's invokable models
      const invokableModel = agentData?.invokableModels?.[0] || agentFlowContext.invokableModels?.[0];
      const llmSettings = invokableModel?.parameters ? {
        maxTokens: invokableModel.parameters.max_tokens || invokableModel.parameters.maxTokens,
        temperature: invokableModel.parameters.temperature,
        reasoningEffort: invokableModel.parameters.reasoning_effort || invokableModel.parameters.reasoningEffort,
      } : undefined;

      const response = await agentService.runCodeInSandbox(
        generatedCode, castInput, tools, gofannonAgents, llmSettings, outputSchema
      );
      if (response.error) {
        setError(response.error);
      } else {
        setOutput(response.result);
        // Schema warnings (advisory): surfaced above the Output panel.
        // Backend sends camelCase via RunCodeResponse alias; accept both.
        const warnings = response.schemaWarnings || response.schema_warnings;
        if (warnings && warnings.length) {
          setSchemaWarnings(warnings);
        }
        // Data-store ops log from the live panel. Null/empty when the
        // agent didn't touch the data store.
        const ops = response.opsLog || response.ops_log;
        if (ops && ops.length) {
          setOpsLog(ops);
        }
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
      observabilityService.logError(err, { context: 'Agent Sandbox Execution' });
    } finally {
      setIsLoading(false);
    }
  };

  // Renders form fields based on the input schema type.
  const renderFormFields = () => {
    if (!inputSchema || Object.keys(inputSchema).length === 0) {
      return <Typography color="text.secondary">No input schema defined.</Typography>;
    }
    return Object.entries(inputSchema).map(([key, type]) => {
      const value = formData[key];

      if (type === 'integer' || type === 'float') {
        return (
          <TextField
            key={key}
            fullWidth
            type="number"
            label={`${key} (${type})`}
            value={value ?? ''}
            onChange={(e) => handleInputChange(key, e.target.value)}
            inputProps={type === 'integer' ? { step: 1 } : { step: 'any' }}
            sx={{ mb: 2 }}
          />
        );
      }

      if (type === 'boolean') {
        return (
          <FormControlLabel
            key={key}
            sx={{ display: 'block', mb: 2 }}
            control={
              <Switch
                checked={Boolean(value)}
                onChange={(e) => handleInputChange(key, e.target.checked)}
              />
            }
            label={`${key} (boolean)`}
          />
        );
      }

      if (type === 'list' || type === 'json') {
        const placeholder = type === 'list'
          ? '["item1", "item2"]'
          : '{"key": "value"}';
        const tooltip = type === 'list'
          ? 'Enter a JSON array. Example: ["apple", "banana", "cherry"]'
          : 'Enter any valid JSON. Object, array, number, string, boolean, or null.';
        return (
          <Box key={key} sx={{ mb: 2, position: 'relative' }}>
            <TextField
              fullWidth
              multiline
              minRows={3}
              maxRows={10}
              label={`${key} (${type})`}
              placeholder={placeholder}
              value={value ?? ''}
              onChange={(e) => handleInputChange(key, e.target.value)}
              InputProps={{
                sx: { fontFamily: 'monospace', fontSize: '0.9rem' },
                endAdornment: (
                  <Tooltip title={tooltip} arrow placement="top">
                    <HelpOutlineIcon
                      fontSize="small"
                      sx={{ color: 'text.secondary', alignSelf: 'flex-start', mt: 1 }}
                    />
                  </Tooltip>
                ),
              }}
            />
          </Box>
        );
      }

      // string (and any unknown type) → plain multiline TextField
      return (
        <TextField
          key={key}
          fullWidth
          multiline
          minRows={3}
          maxRows={10}
          label={`${key}${type !== 'string' ? ` (${type})` : ''}`}
          value={value ?? ''}
          onChange={(e) => handleInputChange(key, e.target.value)}
          sx={{ mb: 2 }}
        />
      );
    });
  };

  return (
    <Box sx={{
      maxWidth: 1400,
      margin: 'auto',
      mt: 4,
      px: 2,
      display: 'flex',
      flexDirection: { xs: 'column', lg: 'row' },
      gap: 2,
      alignItems: 'stretch',
    }}>
      <Paper sx={{ p: 3, flexGrow: 1, minWidth: 0 }}>
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
          {schemaWarnings && schemaWarnings.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <AlertTitle>Output does not match declared schema</AlertTitle>
              The agent ran successfully, but its return value doesn&apos;t match the
              output schema you declared. Consider regenerating the code, or
              adjusting the schema to match what the agent actually produces.
              <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
                {schemaWarnings.map((w, i) => (
                  <li key={i}><code>{w}</code></li>
                ))}
              </ul>
            </Alert>
          )}
          <Typography variant="h6" sx={{ mb: 1 }}>Output</Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' }}>
            <pre style={{ whiteSpace: 'pre', wordBreak: 'keep-all', color: 'lightgreen', margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
              {JSON.stringify(output, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}
      </Paper>

      {/* Data-store side panel. Always rendered (empty state shows hint text)
          so the layout doesn't jump when a run adds ops. Collapses below
          the main panel on narrow screens. */}
      <Box sx={{ width: { xs: '100%', lg: 380 }, flexShrink: 0, mt: { xs: 2, lg: 0 } }}>
        <SandboxDataPanel opsLog={opsLog} />
      </Box>
    </Box>
  );
};

export default SandboxScreen;