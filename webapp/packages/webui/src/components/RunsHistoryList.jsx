// RunsHistoryList.jsx
//
// Renders the list of past runs below the input form on the runs page.
// Each row: status icon + relative time + duration + a 1-line preview
// of the first few input fields + (if errored) the exception type
// inline + a re-run button on the right.
//
// Two callbacks:
//   onOpen(run_id)  — clicked the row body. The page navigates to
//                     /agent/:agentId/runs/:run_id to view this run.
//   onRerun(input)  — clicked the ↻ button. The page fills the form
//                     with this run's input but doesn't navigate; user
//                     clicks Run when ready.
//
// Reads from the in-memory runs[] today; once the run registry lands,
// the parent will source from GET /runs?agent_id=X and pass the same
// shape down. The component itself doesn't care where the array
// comes from.

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Tooltip,
  IconButton,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import StopCircleIcon from '@mui/icons-material/StopCircle';
import ReplayIcon from '@mui/icons-material/Replay';
import PropTypes from 'prop-types';

// Relative-time formatting. Cheap, no dep on a date library.
const formatRelative = (iso) => {
  if (!iso) return '';
  const ts = new Date(iso).getTime();
  if (!Number.isFinite(ts)) return '';
  const delta = Math.max(0, Date.now() - ts);
  const sec = Math.floor(delta / 1000);
  if (sec < 5) return 'just now';
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} day${day === 1 ? '' : 's'} ago`;
  return new Date(iso).toLocaleDateString();
};

const formatDuration = (ms) => {
  if (ms == null || !Number.isFinite(ms)) return '';
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const m = Math.floor(s / 60);
  const rs = Math.round(s % 60);
  return `${m}m ${rs}s`;
};

// First N input fields rendered as `key=value, key=value, ...`,
// truncated. Mirrors what the user typed in the form, in the order
// the schema declared. Long values are clipped with `…`.
const previewInput = (input, inputSchema) => {
  if (!input || !inputSchema) return '';
  const keys = Object.keys(inputSchema).slice(0, 3);
  if (!keys.length) return '';
  const parts = keys.map((k) => {
    let v = input[k];
    if (v == null) v = '';
    let s;
    if (typeof v === 'object') {
      try { s = JSON.stringify(v); } catch { s = '<obj>'; }
    } else {
      s = String(v);
    }
    if (s.length > 30) s = s.slice(0, 30) + '…';
    return `${k}=${s}`;
  });
  return parts.join(', ');
};

// Given a run with outcome=error, find the most informative error
// message to surface in the row. Prefers an explicit error event
// from the trace; falls back to top-level error string if any.
const errorPreview = (run) => {
  if (run.outcome !== 'error') return null;
  const errEvent = (run.events || []).find((e) => e.type === 'error');
  if (errEvent) {
    const t = errEvent.exception_type || 'Error';
    const m = errEvent.message ? `: ${errEvent.message}` : '';
    return `${t}${m}`.slice(0, 60);
  }
  if (run.error) return String(run.error).slice(0, 60);
  return 'Error';
};

const StatusIcon = ({ outcome }) => {
  const sx = { fontSize: 18, flexShrink: 0 };
  switch (outcome) {
    case 'success':
      return <CheckCircleIcon sx={{ ...sx, color: 'success.main' }} />;
    case 'error':
      return <ErrorOutlineIcon sx={{ ...sx, color: 'error.main' }} />;
    case 'running':
      return <HourglassEmptyIcon sx={{ ...sx, color: 'text.secondary' }} />;
    case 'stopped':
      return <StopCircleIcon sx={{ ...sx, color: 'text.secondary' }} />;
    default:
      return <HourglassEmptyIcon sx={{ ...sx, color: 'text.secondary' }} />;
  }
};

StatusIcon.propTypes = { outcome: PropTypes.string };

const RunsHistoryList = ({ runs, inputSchema, onOpen, onRerun }) => {
  // Reverse so newest is at the top.
  const ordered = [...(runs || [])].reverse();

  return (
    <Paper variant="outlined">
      {ordered.map((run, idx) => {
        const errPrev = errorPreview(run);
        const inputPrev = previewInput(run.input, inputSchema);
        return (
          <Box
            key={run.run_id || idx}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              px: 1.5,
              py: 1,
              borderBottom: idx < ordered.length - 1 ? 1 : 0,
              borderColor: 'divider',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              ...(run.outcome === 'error' && {
                borderLeft: 3,
                borderLeftColor: 'error.main',
              }),
            }}
            onClick={() => onOpen(run.run_id)}
          >
            <StatusIcon outcome={run.outcome} />
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {formatRelative(run.started_at)}
                </Typography>
                {run.outcome !== 'running' && run.duration_ms != null && (
                  <Typography variant="caption" color="text.secondary">
                    · {formatDuration(run.duration_ms)}
                  </Typography>
                )}
                {run.outcome === 'running' && (
                  <Typography variant="caption" color="text.secondary">
                    · running
                  </Typography>
                )}
                {errPrev && (
                  <Typography variant="caption" color="error.main"
                    sx={{ overflow: 'hidden', textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap', fontFamily: 'monospace' }}
                    title={errPrev}>
                    · {errPrev}
                  </Typography>
                )}
              </Box>
              {inputPrev && (
                <Typography variant="caption" color="text.secondary"
                  sx={{ display: 'block', overflow: 'hidden',
                        textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        fontFamily: 'monospace' }}
                  title={inputPrev}>
                  {inputPrev}
                </Typography>
              )}
            </Box>
            <Tooltip title="Re-run with these inputs" arrow>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onRerun(run.input);
                }}
                disabled={run.outcome === 'running'}
              >
                <ReplayIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          </Box>
        );
      })}
    </Paper>
  );
};

RunsHistoryList.propTypes = {
  runs: PropTypes.array.isRequired,
  inputSchema: PropTypes.object,
  onOpen: PropTypes.func.isRequired,
  onRerun: PropTypes.func.isRequired,
};

export default RunsHistoryList;
