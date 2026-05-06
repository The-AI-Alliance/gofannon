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
import RunDataPanel from '../../components/RunDataPanel';
import RunProgressLog from '../../components/RunProgressLog';
import RunsHistoryList from '../../components/RunsHistoryList';

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

const RunsScreen = () => {
  const { agentId, runId } = useParams();
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

  console.log('[RunsScreen] Render - agentData:', !!agentData, 'generatedCode:', !!generatedCode, 'loadingAgent:', loadingAgent);

  // Fetch agent data if we have an agentId and context is empty
  useEffect(() => {
    const needsToFetch = agentId && !agentFlowContext.generatedCode;
    console.log('[RunsScreen] agentId:', agentId, 'contextCode:', !!agentFlowContext.generatedCode, 'needsToFetch:', needsToFetch);
    
    if (needsToFetch) {
      const fetchAgent = async () => {
        setLoadingAgent(true);
        setLoadError(null);
        try {
          console.log('[RunsScreen] Fetching agent:', agentId);
          const data = await agentService.getAgent(agentId);
          console.log('[RunsScreen] Fetched agent data:', data);
          console.log('[RunsScreen] Agent code exists:', !!data.code);
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
          console.error('[RunsScreen] Fetch error:', err);
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
  // Data-store ops log from the most recent run. Backend populates
  // RunCodeResponse.ops_log when the agent touched the data store.
  const [opsLog, setOpsLog] = useState(null);

  // Run history for the Progress Log accordion. In-memory only — refresh
  // wipes it. Each entry: { run_id, agent_name, started_at, _started_ms,
  // duration_ms, outcome ('success'|'error'|'running'), events: [...] }.
  // Newest is appended; the component reverses for display.
  const [runs, setRuns] = useState([]);

  // Read the declared output schema so we can send it to the agent runtime for
  // validation. Falls back to null when unavailable — the backend treats
  // a missing output_schema as "skip validation".
  const outputSchema = agentData?.outputSchema || agentFlowContext.outputSchema || null;

  // Initialize formData when inputSchema changes. If we have a
  // most-recent run (or are viewing a specific historical run via
  // runId in the URL), pre-fill with that run's input values so
  // 'tweak and re-run' is one click.
  useEffect(() => {
    if (!inputSchema) return;

    // Defaults first — these get overlaid by run values if any.
    const defaults = Object.keys(inputSchema).reduce((acc, key) => {
      acc[key] = defaultValueForType(inputSchema[key]);
      return acc;
    }, {});

    // Pick the source run for pre-fill: an explicit runId from the URL
    // wins; otherwise fall back to the most-recent run in local state.
    let sourceRun = null;
    if (runId) {
      sourceRun = runs.find((r) => r.run_id === runId) || null;
    } else if (runs.length > 0) {
      sourceRun = runs[runs.length - 1];
    }

    if (sourceRun?.input) {
      // Cast each stored value back to a form-friendly string for
      // text fields; booleans pass through as-is. Lists/JSON are
      // re-serialized so the JSON editor shows the original text.
      const next = { ...defaults };
      for (const key of Object.keys(inputSchema)) {
        if (!(key in sourceRun.input)) continue;
        const stored = sourceRun.input[key];
        const type = inputSchema[key];
        if (type === 'list' || type === 'json') {
          next[key] = JSON.stringify(stored, null, 2);
        } else if (type === 'boolean') {
          next[key] = Boolean(stored);
        } else if (stored == null) {
          next[key] = '';
        } else {
          next[key] = String(stored);
        }
      }
      setFormData(next);
      return;
    }

    setFormData(defaults);
    // runs only matters on mount/route-change; we don't want to keep
    // resetting the form mid-edit when a new run is appended. So we
    // intentionally exclude runs from deps after the initial fill.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputSchema, runId]);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleRun = async () => {
    setIsLoading(true);
    setError(null);
    setOutput(null);
    setSchemaWarnings(null);
    setOpsLog(null);
    observabilityService.log({ eventType: 'user-action', message: 'User running agent.' });

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

      // Append the run record now, with the cast input stashed on it
      // so the form can be re-filled later.
      startRun(castInput);

      // Extract LLM settings from agent's invokable models
      const invokableModel = agentData?.invokableModels?.[0] || agentFlowContext.invokableModels?.[0];
      const llmSettings = invokableModel?.parameters ? {
        maxTokens: invokableModel.parameters.max_tokens || invokableModel.parameters.maxTokens,
        temperature: invokableModel.parameters.temperature,
        reasoningEffort: invokableModel.parameters.reasoning_effort || invokableModel.parameters.reasoningEffort,
      } : undefined;

      const friendlyName = agentData?.friendlyName || agentData?.name
        || agentFlowContext.friendlyName
        || 'sandbox_agent';

      // Stream events into the in-flight 'running' run entry as they
      // arrive. The bulk handler below still runs once we have the
      // final response — it sets the run's outcome and any leftover
      // fields (ops_log, schema warnings).
      const onTraceEvent = (event) => {
        setRuns((prev) => {
          const next = [...prev];
          const idx = next.length - 1;
          if (idx < 0 || next[idx].outcome !== 'running') return prev;
          next[idx] = {
            ...next[idx],
            events: [...(next[idx].events || []), event],
          };
          return next;
        });
      };

      const response = await agentService.runCodeInSandboxStreaming(
        generatedCode, castInput, tools, gofannonAgents, llmSettings, outputSchema, friendlyName,
        onTraceEvent,
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

        // Streaming has been delivering events in real time via
        // onTraceEvent above; here we just stamp the final outcome
        // and duration on the run. Don't overwrite events — they're
        // already accumulated in place.
        const finalOutcome = response.error ? 'error' : 'success';
        setRuns((prev) => {
          const next = [...prev];
          if (next.length > 0 && next[next.length - 1].outcome === 'running') {
            const r = next[next.length - 1];
            next[next.length - 1] = {
              ...r,
              outcome: finalOutcome,
              duration_ms: Date.now() - r._started_ms,
            };
          }
          return next;
        });
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
      observabilityService.logError(err, { context: 'Agent Run Execution' });
      // Mark the in-flight run as errored so the Progress Log doesn't
      // spin forever when the request itself failed (network, 5xx,
      // etc — the backend never got far enough to emit a trace).
      setRuns((prev) => {
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].outcome === 'running') {
          const r = next[next.length - 1];
          next[next.length - 1] = {
            ...r,
            outcome: 'error',
            duration_ms: Date.now() - r._started_ms,
            events: [
              ...(r.events || []),
              {
                type: 'error',
                ts: new Date().toISOString(),
                agent_name: r.agent_name || 'unknown',
                depth: 0,
                exception_type: 'TransportError',
                message: err.message || 'Request failed before reaching the agent runtime.',
                source: 'system',
              },
            ],
          };
        }
        return next;
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Append a 'running' entry to runs[] when the user clicks Run, before
  // the request fires. handleRun replaces it with the real outcome on
  // response (or marks it errored on transport failure).
  const startRun = (castInput) => {
    const now = Date.now();
    const newRunId = `run-${now}-${Math.random().toString(36).slice(2, 7)}`;
    const agentName = agentData?.friendlyName || agentData?.name
      || agentFlowContext.friendlyName || 'sandbox_agent';
    setRuns((prev) => [
      ...prev,
      {
        run_id: newRunId,
        agent_name: agentName,
        started_at: new Date(now).toISOString(),
        _started_ms: now,
        outcome: 'running',
        // Stash the input dict so we can pre-fill the form from it
        // later (re-run / view-historical). castInput is what we
        // actually sent to the backend, with types resolved.
        input: castInput,
        events: [],
      },
    ]);
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
      {/* Header. When viewing a specific historical run (runId in URL),
          the back button takes the user back to the live runs page
          rather than browser-history-back. */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <IconButton
          size="small"
          onClick={() => {
            if (runId) {
              navigate(`/agent/${agentId}/runs`);
            } else {
              navigate(-1);
            }
          }}
          sx={{ mr: 1 }}
        >
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" component="h2">
          {runId ? 'Viewing run' : 'Run'}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {runId
          ? "You're viewing a past run. The form is editable — clicking Run starts a new run with the current values."
          : 'Test your agent by providing input and running the generated code.'}
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
            onClick={async () => { await handleRun(); }}
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

      {/* Past runs history list. Hidden when viewing a specific run
          (the user is already focused on one historical run; the list
          would just compete for attention). The list is also hidden
          when there are no runs to show — empty state would just be
          noise. Future: backed by GET /runs?agent_id=X once the run
          registry lands; currently reads from in-memory runs[]. */}
      {!runId && runs.length > 0 && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>Past runs</Typography>
          <RunsHistoryList
            runs={runs}
            inputSchema={inputSchema}
            onOpen={(rId) => navigate(`/agent/${agentId}/runs/${rId}`)}
            onRerun={(rInput) => {
              // Fill the form with this run's inputs without
              // navigating; user clicks Run when ready. Convert
              // each value back to a form-string per its schema
              // type (same logic as the init useEffect's path).
              const next = {};
              for (const key of Object.keys(inputSchema || {})) {
                const t = inputSchema[key];
                const v = rInput?.[key];
                if (t === 'list' || t === 'json') {
                  next[key] = v == null ? '' : JSON.stringify(v, null, 2);
                } else if (t === 'boolean') {
                  next[key] = Boolean(v);
                } else if (v == null) {
                  next[key] = '';
                } else {
                  next[key] = String(v);
                }
              }
              setFormData(next);
            }}
          />
        </>
      )}
      </Paper>

      {/* Right column: Progress Log above Data-store panel. The Progress
          Log is the per-agent trace of recent runs (errors highlighted,
          stack traces clickable into a side sheet). The Data Store panel
          shows ops the agent did. Both are always rendered so the
          layout doesn't jump when a run completes. Collapses below the
          main panel on narrow screens. */}
      <Box sx={{ width: { xs: '100%', lg: 380 }, flexShrink: 0, mt: { xs: 2, lg: 0 }, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <RunProgressLog runs={runs} />
        <RunDataPanel opsLog={opsLog} />
      </Box>
    </Box>
  );
};

export default RunsScreen;