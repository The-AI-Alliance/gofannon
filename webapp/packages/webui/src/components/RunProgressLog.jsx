// webapp/packages/webui/src/components/SandboxProgressLog.jsx
//
// Progress Log accordion for the sandbox: shows a chronological,
// per-agent-grouped trace of recent runs with errors highlighted and
// stack traces clickable into a side sheet.
//
// Run history is in-memory only (current SandboxScreen mount), per the
// design discussion — refreshing the page wipes it. If we want
// persistence later, the upgrade is to write trace docs to a backend
// collection and query on mount; nothing about this component's shape
// would change.

import React, { useState, useMemo } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Chip,
  Drawer,
  IconButton,
  Stack,
  Typography,
  Divider,
  Button,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CloseIcon from '@mui/icons-material/Close';
import PropTypes from 'prop-types';

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

const formatTime = (iso) => {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour12: false });
  } catch {
    return iso;
  }
};

const formatDuration = (ms) => {
  if (ms == null) return '';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const min = Math.floor(ms / 60000);
  const s = Math.round((ms % 60000) / 1000);
  return `${min}m ${s}s`;
};

const eventColor = (theme, ev) => {
  if (ev.type === 'error') return theme.palette.error.main;
  if (ev.type === 'agent_start' || ev.type === 'agent_end') return theme.palette.primary.main;
  if (ev.type === 'llm_call') return theme.palette.info.main;
  if (ev.type === 'data_store') return theme.palette.success.main;
  return theme.palette.text.secondary;
};

// One-line summary for an event row. Stack traces and full payloads
// expand below or open in the side sheet.
const eventSummary = (ev) => {
  switch (ev.type) {
    case 'agent_start':
      return ev.called_by ? `→ ${ev.agent_name} (called by ${ev.called_by})` : `→ ${ev.agent_name} starting`;
    case 'agent_end': {
      const dur = ev.duration_ms != null ? ` · ${formatDuration(ev.duration_ms)}` : '';
      return `✓ ${ev.agent_name} returned${dur}`;
    }
    case 'llm_call': {
      const tokens = (ev.input_tokens != null && ev.output_tokens != null)
        ? ` (${ev.input_tokens} in / ${ev.output_tokens} out)`
        : '';
      const dur = ev.duration_ms != null ? ` · ${formatDuration(ev.duration_ms)}` : '';
      return `llm.call  ${ev.provider}/${ev.model}${tokens}${dur}`;
    }
    case 'data_store': {
      const target = ev.namespace + (ev.key ? `[${ev.key}]` : '');
      return `data_store.${ev.operation}  ${target}`;
    }
    case 'log':
      return `[${ev.level}] ${ev.message}`;
    case 'stdout':
      return ev.message;
    case 'error':
      return `✗ ${ev.exception_type}: ${ev.message}`;
    case 'trace_truncated':
      return `(${ev.message})`;
    default:
      return ev.message || ev.type;
  }
};

// Decide whether an event has expandable detail (stack trace, multi-line
// stdout) and what string to use for the inline preview vs the full sheet.
const eventDetail = (ev) => {
  if (ev.type === 'error' && ev.traceback) {
    return { full: ev.traceback, label: 'stack trace' };
  }
  if (ev.type === 'stdout' && ev.message?.includes('\n')) {
    return { full: ev.message, label: 'output' };
  }
  if (ev.type === 'log' && ev.message?.includes('\n')) {
    return { full: ev.message, label: 'log entry' };
  }
  return null;
};

// Truncate a multi-line string to N lines for the inline preview.
const truncateLines = (s, maxLines = 3) => {
  const lines = s.split('\n');
  if (lines.length <= maxLines) return { text: s, truncated: false };
  return {
    text: lines.slice(0, maxLines).join('\n'),
    truncated: true,
    remaining: lines.length - maxLines,
  };
};

