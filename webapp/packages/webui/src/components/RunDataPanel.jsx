import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Chip,
  Collapse,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import StorageIcon from '@mui/icons-material/Storage';

// Classify each op into a coarse read/write bucket for the chip color.
// Writes (set/delete/clear) are salient; reads (get/list) are neutral.
const opCategory = (op) => {
  if (op === 'set' || op === 'set_many') return 'write';
  if (op === 'delete' || op === 'clear') return 'destructive';
  return 'read';
};

const categoryStyle = {
  read:        { bgcolor: '#e0f2fe', color: '#075985', label: 'READ'  },
  write:       { bgcolor: '#dcfce7', color: '#166534', label: 'WRITE' },
  destructive: { bgcolor: '#fee2e2', color: '#991b1b', label: 'DEL'   },
};

// Time formatter for the op list. Uses the ops' own timestamps so nothing
// drifts if the user takes a while to expand the panel. Falls back to ''
// if we can't parse.
const fmtTime = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour12: false });
};

const OpRow = ({ op, index }) => {
  const [open, setOpen] = useState(false);
  const cat = opCategory(op.op);
  const style = categoryStyle[cat];
  // Show a compact summary on the collapsed row, everything on expand.
  const summary = op.key
    ? op.key
    : op.prefix
      ? `prefix=${op.prefix}`
      : op.count != null
        ? `${op.count} item${op.count === 1 ? '' : 's'}`
        : '';

  return (
    <Box sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
      <Box
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1,
          py: 0.75,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
        <Typography variant="caption" sx={{ color: 'text.secondary', minWidth: 56, fontFamily: 'monospace' }}>
          {fmtTime(op.ts)}
        </Typography>
        <Chip
          label={style.label}
          size="small"
          sx={{ height: 18, fontSize: '0.65rem', fontWeight: 600, bgcolor: style.bgcolor, color: style.color }}
        />
        <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', fontWeight: 500 }}>
          {op.op}
        </Typography>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{ fontFamily: 'monospace', fontSize: '0.78rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {summary}
          </Typography>
        </Box>
        <Chip
          label={op.namespace || 'default'}
          size="small"
          sx={{ height: 18, fontSize: '0.65rem', fontFamily: 'monospace' }}
        />
      </Box>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box sx={{ px: 3, pb: 1, pt: 0.5, bgcolor: '#fafafa' }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 0.5, fontSize: '0.75rem' }}>
            <Typography variant="caption" color="text.secondary">index</Typography>
            <Typography variant="caption">#{index}</Typography>
            <Typography variant="caption" color="text.secondary">agent</Typography>
            <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{op.agent || '—'}</Typography>
            {op.key && (
              <>
                <Typography variant="caption" color="text.secondary">key</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {op.key}
                </Typography>
              </>
            )}
            {op.valuePreview !== undefined && op.valuePreview !== null && (
              <>
                <Typography variant="caption" color="text.secondary">value</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {op.valuePreview}
                </Typography>
              </>
            )}
            {op.found !== undefined && (
              <>
                <Typography variant="caption" color="text.secondary">found</Typography>
                <Typography variant="caption">{String(op.found)}</Typography>
              </>
            )}
            {op.count !== undefined && (
              <>
                <Typography variant="caption" color="text.secondary">count</Typography>
                <Typography variant="caption">{op.count}</Typography>
              </>
            )}
            {op.prefix !== undefined && op.prefix !== null && (
              <>
                <Typography variant="caption" color="text.secondary">prefix</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{op.prefix}</Typography>
              </>
            )}
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
};

OpRow.propTypes = {
  op: PropTypes.object.isRequired,
  index: PropTypes.number.isRequired,
};

// Aggregate ops into per-namespace state rows.
const aggregateByNamespace = (ops) => {
  const byNs = new Map();
  for (const op of ops) {
    const ns = op.namespace || 'default';
    if (!byNs.has(ns)) {
      byNs.set(ns, {
        namespace: ns,
        reads: 0,
        writes: 0,
        deletes: 0,
        lastTs: null,
        keys: new Set(),
      });
    }
    const b = byNs.get(ns);
    const cat = opCategory(op.op);
    if (cat === 'read') b.reads += 1;
    else if (cat === 'write') b.writes += 1;
    else b.deletes += 1;
    if (op.key) b.keys.add(op.key);
    if (!b.lastTs || (op.ts && op.ts > b.lastTs)) b.lastTs = op.ts;
  }
  return Array.from(byNs.values()).sort((a, b) => a.namespace.localeCompare(b.namespace));
};

const RunDataPanel = ({ opsLog }) => {
  const [tab, setTab] = useState(0);
  const ops = opsLog || [];
  const aggregated = useMemo(() => aggregateByNamespace(ops), [ops]);

  const readCount = useMemo(() => ops.filter((o) => opCategory(o.op) === 'read').length, [ops]);
  const writeCount = useMemo(() => ops.filter((o) => opCategory(o.op) !== 'read').length, [ops]);

  return (
    <Paper variant="outlined" sx={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 2, pt: 1.5, pb: 1, borderBottom: '1px solid', borderColor: 'divider', bgcolor: '#fafafa' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <StorageIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Data Store</Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Tooltip title="Reads this run" arrow>
            <Chip
              label={`${readCount} R`}
              size="small"
              sx={{ height: 20, fontSize: '0.68rem', bgcolor: '#e0f2fe', color: '#075985' }}
            />
          </Tooltip>
          <Tooltip title="Writes this run" arrow>
            <Chip
              label={`${writeCount} W`}
              size="small"
              sx={{ height: 20, fontSize: '0.68rem', bgcolor: '#dcfce7', color: '#166534' }}
            />
          </Tooltip>
        </Box>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="fullWidth"
        sx={{ minHeight: 36, '& .MuiTab-root': { minHeight: 36, fontSize: '0.8rem', textTransform: 'none' } }}
      >
        <Tab label={`Operations (${ops.length})`} />
        <Tab label={`State (${aggregated.length})`} />
      </Tabs>

      <Box sx={{ flexGrow: 1, overflowY: 'auto', minHeight: 200 }}>
        {tab === 0 && (
          ops.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                No data store operations yet. Run the agent to see reads and writes here.
              </Typography>
            </Box>
          ) : (
            <Box>
              {ops.map((op, idx) => <OpRow key={idx} op={op} index={idx} />)}
            </Box>
          )
        )}

        {tab === 1 && (
          aggregated.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                No namespaces touched this run.
              </Typography>
            </Box>
          ) : (
            <Box>
              {aggregated.map((row) => (
                <Box
                  key={row.namespace}
                  sx={{ px: 2, py: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 500, flexGrow: 1 }}>
                      {row.namespace}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                      {fmtTime(row.lastTs)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {row.reads > 0 && (
                      <Chip
                        label={`${row.reads} read${row.reads === 1 ? '' : 's'}`}
                        size="small"
                        sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#e0f2fe', color: '#075985' }}
                      />
                    )}
                    {row.writes > 0 && (
                      <Chip
                        label={`${row.writes} write${row.writes === 1 ? '' : 's'}`}
                        size="small"
                        sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#dcfce7', color: '#166534' }}
                      />
                    )}
                    {row.deletes > 0 && (
                      <Chip
                        label={`${row.deletes} delete${row.deletes === 1 ? '' : 's'}`}
                        size="small"
                        sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#fee2e2', color: '#991b1b' }}
                      />
                    )}
                    <Chip
                      label={`${row.keys.size} key${row.keys.size === 1 ? '' : 's'} touched`}
                      size="small"
                      sx={{ height: 18, fontSize: '0.65rem' }}
                    />
                  </Box>
                </Box>
              ))}
            </Box>
          )
        )}
      </Box>
    </Paper>
  );
};

RunDataPanel.propTypes = {
  opsLog: PropTypes.array,
};

export default RunDataPanel;
