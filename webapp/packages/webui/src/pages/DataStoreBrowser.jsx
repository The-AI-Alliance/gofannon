import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  CircularProgress,
  Tooltip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Stack,
  Drawer,
  TextField,
  InputAdornment,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Snackbar,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import dataStoreService from '../services/dataStoreService';

const formatBytes = (n) => {
  if (n == null) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDateTime = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
};

// Estimate record size from its JSON value length. Cheap and good enough
// for the "1.8 KB" chips next to each record.
const recordSize = (value) => {
  try { return new Blob([JSON.stringify(value)]).size; } catch { return 0; }
};

// Group records by their leading path segment (everything before the first
// slash). Keys without a slash go into a `(no prefix)` bucket. Matches the
// `src/`, `_metadata/` groupings in the mockup.
const groupByPrefix = (records) => {
  const groups = new Map();
  for (const rec of records) {
    const key = rec.key || '';
    const slashIdx = key.indexOf('/');
    const prefix = slashIdx >= 0 ? `${key.slice(0, slashIdx)}/` : '(no prefix)';
    if (!groups.has(prefix)) groups.set(prefix, []);
    groups.get(prefix).push(rec);
  }
  // Sort groups alphabetically, keys within each group alphabetically
  for (const [, list] of groups) list.sort((a, b) => (a.key || '').localeCompare(b.key || ''));
  return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
};

// Heuristic "type" label for a record value. Matches the "summary" chip in
// the mockup — agents can put whatever they want in `metadata.type`, so
// prefer that; otherwise fall back to the JS typeof.
const recordType = (rec) => {
  const explicit = rec?.metadata?.type;
  if (explicit) return String(explicit);
  const v = rec?.value;
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
};

const PrefixGroup = ({ prefix, records, onSelect, selectedKey }) => {
  const [open, setOpen] = useState(true);
  return (
    <Box sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
      <Box
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          p: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
        <Typography sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{prefix}</Typography>
        <Chip label={records.length} size="small" sx={{ ml: 1, height: 20, fontSize: '0.7rem' }} />
      </Box>
      {open && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ pl: 5 }}>Key</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Size</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((rec) => {
              const isSelected = rec.key === selectedKey;
              return (
                <TableRow
                  key={rec._id || rec.key}
                  hover
                  onClick={() => onSelect(rec)}
                  sx={{
                    cursor: 'pointer',
                    bgcolor: isSelected ? 'action.selected' : 'transparent',
                  }}
                >
                  <TableCell sx={{ pl: 5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <DescriptionIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {rec.key}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={recordType(rec)}
                      size="small"
                      sx={{ height: 20, fontSize: '0.7rem', bgcolor: '#f1f5f9', color: '#334155' }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      {formatBytes(recordSize(rec.value))}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </Box>
  );
};

const RecordDrawer = ({ record, onClose, onCopy, onDelete, onEdit }) => {
  if (!record) return null;
  const typeLabel = recordType(record);
  const sizeBytes = recordSize(record.value);
  const valueStr = typeof record.value === 'string'
    ? record.value
    : JSON.stringify(record.value, null, 2);

  return (
    <Drawer anchor="right" open={Boolean(record)} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 480 } } }}>
      <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6" sx={{ fontFamily: 'monospace', wordBreak: 'break-all', pr: 2 }}>
            {record.key}
          </Typography>
          <IconButton size="small" onClick={onClose} aria-label="Close"><CloseIcon /></IconButton>
        </Box>
        <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
          <Chip
            label={typeLabel}
            size="small"
            sx={{ height: 22, bgcolor: '#f1f5f9', color: '#334155' }}
          />
          <Chip label={formatBytes(sizeBytes)} size="small" sx={{ height: 22 }} />
        </Box>
      </Box>

      <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
        <Typography variant="overline" color="text.secondary">Value</Typography>
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#fafafa', mt: 0.5, maxHeight: 300, overflow: 'auto' }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', fontSize: '0.82rem' }}>
            {valueStr}
          </pre>
        </Paper>

        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mt: 3 }}>
          Metadata
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 1 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Created by</Typography>
            <Typography variant="body2">{record.createdByAgent || '—'}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Last accessed by</Typography>
            <Typography variant="body2">{record.lastAccessedByAgent || '—'}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Created</Typography>
            <Typography variant="body2">{formatDateTime(record.createdAt)}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Updated</Typography>
            <Typography variant="body2">{formatDateTime(record.updatedAt)}</Typography>
          </Box>
          <Box sx={{ gridColumn: '1 / -1' }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Access count</Typography>
            <Typography variant="body2">{record.accessCount || 0}</Typography>
          </Box>
        </Box>
      </Box>

      <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider', display: 'flex', gap: 1 }}>
        <Button startIcon={<ContentCopyIcon fontSize="small" />} onClick={onCopy} variant="outlined" fullWidth>
          Copy
        </Button>
        <Button startIcon={<EditIcon fontSize="small" />} onClick={onEdit} variant="outlined" fullWidth>
          Edit
        </Button>
        <Button startIcon={<DeleteIcon fontSize="small" />} onClick={onDelete} variant="outlined" color="error" fullWidth>
          Delete
        </Button>
      </Box>
    </Drawer>
  );
};

