import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAgentFlow } from './AgentCreationFlowContextValue';
import agentService from '../../services/agentService';
import runService from '../../services/runService';
import useRun from '../../hooks/useRun';
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
import StopIcon from '@mui/icons-material/Stop';
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
  
  // Data source: when :agentId is in the URL, the saved agent doc on
  // the server is the source of truth — context's hardcoded defaults
  // (inputSchema={inputText:"string"}, outputSchema={outputText:"string"})
  // would silently mask the user's actual schema if we fell back to
  // them. So when there's an agentId, we read only from agentData.
  // The creation-flow case (no agentId yet) still needs context.
  const inputSchema = agentId
    ? (agentData?.inputSchema ?? null)
    : (agentFlowContext.inputSchema);
  const tools = agentId
    ? (agentData?.tools ?? null)
    : (agentFlowContext.tools);
  const generatedCode = agentId
    ? (agentData?.code ?? null)
    : (agentFlowContext.generatedCode);
  const gofannonAgents = agentId
    ? (agentData?.gofannonAgents ?? [])
    : (agentFlowContext.gofannonAgents);

  console.log('[RunsScreen] Render - agentData:', !!agentData, 'generatedCode:', !!generatedCode, 'loadingAgent:', loadingAgent);

  // Always fetch the agent doc when :agentId is in the URL. The
  // server is the source of truth for an existing agent; context can
  // only mirror or be staler than the server. The previous gate
  // (`!agentFlowContext.generatedCode`) skipped the fetch whenever
  // context had any state — which produced silent staleness when the
  // user came to Runs after editing in the same session.
  useEffect(() => {
    const needsToFetch = !!agentId;
    console.log('[RunsScreen] agentId:', agentId, 'needsToFetch:', needsToFetch);
    
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
  }, [agentId]);

  const [formData, setFormData] = useState({});
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  // track the active run's id so we can render
  // a Stop button while it's in flight. Set from the first 'run_id'
  // SSE event; cleared in handleRun's finally.
  const [currentRunId, setCurrentRunId] = useState(null);
  // AbortController for the streaming fetch. Stop button uses this to
  // cut the client off immediately, then best-effort POSTs to
  // /runs/{id}/stop so the backend cancels server-side work via the
  // cancel-token check wired into data_store_service
  // and llm_service.
  const abortRef = React.useRef(null);
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
  // When arriving via /agent/<id>/runs/<runId> deep link, the run isn't
  // in local `runs` state (which only accumulates during this session),
  // so fetch it from the registry to pre-fill the form. null until
  // resolved; set to the fetched record on success or null on failure.
  const [fetchedRun, setFetchedRun] = useState(null);
  // Re-attach to an in-flight run when the URL carries a runId that was not
  // started in this session — page refresh, direct link, or a run picked from
  // the past-runs list. useRun does its own pre-flight auth check against
  // /runs/{run_id} (which goes through fetchInterceptor, so a 401 raises
  // AuthExpiryModal — EventSource cannot), then opens the SSE stream, which
  // replays the whole trace before going live.
  //
  // With backend persistent-runs shipped, `disconnected` means "your live view
  // is stale", NOT "your run died" — the run keeps going either way. That is
  // why the banner offers Reconnect rather than reporting a failure.
  const {
    events: streamedEvents,
    status: streamStatus,
    final: streamFinal,
    reconnect: reconnectStream,
  } = useRun(runId);
  // Local 'stop is in flight' flag flipped on Stop click and cleared
  // when the backend confirms the run has actually moved off
  // 'running'. Gives the button immediate visual feedback
  // ('Stopping...' disabled) rather than waiting for the next 5s
  // polling cycle to fetch a new status. Cleared on status change so
  // a stop that fails (e.g. orphaned worker) re-enables the button.
  const [stopRequested, setStopRequested] = useState(false);
  // Cross-session past runs for this agent. Sourced from the run
  // registry via GET /runs?agent_id=<id>. The local `runs` state above
  // only tracks the live in-session run; this state powers the
  // 'Past runs' list at the bottom of the page.
  const [historicalRuns, setHistoricalRuns] = useState([]);
  // Bump on run completion so the historical-runs fetch effect re-runs
  // and the newly-finished run appears in the list immediately.
  const [completionTick, setCompletionTick] = useState(0);

  // Read the declared output schema so we can send it to the agent runtime for
  // validation. Falls back to null when unavailable — the backend treats
  // a missing output_schema as "skip validation".
  // outputSchema reaches the backend's validate_output_against_schema()
  // and (for newly-generated agents) flows into the composer prompt.
  // Reading from context defaults here would tell the composer the
  // schema is {outputText: "string"} and produce agents that always
  // return that shape, ignoring what the user declared.
  const outputSchema = agentId
    ? (agentData?.outputSchema ?? null)
    : (agentFlowContext.outputSchema ?? null);

  // Initialize formData when inputSchema changes. If we have a
  // most-recent run (or are viewing a specific historical run via
  // Fetch the run-record when we landed here via a deep link and
  // don't already have a matching local run. The registry endpoint
  // (/runs/<id>) returns inputDict, which we use below to seed the
  // form. Failures degrade gracefully: form just shows defaults.
  // Memoize the local-match check so the effect below depends on
  // a stable boolean instead of the full runs array. The SSE trace
  // event handler updates runs as a new array reference on every
  // event (often 1000+ per agent run); with runs in the effect's
  // deps the effect refired on every event and produced a fetch
  // storm against GET /runs/<id>, which on a deep-linked ghost
  // runId showed up as hundreds of 404s per second in the api log.
  const hasLocalRunMatch = useMemo(
    () => runs.some((r) => r.run_id === runId),
    [runs, runId]
  );
  useEffect(() => {
    let cancelled = false;
    if (!runId) { setFetchedRun(null); return; }
    if (hasLocalRunMatch) { setFetchedRun(null); return; }
    (async () => {
      try {
        const data = await runService.getRun(runId);
        if (!cancelled) setFetchedRun(data || null);
      } catch (e) {
        if (!cancelled) {
          console.warn('RunsScreen: getRun failed:', e?.message || e);
          setFetchedRun(null);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [runId, hasLocalRunMatch, completionTick]);

  // Load the past-runs list from the run registry, filtered to this
  // agent. Refetches when completionTick bumps (after a streaming run
  // finishes), so freshly-completed runs land in the list without a
  // page reload. agentId-less runs (create-flow sandbox) keep the
  // pre-registry behavior: nothing in the historical list.
  useEffect(() => {
    let cancelled = false;
    if (!agentId) { setHistoricalRuns([]); return; }
    (async () => {
      try {
        const data = await runService.listRuns(agentId);
        if (cancelled) return;
        // Map server keys (runId/startedAt/status/inputDict) to the
        // local-state shape RunsHistoryList expects (run_id /
        // started_at / outcome / input). duration_ms is computed
        // from started/completed timestamps.
        const mapped = ((data && data.runs) || []).map((r) => ({
          run_id: r.runId,
          agent_name: r.agentName,
          started_at: r.startedAt,
          duration_ms: r.completedAt
            ? new Date(r.completedAt).getTime() - new Date(r.startedAt).getTime()
            : null,
          outcome: r.status,
          input: r.inputDict || {},
          error: r.error || null,
          // events is only on the full record; errorPreview falls back
          // to the top-level error string if events is empty/missing,
          // which is exactly what we want here.
          events: [],
        }));
        // Server returns newest-first; RunsHistoryList reverses before
        // rendering. Pass oldest-first so the reverse lands in the
        // order the user expects (newest at top).
        setHistoricalRuns(mapped.slice().reverse());
      } catch (e) {
        if (!cancelled) {
          console.warn('RunsScreen: listRuns failed:', e?.message || e);
          setHistoricalRuns([]);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [agentId, completionTick]);

  // While anything visible is still 'running', poll every 5s so a
  // natural completion (or a delayed stop taking effect once the
  // agent reaches its next structural boundary) surfaces in the UI
  // without a manual reload. The home page's RunningJobsModule
  // already does this for its own snapshot; the per-agent runs page
  // needs the same so users on this page get the same liveness.
  //
  // Auto-stops when nothing's running so we don't peg the API with
  // pointless requests on a long-idle page.
  useEffect(() => {
    const anyRunning = (
      (fetchedRun && fetchedRun.status === 'running') ||
      historicalRuns.some((r) => r.outcome === 'running')
    );
    if (!anyRunning) return;
    const id = setInterval(() => {
      setCompletionTick((n) => n + 1);
    }, 5000);
    return () => clearInterval(id);
  }, [fetchedRun, historicalRuns]);

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
    // For the deep-link case (runId in URL but no matching local run),
    // fetchedRun carries the registry record -- normalize its inputDict
    // to the local-state `input` shape so the rest of this block stays
    // simple.
    let sourceRun = null;
    if (runId) {
      sourceRun = runs.find((r) => r.run_id === runId) || null;
      if (!sourceRun && fetchedRun?.inputDict) {
        sourceRun = { input: fetchedRun.inputDict };
      }
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
    // fetchedRun is included so the form re-fills when an async getRun
    // resolves after the initial render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputSchema, runId, fetchedRun]);

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

      // Build per-model LLM settings map from ALL invokable models, not
      // just [0]. The backend looks up overrides by exact provider/model
      // when each tools.call_llm() fires, so a Sonnet call picks up
      // Sonnet's overrides while an Opus call picks up Opus's.
      // Same staleness reasoning as above: when there's a saved agent,
      // read from agentData only. The creation-flow case still uses
      // context.
      const invokableModels = agentId
        ? (agentData?.invokableModels ?? [])
        : (agentFlowContext.invokableModels ?? []);
      const perModel = {};
      for (const im of invokableModels) {
        if (!im?.provider || !im?.model || !im?.parameters) continue;
        const key = `${im.provider}/${im.model}`;
        // ?? (nullish coalescing) so a legitimately-zero stored value
        // doesn't silently get overridden by whichever variant happens
        // to come second.
        perModel[key] = {
          maxTokens: im.parameters.max_tokens ?? im.parameters.maxTokens,
          temperature: im.parameters.temperature,
          reasoningEffort: im.parameters.reasoning_effort ?? im.parameters.reasoningEffort,
        };
      }
      const llmSettings = Object.keys(perModel).length > 0
        ? { perModel }
        : undefined;

      // friendlyName: same treatment — server-of-truth when agentId is set.
      const friendlyName = agentId
        ? (agentData?.friendlyName || agentData?.name || 'sandbox_agent')
        : (agentFlowContext.friendlyName || 'sandbox_agent');

      // Stream events into the in-flight 'running' run entry as they
      // arrive. The bulk handler below still runs once we have the
      // final response — it sets the run's outcome and any leftover
      // fields (ops_log, schema warnings).
      const onTraceEvent = (event) => {
        // Never let a per-event render error kill the stream. A malformed
        // or unexpected-shape event must log-and-continue, not tear down
        // the ReadableStream reader -- that closes the SSE, which the
        // backend reads as a client disconnect. Historically a single
        // TypeError here killed 61 of 64 batches mid-flight.
        //
        // NOTE: this try/catch covers code that runs SYNCHRONOUSLY in the
        // handler. The setRuns updater below is a functional update, which
        // React invokes later during the render phase -- an exception in
        // there is raised outside this block and is NOT caught here. That
        // updater has its own guard for exactly that reason.
        try {
        // capture runId from the first 'run_id' event
        // so the Stop button becomes enabled.
        if (event && event.type === 'run_id' && event.data && event.data.runId) {
          setCurrentRunId(event.data.runId);
          // Align the URL with the just-started run so:
          // - the page now visibly represents the run you're streaming
          // - handleStop targets the run shown in the URL (Stop button
          //   was ambiguous before: it stopped currentRunId regardless
          //   of which run the URL pointed at, so clicking Run while
          //   deep-linked to an older run and then clicking Stop would
          //   stop the NEW run, leaving the displayed OLD one alone
          //   and looking 'unstoppable')
          // - reload preserves the run you were watching
          //
          // Skip the navigate if the URL already matches (e.g.
          // we navigated via past-runs to a running run and that
          // triggered a streaming continuation). Avoids a no-op
          // history entry.
          if (runId !== event.data.runId) {
            navigate(`/agent/${agentId}/runs/${event.data.runId}`);
          }
          // Trigger a historicalRuns refetch so the just-registered
          // run shows up in the past-runs section immediately. The
          // backend has the record by the time this event fires
          // (new_record completes before the run_id event is sent).
          setCompletionTick((n) => n + 1);
          return;
        }
        setRuns((prev) => {
          // Guarded independently of the outer try/catch: React runs this
          // closure during render, not at setRuns() call time, so a throw
          // in here escapes the handler's try block entirely. An uncaught
          // throw during render unmounts the tree and takes the SSE reader
          // with it -- the exact failure this whole patch exists to stop.
          try {
            const next = [...prev];
            const idx = next.length - 1;
            // `!next[idx]` added: the original dereferenced .outcome on a
            // possibly-undefined element.
            if (idx < 0 || !next[idx] || next[idx].outcome !== 'running') return prev;
            next[idx] = {
              ...next[idx],
              events: [...(next[idx].events || []), event],
            };
            return next;
          } catch {
            return prev;
          }
        });
        } catch (renderErr) {
          // Log the failing event so the underlying bug stays traceable,
          // but do NOT rethrow. One event's UI update is lost; the stream
          // and the run continue.
          //
          // This is deliberately a silent-degradation trade: watch
          // /log/client for these. A boundary nobody monitors is a
          // bug-hiding machine.
          try {
            observabilityService.logError(renderErr, {
              context: 'onTraceEvent',
              eventType: event?.type ?? 'unknown',
              eventPreview: (() => {
                try { return JSON.stringify(event).slice(0, 500); }
                catch { return '<unserialisable>'; }
              })(),
            });
          } catch {
            // Even the logger failed. Nothing to do -- keeping the stream
            // alive outranks recording why we couldn't.
          }
        }
      };

      // AbortController for the streaming fetch.
      // Stored in the ref so handleStop can call .abort() on it.
      const abort = new AbortController();
      abortRef.current = abort;
      const response = await agentService.runCodeInSandboxStreaming(
        generatedCode, castInput, tools, gofannonAgents, llmSettings, outputSchema, friendlyName,
        onTraceEvent,
        agentData?.envVars,
        abort.signal,
        agentId,
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
        // Trigger historical-runs refetch so this run appears in the
        // past-runs list at the bottom of the page.
        setCompletionTick((n) => n + 1);
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
      // distinguish a user-initiated stop from a real
      // transport error. AbortController.abort() makes the streaming fetch's
      // body stream throw with name='AbortError' or a 'BodyStreamBuffer was
      // aborted' message depending on browser. Neither is a failure -- the
      // user clicked Stop. Mark the run as 'stopped' and skip the red error
      // banner / observability noise.
      const isAbort = err && (err.name === 'AbortError' || /abort/i.test(err.message || ''));
      if (isAbort) {
        setCompletionTick((n) => n + 1);
        setRuns((prev) => {
          const next = [...prev];
          if (next.length > 0 && next[next.length - 1].outcome === 'running') {
            const r = next[next.length - 1];
            next[next.length - 1] = {
              ...r,
              outcome: 'stopped',
              duration_ms: Date.now() - r._started_ms,
              events: [
                ...(r.events || []),
                {
                  type: 'stopped',
                  ts: new Date().toISOString(),
                  agent_name: r.agent_name || 'unknown',
                  depth: 0,
                  message: 'Run stopped by user. Backend cancellation may take a moment to propagate to the next structural boundary.',
                  source: 'system',
                },
              ],
            };
          }
          return next;
        });
        return;
      }

      setError(err.message || 'An unexpected error occurred.');
      observabilityService.logError(err, { context: 'Agent Run Execution' });
      // Mark the in-flight run as errored so the Progress Log doesn't
      // spin forever when the request itself failed (network, 5xx,
      // etc — the backend never got far enough to emit a trace).
      setCompletionTick((n) => n + 1);
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
      setCurrentRunId(null);
      abortRef.current = null;
    }
  };

  // stop a run in flight. Client-side abort frees
  // the user from the running view immediately; backend POST sets the
  // cancel token, which is wired into data_store_service
  // and llm_service so the agent's next structural boundary raises.
  const handleStop = async () => {
    // Optimistic UX: flip the button to 'Stopping...' disabled state
    // immediately, well before the backend has actually stopped the
    // run and the next poll has fetched the new status. The status-
    // change effect below clears the flag once the registry reports
    // the run as no longer 'running', so a stop that fails (orphaned
    // worker, etc.) re-enables the button rather than locking it.
    setStopRequested(true);
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch { /* ignore */ }
    }
    // Fall back to the URL-param runId when this tab didn't start the
    // run (deep-link revisit to a long-running agent). The backend
    // doesn't care who initiates the stop -- the cancel token is
    // looked up in the registry by runId.
    const stopTarget = currentRunId || runId;
    if (stopTarget) {
      try {
        await fetch(`/runs/${encodeURIComponent(stopTarget)}/stop`, {
          method: 'POST',
          credentials: 'include',
        });
        // Refresh the fetchedRun + historicalRuns so the status chip
        // flips to 'stopped' once the backend confirms.
        setCompletionTick((n) => n + 1);
      } catch (e) {
        console.warn('Stop request failed:', e);
        // Network error -- the backend may or may not have received
        // the request. Re-enable the button so the user can retry;
        // if the backend did succeed, the next poll will flip the
        // status and the effect below will re-disable.
        setStopRequested(false);
      }
    }
  };

  // Clear the stopRequested flag once the registry reports the run
  // as no longer 'running'. This handles both the happy path
  // (status flips to 'stopped' or 'success'/'error') and the
  // recover-from-failed-stop case where the agent kept running and
  // a later state change is observed.
  React.useEffect(() => {
    if (stopRequested && fetchedRun && fetchedRun.status !== 'running') {
      setStopRequested(false);
    }
  }, [stopRequested, fetchedRun]);

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

  // Render the agent's output as one labeled panel per top-level key,
  // mirroring how inputs are rendered above. Two driver heuristics:
  //   1. If outputSchema is declared with multiple keys, iterate over
  //      schema keys so the user sees a panel for every expected key
  //      even if the agent omitted some (helps diagnose missing-key bugs).
  //   2. Fall back to iterating over actual output keys so we still
  //      render coherently when no schema is declared, or when the
  //      output has extra keys the schema didn't expect.
  // Either way, non-string values stringify as pretty JSON; strings
  // render as-is so they're readable rather than quoted.
  const renderOutput = (out, schema) => {
    if (out === null || out === undefined) return null;
    // Single-string-blob fallback: if output is not an object (a bare
    // string or number got returned), render it as a single panel
    // labeled "output" — the old behavior for non-dict returns.
    if (typeof out !== 'object' || Array.isArray(out)) {
      return (
        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'lightgreen', margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
            {typeof out === 'string' ? out : JSON.stringify(out, null, 2)}
          </pre>
        </Paper>
      );
    }
    // Keys to render: prefer the schema's declared order if it has 2+ keys
    // so we render a slot for each declared key even when the agent omits
    // some. Single-key schemas (the default {outputText:"string"} case)
    // fall through to using the output's actual keys, since there's nothing
    // to highlight by anticipating one key that's almost certainly there.
    const schemaKeys = schema ? Object.keys(schema) : [];
    const outKeys = Object.keys(out);
    const keys = schemaKeys.length >= 2 ? schemaKeys : outKeys;
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {keys.map((key) => {
          const value = out[key];
          const isMissing = !(key in out);
          const declaredType = schema?.[key];
          const label = declaredType ? `${key} (${declaredType})` : key;
          let body;
          if (isMissing) {
            body = <em style={{ color: '#999' }}>not returned by agent</em>;
          } else if (value === null || value === undefined) {
            body = <em style={{ color: '#999' }}>{String(value)}</em>;
          } else if (typeof value === 'string') {
            body = value;
          } else {
            body = JSON.stringify(value, null, 2);
          }
          return (
            <Box key={key}>
              <Typography variant="subtitle2" sx={{ mb: 0.5, color: 'text.secondary' }}>
                {label}
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'lightgreen', margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {body}
                </pre>
              </Paper>
            </Box>
          );
        })}
        {/* Extra keys the agent returned that weren't declared in schema.
            Surfaced separately so they're visible but don't dilute the
            primary view; helps diagnose agents drifting from their declared
            shape. */}
        {schemaKeys.length >= 2 && outKeys.filter(k => !schemaKeys.includes(k)).length > 0 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 0.5, color: 'warning.main' }}>
              Extra keys not in schema
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', overflowX: 'auto', maxHeight: '300px', overflowY: 'auto' }}>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'orange', margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
                {JSON.stringify(
                  Object.fromEntries(outKeys.filter(k => !schemaKeys.includes(k)).map(k => [k, out[k]])),
                  null, 2
                )}
              </pre>
            </Paper>
          </Box>
        )}
      </Box>
    );
  };

  // A streamed run reaching a terminal state carries the same payload the
  // in-session handleRun path sets directly. Mirror it so a deep-linked or
  // refreshed run populates the output panel rather than showing an empty one.
  useEffect(() => {
    if (!streamFinal) return;
    if (streamFinal.result !== undefined && streamFinal.result !== null) {
      setOutput(streamFinal.result);
    }
    if (streamFinal.error) setError(streamFinal.error);
    if (streamFinal.schemaWarnings?.length) setSchemaWarnings(streamFinal.schemaWarnings);
    if (streamFinal.opsLog?.length) setOpsLog(streamFinal.opsLog);
  }, [streamFinal]);

  // RunProgressLog takes an array of run objects, not a flat event list, so
  // wrap the streamed events in one synthetic record when local `runs` is
  // empty. `runs` is only populated by handleRun during this session — the
  // deep-link and refresh cases have nothing in it, which is exactly when the
  // stream is the only source of truth. When both exist, handleRun wins: it is
  // the run the user just started and its record carries timing the stream
  // does not.
  const displayRuns = useMemo(() => {
    if (runs.length > 0) return runs;
    if (streamedEvents.length === 0) return runs;
    const terminal = ['success', 'error', 'stopped'];
    return [{
      started_at: fetchedRun?.startedAt ?? fetchedRun?.started_at ?? null,
      duration_ms: null,
      outcome: terminal.includes(streamStatus) ? streamStatus : 'running',
      events: streamedEvents,
    }];
  }, [runs, streamedEvents, streamStatus, fetchedRun]);

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
          // Always go back in browser history. The previous logic
          // special-cased the runId case by navigating to
          // /agent/<id>/runs (no runId), which created a duplicate-
          // looking page and a navigation loop -- back from there
          // went forward in history to the same /<id>/runs/<runId>
          // we'd just left. navigate(-1) restores the natural
          // 'return to where I came from' behavior; users opening
          // the URL in a fresh tab can use the app's top nav to
          // reach home.
          onClick={() => navigate(-1)}
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
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Button
              variant="contained"
              onClick={async () => { await handleRun(); }}
              disabled={isLoading || !generatedCode}
              startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
            >
              {isLoading ? 'Running...' : 'Run Agent'}
            </Button>
            {/* Stop button visible when either (a) we have an in-flight
                run in this tab, or (b) we're viewing a deep-linked run
                whose registry status is still 'running'. Disabled only
                when there's nothing to identify the run by. */}
            {(isLoading || (fetchedRun && fetchedRun.status === 'running')) && (
              <Button
                variant="outlined"
                color="error"
                onClick={handleStop}
                disabled={stopRequested || (!currentRunId && !runId)}
                startIcon={<StopIcon />}
              >
                {stopRequested ? 'Stopping…' : 'Stop'}
              </Button>
            )}
          </Box>
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
          {renderOutput(output, outputSchema)}
        </Box>
      )}

      {/* Past runs list. Sourced from the run registry when this is
          a saved agent (agentId set); otherwise falls back to the
          session's in-memory runs[]. Visible whether or not we're
          viewing a specific runId -- the user can pivot between
          historical runs from here. Hidden only when there's nothing
          to show. */}
      {((agentId ? historicalRuns : runs).length > 0) && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>Past runs</Typography>
          <RunsHistoryList
            runs={agentId ? historicalRuns : runs}
            inputSchema={inputSchema}
            onOpen={(rId) => {
              // No-op when the clicked row is the run we're already
              // viewing -- otherwise repeated clicks on the same row
              // pile up identical history entries and the back arrow
              // has to be pressed once per click to escape.
              const target = `/agent/${agentId}/runs/${rId}`;
              if (target !== window.location.pathname) {
                navigate(target);
              }
            }}
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
        {streamStatus === 'disconnected' && (
          <Alert
            severity="warning"
            action={
              <Button color="inherit" size="small" onClick={reconnectStream}>
                Reconnect
              </Button>
            }
          >
            <AlertTitle>Connection to run lost</AlertTitle>
            The run is still going on the server — losing this stream does not
            stop it. Reconnect to replay the trace and catch up on anything that
            happened while you were disconnected.
          </Alert>
        )}
        {streamStatus === 'not_found' && (
          <Alert severity="info">
            No run with that ID exists, or it belongs to someone else.
          </Alert>
        )}
        <RunProgressLog runs={displayRuns} />
        <RunDataPanel opsLog={opsLog} />
      </Box>
    </Box>
  );
};

export default RunsScreen;