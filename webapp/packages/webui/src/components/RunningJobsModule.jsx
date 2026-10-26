// webapp/packages/webui/src/components/RunningJobsModule.jsx
//
// cross-agent view of recent and current runs on the home page.
// Polls GET /runs every 5s and renders each non-terminal run plus the
// most recent N completed runs. Status chip color encodes terminal
// state.
//
// Deliberately uses polling rather than per-row SSE — this is an
// at-a-glance overview, and 30+ concurrent EventSources for users
// with many agents would be wasteful.
//
// Run control (added alongside backend persistent-runs):
//   - Stop      — cooperative cancel via POST /runs/{id}/stop. The run
//                 unwinds at its next structural boundary.
//   - Clear     — POST /runs/{id}/force-complete, for rows stuck in
//                 'running' whose owning worker died. /stop cannot help
//                 those: it flips a cancel token nothing is left to read.
//
// Both are behind a confirmation dialog. Stop is destructive (an hour of
// pipeline work) and Clear writes a terminal status the pipeline never
// reported, so neither should be a single misclick.

import React, { useCallback, useEffect, useState } from 'react';
import {
  Paper, Box, Typography, Chip, CircularProgress, Stack, Link, Button,
  IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogContentText,
  DialogActions, Snackbar, Alert,
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import StopCircleIcon from '@mui/icons-material/StopCircle';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import { listRuns, stopRun, forceCompleteRun } from '../services/runService';
import { ageMs, formatTimeAgo } from '../utils/serverTime';

const POLL_INTERVAL_MS = 5000;
const MAX_COMPLETED_SHOWN = 5;

// A run older than this with status still 'running' is *probably*
// orphaned, so we surface the Clear affordance. Advisory only — the
// server does the real staleness check against last trace event, which
// this widget cannot see from the summary payload.
const CLEAR_AFFORDANCE_AFTER_MS = 15 * 60 * 1000;

const STATUS_CHIP = {
  running: { label: 'running', color: 'info' },
  success: { label: 'success', color: 'success' },
  error:   { label: 'error',   color: 'error' },
  stopped: { label: 'stopped', color: 'default' },
};

export default function RunningJobsModule() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  // { mode: 'stop' | 'clear', run, force: bool } | null
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchOnce = useCallback(async () => {
    try {
      const data = await listRuns();
      // Defensive: data may be null/undefined if the endpoint returned
      // something we couldn't parse (e.g. vite SPA fallback returning
      // index.html when the api is briefly unreachable). Treat as empty
      // rather than surfacing a parse error -- this widget is
      // at-a-glance and empty is the right signal when nothing's there.
      setRuns((data && data.runs) || []);
    } catch (e) {
      console.warn('RunningJobsModule: unable to fetch /runs:', e.message || e);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => { if (!cancelled) await fetchOnce(); };
    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [fetchOnce]);

  const handleConfirm = async () => {
    if (!confirm) return;
    const { mode, run, force } = confirm;
    setBusy(true);
    try {
      if (mode === 'stop') {
        await stopRun(run.runId);
        setToast({ severity: 'success', msg: `Stop requested for ${run.agentName}.` });
        setConfirm(null);
      } else {
        const res = await forceCompleteRun(run.runId, { force: !!force });
        setToast({
          severity: 'success',
          msg: res.changed
            ? `Cleared ${run.agentName}.`
            : `${run.agentName} was already complete.`,
        });
        setConfirm(null);
      }
      await fetchOnce();
    } catch (e) {
      if (e.code === 'RUN_LOOKS_ACTIVE') {
        // Server says the run emitted an event recently. Escalate to a
        // second confirmation rather than silently forcing -- the whole
        // point of the 409 is that this is probably a misclick.
        setConfirm({ ...confirm, force: true, serverWarning: e.message });
      } else {
        setToast({ severity: 'error', msg: e.message || 'Request failed.' });
        setConfirm(null);
      }
    } finally {
      setBusy(false);
    }
  };

  const running = runs.filter((r) => r.status === 'running');
  const recent  = runs.filter((r) => r.status !== 'running').slice(0, MAX_COMPLETED_SHOWN);

  return (
    <Paper sx={{ overflow: 'hidden' }}>
      {/* Header matches the Data Stores / Agents pattern on the home
          page: icon + title + count chip on the left, View all on
          the right. */}
      <Box sx={{
        p: 2,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #e4e4e7',
        bgcolor: '#fafafa',
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PendingActionsIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>Runs</Typography>
          <Chip label={`All (${runs.length})`} size="small" sx={{ height: 22, fontSize: '0.72rem' }} />
          {loading && <CircularProgress size={14} sx={{ ml: 1 }} />}
        </Box>
        <Button
          variant="outlined"
          size="small"
          onClick={() => navigate('/jobs')}
          disabled={runs.length === 0}
        >
          View all
        </Button>
      </Box>

      <Box sx={{ p: 2 }}>
        {!loading && running.length === 0 && recent.length === 0 && (
          <Box sx={{ py: 3, textAlign: 'center' }}>
            <Typography color="text.secondary" variant="body2">
              No runs yet
            </Typography>
            <Typography color="text.secondary" variant="caption" sx={{ display: 'block', mt: 0.5 }}>
              Kick off an agent to see live status here.
            </Typography>
          </Box>
        )}

        {running.length > 0 && (
          <Box sx={{ mb: 1.5 }}>
            <Typography variant="caption" color="text.secondary">In flight</Typography>
            <Stack spacing={0.5} sx={{ mt: 0.5 }}>
              {running.map((r) => (
                <RunRow
                  key={r.runId}
                  run={r}
                  onStop={() => setConfirm({ mode: 'stop', run: r })}
                  onClear={() => setConfirm({ mode: 'clear', run: r })}
                />
              ))}
            </Stack>
          </Box>
        )}

        {recent.length > 0 && (
          <Box>
            <Typography variant="caption" color="text.secondary">Recent</Typography>
            <Stack spacing={0.5} sx={{ mt: 0.5 }}>
              {recent.map((r) => <RunRow key={r.runId} run={r} />)}
            </Stack>
          </Box>
        )}
      </Box>

      <ConfirmDialog
        confirm={confirm}
        busy={busy}
        onCancel={() => setConfirm(null)}
        onConfirm={handleConfirm}
      />

      <Snackbar
        open={!!toast}
        autoHideDuration={5000}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {toast ? (
          <Alert severity={toast.severity} onClose={() => setToast(null)} sx={{ width: '100%' }}>
            {toast.msg}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Paper>
  );
}

function ConfirmDialog({ confirm, busy, onCancel, onConfirm }) {
  if (!confirm) return null;
  const { mode, run, force, serverWarning } = confirm;
  const stopping = mode === 'stop';

  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>
        {stopping ? 'Stop this run?' : force ? 'Clear anyway?' : 'Clear this run?'}
      </DialogTitle>
      <DialogContent>
        {serverWarning && (
          <Alert severity="warning" sx={{ mb: 2 }}>{serverWarning}</Alert>
        )}
        <DialogContentText component="div">
          <Box sx={{ mb: 1.5, fontWeight: 600 }}>{run.agentName}</Box>
          {stopping ? (
            <>
              The run will unwind at its next checkpoint — an in-flight model
              call finishes first, so this is not instant. Work already
              completed and pushed is kept; work in progress is lost.
              <Box sx={{ mt: 1.5 }}>This cannot be undone.</Box>
            </>
          ) : force ? (
            <>
              The server thinks this run is still alive. Clearing it now marks
              it <strong>error</strong> and, if the pipeline is still running on
              this worker, cancels it.
              <Box sx={{ mt: 1.5 }}>
                If you only meant to stop a healthy run, cancel this and use
                Stop instead.
              </Box>
            </>
          ) : (
            <>
              This marks the run <strong>error</strong> and removes it from the
              in-flight list. Use this for rows stuck on 'running' whose worker
              died — Stop cannot clear those, because nothing is left to receive
              the cancel.
              <Box sx={{ mt: 1.5 }}>
                It does not stop any work that is genuinely still running, and
                the status it writes is a guess: the pipeline never reported
                one.
              </Box>
            </>
          )}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={busy}>Cancel</Button>
        <Button
          onClick={onConfirm}
          color="error"
          variant="contained"
          disabled={busy}
          startIcon={busy ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {stopping ? 'Stop run' : force ? 'Clear anyway' : 'Clear run'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function RunRow({ run, onStop, onClear }) {
  const cfg = STATUS_CHIP[run.status] || { label: run.status, color: 'default' };
  // Deep-link to the per-agent runs page when we have an agentId. Runs
  // that predate the agent_id field on RunRecord (or sandbox runs from
  // the create-flow before a save) render the name as plain text rather
  // than linking to a route that wouldn't resolve.
  const linkTo = run.agentId ? `/agent/${run.agentId}/runs/${run.runId}` : null;

  // ageMs() from serverTime, not new Date(): the API emits NAIVE UTC, and a
  // raw parse reads it as local time -- off by the viewer's UTC offset, which
  // is what produced '-25176s ago' on the home page.
  const age = ageMs(run.startedAt);
  const looksOrphaned =
    run.status === 'running' && age !== null && age > CLEAR_AFFORDANCE_AFTER_MS;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, fontSize: '0.875rem' }}>
      <Chip size="small" label={cfg.label} color={cfg.color} />
      {linkTo ? (
        <Link component={RouterLink} to={linkTo} sx={{ flex: 1, textDecoration: 'none' }}>
          {run.agentName}
        </Link>
      ) : (
        <Typography sx={{ flex: 1, fontSize: '0.875rem', color: 'text.secondary' }}>
          {run.agentName}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary">
        {formatTimeAgo(run.startedAt)}
      </Typography>
      {onStop && (
        <Tooltip title="Stop run">
          <IconButton size="small" onClick={onStop} aria-label={`Stop ${run.agentName}`}>
            <StopCircleIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
      {onClear && looksOrphaned && (
        <Tooltip title="Clear stuck run (worker likely died)">
          <IconButton size="small" onClick={onClear} aria-label={`Clear ${run.agentName}`}>
            <DeleteSweepIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Box>
  );
}