const EditDialog = ({ record, open, onClose, onSave }) => {
  const [text, setText] = useState('');
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (open && record) {
      const initial = typeof record.value === 'string'
        ? record.value
        : JSON.stringify(record.value, null, 2);
      setText(initial);
      setErr(null);
    }
  }, [open, record]);

  const handleSave = async () => {
    setErr(null);
    // Try to parse as JSON first; if it fails, save as raw string.
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
    try {
      await onSave(parsed);
    } catch (e) {
      setErr(e.message || 'Save failed.');
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Edit <code>{record?.key}</code></DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 1 }}>
          Valid JSON is parsed (objects, arrays, numbers, booleans, null). Anything else is stored as a string.
        </DialogContentText>
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={10}
          maxRows={30}
          value={text}
          onChange={(e) => setText(e.target.value)}
          InputProps={{ sx: { fontFamily: 'monospace', fontSize: '0.85rem' } }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};

const DataStoreBrowser = () => {
  const { namespace: namespaceRaw } = useParams();
  const namespace = decodeURIComponent(namespaceRaw || '');
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsResp, recordsResp] = await Promise.all([
        dataStoreService.getNamespaceStats(namespace),
        dataStoreService.listRecords(namespace),
      ]);
      setStats(statsResp);
      setRecords(recordsResp || []);
    } catch (err) {
      setError(err.message || 'Failed to load namespace.');
    } finally {
      setLoading(false);
    }
  }, [namespace]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return records;
    const q = search.trim().toLowerCase();
    return records.filter((r) => (r.key || '').toLowerCase().includes(q));
  }, [records, search]);

  const grouped = useMemo(() => groupByPrefix(filtered), [filtered]);

  const handleCopy = () => {
    if (!selected) return;
    const str = typeof selected.value === 'string'
      ? selected.value
      : JSON.stringify(selected.value, null, 2);
    navigator.clipboard.writeText(str).then(
      () => setSnack({ severity: 'success', message: 'Value copied to clipboard.' }),
      () => setSnack({ severity: 'error', message: 'Copy failed.' })
    );
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await dataStoreService.deleteRecord(namespace, deleteTarget.key);
      setDeleteTarget(null);
      if (selected && selected.key === deleteTarget.key) setSelected(null);
      setSnack({ severity: 'success', message: `Deleted ${deleteTarget.key}.` });
      await load();
    } catch (err) {
      setSnack({ severity: 'error', message: err.message || 'Delete failed.' });
    }
  };

  const handleEditSave = async (newValue) => {
    await dataStoreService.setRecord(namespace, selected.key, newValue);
    setEditOpen(false);
    setSnack({ severity: 'success', message: 'Saved.' });
    await load();
    // re-select with the fresh record
    const fresh = await dataStoreService.getRecord(namespace, selected.key);
    setSelected(fresh);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1400, margin: '0 auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton size="small" onClick={() => navigate('/data-stores')} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
            {namespace}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Browse and manage stored data records
          </Typography>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Accordion defaultExpanded sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>Overview</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {stats ? (
            <Box>
              <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap' }}>
                <Chip label={`${(stats.recordCount || 0).toLocaleString()} records`} sx={{ fontWeight: 500 }} />
                <Chip label={`${formatBytes(stats.sizeBytes || 0)} total size`} />
                <Chip label={`Updated ${formatDateTime(stats.updatedAt)}`} />
              </Stack>
              {(stats.agents || []).length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary">Accessed by:</Typography>
                  <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {stats.agents.map((a) => (
                      <Chip
                        key={a}
                        label={a}
                        size="small"
                        sx={{ bgcolor: '#e0f2fe', color: '#075985' }}
                      />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          ) : (
            <Typography color="text.secondary">—</Typography>
          )}
        </AccordionDetails>
      </Accordion>

      <Paper>
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ mb: 1 }}>Records</Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Search keys…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
        </Box>
        {loading ? (
          <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={28} />
          </Box>
        ) : grouped.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary" variant="body2">
              {records.length === 0 ? 'This namespace is empty.' : 'No records match your search.'}
            </Typography>
          </Box>
        ) : (
          <Box>
            {grouped.map(([prefix, recs]) => (
              <PrefixGroup
                key={prefix}
                prefix={prefix}
                records={recs}
                selectedKey={selected?.key}
                onSelect={setSelected}
              />
            ))}
          </Box>
        )}
      </Paper>

      <RecordDrawer
        record={selected}
        onClose={() => setSelected(null)}
        onCopy={handleCopy}
        onEdit={() => setEditOpen(true)}
        onDelete={() => setDeleteTarget(selected)}
      />
      <EditDialog
        record={selected}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSave={handleEditSave}
      />
      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete record?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Permanently delete <code>{deleteTarget?.key}</code>? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
      <Snackbar
        open={Boolean(snack)}
        autoHideDuration={3000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        {snack && <Alert severity={snack.severity} onClose={() => setSnack(null)}>{snack.message}</Alert>}
      </Snackbar>
    </Box>
  );
};

export default DataStoreBrowser;