// Group flat events into per-agent sections within a run. Uses depth to
// preserve the call hierarchy. We show top-level agent groups as
// collapsible cards; nested calls (depth > 0) appear inside their
// parent's group.
const groupEventsByAgent = (events) => {
  const groups = [];
  const stack = []; // [{name, events: [...]}]

  for (const ev of events) {
    if (ev.type === 'agent_start') {
      const group = {
        name: ev.agent_name,
        depth: ev.depth,
        startEvent: ev,
        events: [],
        endEvent: null,
        outcome: 'running',
      };
      if (ev.depth === 0 || stack.length === 0) {
        groups.push(group);
      } else {
        stack[stack.length - 1].events.push(group); // nested
      }
      stack.push(group);
      continue;
    }
    if (ev.type === 'agent_end') {
      if (stack.length > 0) {
        const top = stack.pop();
        top.endEvent = ev;
        top.outcome = ev.outcome || 'success';
      }
      continue;
    }
    // Regular event — attach to current top of stack.
    if (stack.length > 0) {
      stack[stack.length - 1].events.push(ev);
      // Bubble error outcome up to the group
      if (ev.type === 'error') {
        stack[stack.length - 1].outcome = 'error';
      }
    } else {
      // Stray event before any agent_start — shouldn't happen but
      // keep it visible at the top level instead of dropping.
      groups.push({
        name: '(unbound)',
        depth: 0,
        startEvent: null,
        events: [ev],
        endEvent: null,
        outcome: ev.type === 'error' ? 'error' : 'info',
      });
    }
  }

  return groups;
};

// ---------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------

