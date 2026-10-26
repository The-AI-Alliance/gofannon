// webapp/packages/webui/src/pages/RunsPage.jsx
//
// All runs index — cross-agent table view of every run currently
// known to the in-memory RunRegistry. Linked from the
// home page Running Jobs module's "View all" button.
//
// Polls GET /runs every 5s like the home page module does, but
// renders a fuller table with status filter chips, started/completed
// timestamps, and a runtime column. Layout, header bar, refresh
// button, empty-state, and table styling follow the conventions
// established in DataStoresPage / SavedAgentsPage / DemoAppsPage.

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, CircularProgress, IconButton, Stack, Tooltip,
  Button, Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import { listRuns } from '../services/runService';
import { parseServerDate, formatTimeAgo } from '../utils/serverTime';

const POLL_INTERVAL_MS = 5000;

const STATUS_CHIP = {
  running: { label: 'running', color: 'info' },
  success: { label: 'success', color: 'success' },
  error:   { label: 'error',   color: 'error' },
  stopped: { label: 'stopped', color: 'default' },
};

const FILTERS = [
  { id: 'all',     label: 'All' },
  { id: 'running', label: 'Running' },
  { id: 'success', label: 'Success' },
  { id: 'error',   label: 'Error' },
  { id: 'stopped', label: 'Stopped' },
];

// Delegates to serverTime.formatTimeAgo, which treats an offset-less
// timestamp as UTC. The API emits NAIVE UTC, so a raw `new Date(iso)` read
// it as local time and every age was wrong by the viewer's UTC offset.
const relativeTime = formatTimeAgo;

function durationOf(run) {
  if (!run.startedAt) return '';
  const completed = parseServerDate(run.completedAt);
  const started = parseServerDate(run.startedAt);
  if (!started) return '';
  const end = completed ? completed.getTime() : Date.now();
  const ms = end - started.getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rs = s % 60;
  return `${m}m ${rs}s`;
}

const RunsPage = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [refreshNonce, setRefreshNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchOnce = async () => {
      try {
        const data = await listRuns();
        if (cancelled) return;
        setRuns((data && data.runs) || []);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          console.warn('RunsPage: unable to fetch /runs:', e.message || e);
          setError(e.message || String(e));
          setRuns([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchOnce();
    const id = setInterval(fetchOnce, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [refreshNonce]);

  const filtered = useMemo(() => {
    if (filter === 'all') return runs;
    return runs.filter((r) => r.status === filter);
  }, [runs, filter]);

  // Counts per status for the filter chips.
  const counts = useMemo(() => {
    const c = { all: runs.length };
    for (const f of FILTERS) {
      if (f.id === 'all') continue;
      c[f.id] = runs.filter((r) => r.status === f.id).length;
    }
    return c;
  }, [runs]);

  const load = () => setRefreshNonce(n => n + 1);

  return (
    <Box sx={{ p: 3, maxWidth: 1400, margin: '0 auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton size="small" onClick={() => navigate('/')} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 600, flexGrow: 1 }}>
          All Runs
        </Typography>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Box>

      {/* Status filter chips — page-specific, no existing convention to match. */}
      <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
        {FILTERS.map((f) => (
          <Chip
            key={f.id}
            label={`${f.label} (${counts[f.id] ?? 0})`}
            size="small"
            color={filter === f.id ? 'primary' : 'default'}
            variant={filter === f.id ? 'filled' : 'outlined'}
            onClick={() => setFilter(f.id)}
            clickable
          />
        ))}
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ overflow: 'hidden' }}>
        <TableContainer>
          {loading && runs.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : filtered.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <PendingActionsIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
              <Typography color="text.secondary" variant="body2">
                {filter === 'all'
                  ? 'No runs yet. Kick off an agent to see runs appear here.'
                  : `No ${filter} runs. Try a different filter.`}
              </Typography>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#fafafa' }}>
                  <TableCell>Status</TableCell>
                  <TableCell>Agent</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Run ID</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((run) => {
                  const cfg = STATUS_CHIP[run.status] || { label: run.status, color: 'default' };
                  // Deep-link to the per-agent runs page when agentId is
                  // available. Runs without one (sandbox / pre-field) get
                  // a row with no click behavior.
                  const linkTo = run.agentId ? `/agent/${run.agentId}/runs/${run.runId}` : null;
                  return (
                    <TableRow
                      key={run.runId}
                      hover
                      sx={linkTo ? { cursor: 'pointer' } : undefined}
                      onClick={linkTo ? () => navigate(linkTo) : undefined}
                    >
                      <TableCell>
                        <Chip size="small" label={cfg.label} color={cfg.color} />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {run.agentName}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Tooltip title={run.startedAt || ''} arrow>
                          <Typography variant="body2" color="text.secondary">
                            {relativeTime(run.startedAt)}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {durationOf(run)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary' }}
                        >
                          {run.runId}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default RunsPage;