const EventRow = ({ event, onOpenDetail }) => {
  const detail = eventDetail(event);
  const summary = eventSummary(event);
  const isError = event.type === 'error';

  // For stdout/log multi-line events, inline the first 3 lines and
  // offer "more" to open the side sheet.
  let preview = null;
  let moreLabel = null;
  if (detail) {
    const { text, truncated, remaining } = truncateLines(detail.full, 3);
    preview = text;
    moreLabel = truncated ? `more (${remaining} more lines)` : `view full ${detail.label}`;
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1.5,
        py: 0.5,
        pl: event.depth ? event.depth * 2 : 0,
        ...(isError && {
          bgcolor: 'error.lighter',
          borderLeft: 3,
          borderColor: 'error.main',
          px: 1,
          mx: -1,
          borderRadius: 0.5,
        }),
      }}
    >
      <Typography
        variant="caption"
        sx={{ color: 'text.secondary', fontFamily: 'monospace', flexShrink: 0, minWidth: 70 }}
      >
        {formatTime(event.ts)}
      </Typography>
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Typography
          variant="body2"
          sx={(theme) => ({
            color: eventColor(theme, event),
            fontFamily: detail || event.type === 'log' || event.type === 'stdout'
              ? 'monospace' : 'inherit',
            fontSize: '0.8rem',
            wordBreak: 'break-word',
            ...(isError && { fontWeight: 600 }),
          })}
        >
          {summary}
        </Typography>

        {/* Inline preview for multi-line content (stack traces, multi-line
            stdout). Always shows a "more" link to open the side sheet. */}
        {detail && (
          <Box sx={{ mt: 0.5 }}>
            <Box
              component="pre"
              sx={{
                m: 0,
                fontSize: '0.72rem',
                fontFamily: 'monospace',
                color: 'text.secondary',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                bgcolor: 'background.paper',
                p: 1,
                borderRadius: 0.5,
                border: 1,
                borderColor: 'divider',
              }}
            >
              {preview}
            </Box>
            {moreLabel && (
              <Button
                size="small"
                onClick={() => onOpenDetail(event)}
                sx={{ mt: 0.25, fontSize: '0.7rem', textTransform: 'none', minWidth: 0, p: 0.25 }}
              >
                {moreLabel}
              </Button>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};

EventRow.propTypes = {
  event: PropTypes.object.isRequired,
  onOpenDetail: PropTypes.func.isRequired,
};

// Heuristic for "this stdout/log line probably represents an error
// the agent caught and printed". Useful for bucket badges; doesn't
// affect coloring of structural error events (those are already red).
const looksLikeUserError = (ev) => {
  if (ev.type !== 'stdout' && ev.type !== 'log') return false;
  const m = (ev.message || '').toUpperCase();
  return m.includes('ERROR') || m.includes('FAIL') || m.includes('TRACEBACK');
};

const AgentGroup = ({ group, onOpenBucket, onOpenDetail }) => {
  const outcomeIcon = group.outcome === 'error'
    ? <ErrorOutlineIcon sx={{ fontSize: 14, color: 'error.main' }} />
    : group.outcome === 'running'
    ? <HourglassEmptyIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
    : <CheckCircleIcon sx={{ fontSize: 14, color: 'success.main' }} />;

  const duration = group.endEvent?.duration_ms;

  // Walk the children once. Structural events render inline; stdout/log
  // events get accumulated into per-position buckets so the order
  // relative to structural events is preserved (e.g. you see
  // "agent prints stuff → llm.call → agent prints more" rather than
  // "agent prints everything → llm.call"). Each contiguous run of
  // bucketable events becomes one bucket row.
  const renderItems = [];
  let pendingBucket = null;

  const flushBucket = () => {
    if (pendingBucket && pendingBucket.events.length > 0) {
      renderItems.push({ kind: 'bucket', ...pendingBucket });
    }
    pendingBucket = null;
  };

  for (let idx = 0; idx < group.events.length; idx++) {
    const ev = group.events[idx];
    // Nested agent group.
    if (ev.events && Array.isArray(ev.events)) {
      flushBucket();
      renderItems.push({ kind: 'nested', group: ev, idx });
      continue;
    }
    // Bucketable: stdout/log.
    if (ev.type === 'stdout' || ev.type === 'log') {
      if (!pendingBucket) {
        pendingBucket = { events: [], firstIdx: idx };
      }
      pendingBucket.events.push(ev);
      continue;
    }
    // Anything else is structural — render inline.
    flushBucket();
    renderItems.push({ kind: 'event', event: ev, idx });
  }
  flushBucket();

  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
        {outcomeIcon}
        <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
          {group.name}
        </Typography>
        {duration != null && (
          <Typography variant="caption" color="text.secondary">
            · {formatDuration(duration)}
          </Typography>
        )}
        {group.depth > 0 && (
          <Chip label="chained" size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
        )}
      </Box>
      <Box sx={{ pl: 2, borderLeft: 1, borderColor: 'divider' }}>
        {renderItems.map((item) => {
          if (item.kind === 'nested') {
            return (
              <AgentGroup
                key={`nested-${item.idx}`}
                group={item.group}
                onOpenBucket={onOpenBucket}
                onOpenDetail={onOpenDetail}
              />
            );
          }
          if (item.kind === 'event') {
            return (
              <EventRow
                key={`${item.event.ts}-${item.idx}`}
                event={item.event}
                onOpenDetail={onOpenDetail}
              />
            );
          }
          // Bucket. Show count + (if any) error-flavored count, with
          // a one-line preview of the most recent error-looking line
          // so common failure modes are visible without clicking.
          const errorishEvents = item.events.filter(looksLikeUserError);
          const lastErrorish = errorishEvents[errorishEvents.length - 1];
          const lineWord = item.events.length === 1 ? 'line' : 'lines';
          return (
            <Box
              key={`bucket-${item.firstIdx}`}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
                py: 0.5,
                cursor: 'pointer',
                '&:hover': { bgcolor: 'action.hover' },
                borderRadius: 0.5,
                px: 1,
                mx: -1,
                ...(errorishEvents.length > 0 && {
                  bgcolor: 'error.lighter',
                  borderLeft: 3,
                  borderColor: 'error.main',
                }),
              }}
              onClick={() => onOpenBucket(group.name, item.events)}
            >
              <Typography
                variant="caption"
                sx={{ color: 'text.secondary', fontFamily: 'monospace', flexShrink: 0, minWidth: 70 }}
              >
                {formatTime(item.events[0].ts)}
              </Typography>
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                  <strong>{item.events.length} {lineWord}</strong>
                  {' '}of stdout/log output
                  {errorishEvents.length > 0 && (
                    <span style={{ color: 'var(--mui-palette-error-main, #d32f2f)' }}>
                      {' · '}{errorishEvents.length} with errors
                    </span>
                  )}
                  {' · '}
                  <span style={{ textDecoration: 'underline' }}>click to view</span>
                </Typography>
                {lastErrorish && (
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      color: 'error.main',
                      mt: 0.25,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={lastErrorish.message}
                  >
                    Latest: {lastErrorish.message}
                  </Typography>
                )}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

AgentGroup.propTypes = {
  group: PropTypes.object.isRequired,
  onOpenBucket: PropTypes.func.isRequired,
  onOpenDetail: PropTypes.func.isRequired,
};

const RunSection = ({ run, index, onOpenBucket, onOpenDetail }) => {
  const groups = useMemo(() => groupEventsByAgent(run.events || []), [run.events]);
  const totalDuration = run.duration_ms;
  const isError = run.outcome === 'error';
  const isRunning = run.outcome === 'running';

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.5,
        border: 1,
        borderColor: isError ? 'error.main' : 'divider',
        borderRadius: 1,
        bgcolor: 'background.paper',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Run #{index + 1}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          · started {formatTime(run.started_at)}
        </Typography>
        {totalDuration != null && (
          <Typography variant="caption" color="text.secondary">
            · {formatDuration(totalDuration)}
          </Typography>
        )}
        <Box sx={{ flexGrow: 1 }} />
        {isRunning && <Chip label="running" size="small" color="default" />}
        {!isRunning && (
          <Chip
            label={isError ? 'error' : 'success'}
            size="small"
            color={isError ? 'error' : 'success'}
            variant="outlined"
          />
        )}
      </Box>
      {groups.length === 0 ? (
        <Typography variant="caption" color="text.secondary">
          No events recorded.
        </Typography>
      ) : (
        groups.map((g, i) => (
          <AgentGroup key={`g-${i}`} group={g} onOpenBucket={onOpenBucket} onOpenDetail={onOpenDetail} />
        ))
      )}
    </Box>
  );
};

RunSection.propTypes = {
  run: PropTypes.object.isRequired,
  index: PropTypes.number.isRequired,
  onOpenBucket: PropTypes.func.isRequired,
  onOpenDetail: PropTypes.func.isRequired,
};

// ---------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------

const SandboxProgressLog = ({ runs }) => {
  const [detailEvent, setDetailEvent] = useState(null);
  // When set, the side sheet shows all events in a bucket (one agent's
  // stdout/log slice) instead of a single event's full content.
  const [detailBucket, setDetailBucket] = useState(null);

  // Newest runs first.
  const runsNewestFirst = useMemo(
    () => (runs ? [...runs].reverse() : []),
    [runs]
  );

  // Status for the accordion summary line.
  const latestRun = runsNewestFirst[0];
  const summaryText = !latestRun
    ? 'No runs yet'
    : latestRun.outcome === 'running'
    ? 'Running…'
    : latestRun.outcome === 'error'
    ? `Last run: error · ${formatTime(latestRun.started_at)}`
    : `Last run: success · ${formatTime(latestRun.started_at)}`;

  const detailFull = detailEvent ? eventDetail(detailEvent) : null;

  return (
    <>
      <Accordion defaultExpanded sx={{ mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
            <Typography sx={{ fontWeight: 600 }}>Progress Log</Typography>
            <Typography variant="caption" color="text.secondary">
              {summaryText}
            </Typography>
            {runsNewestFirst.length > 0 && (
              <Box sx={{ flexGrow: 1 }} />
            )}
            {runsNewestFirst.length > 0 && (
              <Chip
                label={`${runsNewestFirst.length} run${runsNewestFirst.length === 1 ? '' : 's'}`}
                size="small"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
          </Box>
        </AccordionSummary>
        <AccordionDetails sx={{ pt: 0 }}>
          {runsNewestFirst.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Run the agent to see a per-agent trace of what it's doing —
              LLM calls, data store ops, errors, and any output it prints.
            </Typography>
          ) : (
            <Stack spacing={0}>
              {runsNewestFirst.map((run, i) => (
                <RunSection
                  key={run.run_id || i}
                  run={run}
                  index={runsNewestFirst.length - 1 - i}
                  onOpenBucket={(agentName, events) => {
                    setDetailEvent(null);
                    setDetailBucket({ agentName, events });
                  }}
                  onOpenDetail={(ev) => {
                    setDetailBucket(null);
                    setDetailEvent(ev);
                  }}
                />
              ))}
            </Stack>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Side sheet — single event view (stack traces, multi-line
          content) or bucket view (all stdout/log lines for one
          agent). The two modes are mutually exclusive; opening one
          closes the other. */}
      <Drawer
        anchor="right"
        open={Boolean(detailEvent || detailBucket)}
        onClose={() => { setDetailEvent(null); setDetailBucket(null); }}
        PaperProps={{ sx: { width: { xs: '100%', sm: 700 }, maxWidth: '100%' } }}
      >
        {detailEvent && (
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6">
                  {detailEvent.type === 'error' ? 'Stack Trace' : 'Full Output'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {detailEvent.agent_name} · {formatTime(detailEvent.ts)}
                  {detailEvent.exception_type && ` · ${detailEvent.exception_type}`}
                </Typography>
              </Box>
              <Tooltip title="Close">
                <IconButton onClick={() => setDetailEvent(null)} size="small">
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            </Box>
            <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
              {detailEvent.type === 'error' && detailEvent.message && (
                <>
                  <Typography variant="overline" color="text.secondary">Message</Typography>
                  <Typography variant="body2" sx={{ mb: 2, fontFamily: 'monospace' }}>
                    {detailEvent.message}
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Typography variant="overline" color="text.secondary">Traceback</Typography>
                </>
              )}
              <Box
                component="pre"
                sx={{
                  m: 0,
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {detailFull?.full || detailEvent.message || ''}
              </Box>
            </Box>
          </Box>
        )}
        {detailBucket && (
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6">Output</Typography>
                <Typography variant="caption" color="text.secondary">
                  {detailBucket.agentName} · {detailBucket.events.length} line{detailBucket.events.length === 1 ? '' : 's'}
                </Typography>
              </Box>
              <Tooltip title="Close">
                <IconButton onClick={() => setDetailBucket(null)} size="small">
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            </Box>
            {/* Each line on its own row with a timestamp gutter so you
                can correlate output with structural events. Errors get
                a red left border. Monospace throughout. */}
            <Box sx={{ flexGrow: 1, overflow: 'auto', fontFamily: 'monospace', fontSize: '0.78rem' }}>
              {detailBucket.events.map((ev, idx) => {
                const isErr = looksLikeUserError(ev);
                return (
                  <Box
                    key={`${ev.ts}-${idx}`}
                    sx={{
                      display: 'flex',
                      gap: 1.5,
                      px: 2,
                      py: 0.25,
                      ...(isErr && {
                        bgcolor: 'error.lighter',
                        borderLeft: 3,
                        borderColor: 'error.main',
                        pl: 1.5,
                      }),
                    }}
                  >
                    <Box sx={{ color: 'text.secondary', flexShrink: 0, minWidth: 70 }}>
                      {formatTime(ev.ts)}
                    </Box>
                    <Box sx={{ flexGrow: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {ev.type === 'log' && ev.level && <span style={{ opacity: 0.7 }}>[{ev.level}] </span>}
                      {ev.message}
                    </Box>
                  </Box>
                );
              })}
            </Box>
          </Box>
        )}
      </Drawer>
    </>
  );
};

SandboxProgressLog.propTypes = {
  runs: PropTypes.array,
};

export default SandboxProgressLog;
