import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Autocomplete,
  Tooltip,
  Alert,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowRightAltIcon from '@mui/icons-material/ArrowRightAlt';
import StorageIcon from '@mui/icons-material/Storage';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import dataStoreService from '../services/dataStoreService';

// Flow preview: "Reads From  →  [agent]  →  Writes To"
const FlowPreview = ({ agentName, configs }) => {
  const reads = configs.filter((c) => c.access === 'read' || c.access === 'both');
  const writes = configs.filter((c) => c.access === 'write' || c.access === 'both');

  const Column = ({ title, items, accent, empty }) => (
    <Paper
      variant="outlined"
      sx={{
        flex: 1,
        p: 1.5,
        minHeight: 120,
        borderColor: accent,
        borderStyle: items.length === 0 ? 'dashed' : 'solid',
      }}
    >
      <Typography variant="overline" sx={{ color: accent, fontSize: '0.68rem', fontWeight: 600 }}>
        {title}
      </Typography>
      <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {items.length === 0 ? (
          <Typography variant="caption" color="text.secondary">{empty}</Typography>
        ) : items.map((c) => (
          <Box key={c.namespace} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <StorageIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 500 }}>
              {c.namespace}
            </Typography>
          </Box>
        ))}
      </Box>
    </Paper>
  );

  Column.propTypes = {
    title: PropTypes.string.isRequired,
    items: PropTypes.array.isRequired,
    accent: PropTypes.string.isRequired,
    empty: PropTypes.string.isRequired,
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'stretch', gap: 1, mb: 2 }}>
      <Column title="Reads from" items={reads} accent="#075985" empty="(none)" />
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <ArrowRightAltIcon sx={{ color: 'text.secondary' }} />
      </Box>
      <Paper
        variant="outlined"
        sx={{
          flex: 1,
          p: 1.5,
          minHeight: 120,
          bgcolor: '#fafafa',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
        }}
      >
        <SmartToyIcon sx={{ color: 'primary.main', mb: 0.5 }} />
        <Typography variant="caption" sx={{ fontWeight: 600 }}>
          {agentName || '(this agent)'}
        </Typography>
      </Paper>
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <ArrowRightAltIcon sx={{ color: 'text.secondary' }} />
      </Box>
      <Column title="Writes to" items={writes} accent="#166534" empty="(none)" />
    </Box>
  );
};

FlowPreview.propTypes = {
  agentName: PropTypes.string,
  configs: PropTypes.array.isRequired,
};

const ConfigDialog = ({ open, onClose, onSave, initialConfig, suggestions, usedNamespaces }) => {
  const [namespace, setNamespace] = useState('');
  const [access, setAccess] = useState('both');
  const [description, setDescription] = useState('');
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (open) {
      setNamespace(initialConfig?.namespace || '');
      setAccess(initialConfig?.access || 'both');
      setDescription(initialConfig?.description || '');
      setErr(null);
    }
  }, [open, initialConfig]);

  const handleSave = () => {
    const trimmed = (namespace || '').trim();
    if (!trimmed) {
      setErr('Namespace is required.');
      return;
    }
    if (!initialConfig && usedNamespaces.has(trimmed)) {
      setErr('This namespace is already configured. Edit it instead.');
      return;
    }
    onSave({ namespace: trimmed, access, description: description.trim() || undefined });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialConfig ? 'Edit namespace config' : 'Add namespace config'}</DialogTitle>
      <DialogContent>
        {err && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErr(null)}>{err}</Alert>}

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Namespace
        </Typography>
        <Autocomplete
          freeSolo
          options={suggestions}
          value={namespace}
          onChange={(_, newValue) => setNamespace(newValue || '')}
          onInputChange={(_, newValue) => setNamespace(newValue)}
          disabled={Boolean(initialConfig)}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              placeholder="e.g. repo-summaries"
              helperText={initialConfig ? 'Namespace cannot be changed — delete and re-add.' : 'Pick an existing namespace or type a new one.'}
            />
          )}
          sx={{ mb: 2 }}
        />

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Access mode
        </Typography>
        <ToggleButtonGroup
          value={access}
          exclusive
          onChange={(_, v) => v && setAccess(v)}
          size="small"
          fullWidth
          sx={{ mb: 2 }}
        >
          <ToggleButton value="read">Read</ToggleButton>
          <ToggleButton value="write">Write</ToggleButton>
          <ToggleButton value="both">Both</ToggleButton>
        </ToggleButtonGroup>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
          Advisory only — the runtime doesn&apos;t enforce this. It&apos;s used to show
          data flow in the editor and viewer.
        </Typography>

        <TextField
          fullWidth
          size="small"
          label="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          multiline
          minRows={2}
          maxRows={4}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};

ConfigDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  initialConfig: PropTypes.object,
  suggestions: PropTypes.array.isRequired,
  usedNamespaces: PropTypes.instanceOf(Set).isRequired,
};

const accessChipStyle = {
  read:  { label: 'Read',  bgcolor: '#e0f2fe', color: '#075985' },
  write: { label: 'Write', bgcolor: '#dcfce7', color: '#166534' },
  both:  { label: 'Read + Write', bgcolor: '#ede9fe', color: '#5b21b6' },
};

const DataStoreConfigAccordion = ({ agentName, value, onChange }) => {
  const configs = Array.isArray(value) ? value : [];
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [existingStats, setExistingStats] = useState({});

  useEffect(() => {
    let cancelled = false;
    dataStoreService.listNamespaces().then(
      (data) => {
        if (cancelled) return;
        const nss = (data?.namespaces) || [];
        setSuggestions(nss.map((n) => n.namespace));
        setExistingStats(Object.fromEntries(nss.map((n) => [n.namespace, n.recordCount])));
      },
      () => { /* ignore */ }
    );
    return () => { cancelled = true; };
  }, []);

  const usedNamespaces = new Set(configs.map((c) => c.namespace));

  const openAdd = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (cfg) => { setEditing(cfg); setDialogOpen(true); };

  const handleSave = (newCfg) => {
    if (editing) {
      onChange(configs.map((c) => (c.namespace === editing.namespace ? newCfg : c)));
    } else {
      onChange([...configs, newCfg]);
    }
    setDialogOpen(false);
  };

  const handleDelete = (ns) => {
    onChange(configs.filter((c) => c.namespace !== ns));
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Declare which data store namespaces this agent reads from or writes to.
        This metadata is advisory — the runtime doesn&apos;t block access — but it
        shows up in the editor&apos;s data flow preview and in the data store viewer
        so everyone can see which agents touch which data.
      </Typography>

      <FlowPreview agentName={agentName} configs={configs} />

      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>Configured namespaces</Typography>
        <Button
          size="small"
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={openAdd}
        >
          Add namespace
        </Button>
      </Box>

      {configs.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 3, textAlign: 'center' }}>
          <StorageIcon sx={{ fontSize: 32, color: 'text.secondary', mb: 1 }} />
          <Typography variant="body2" color="text.secondary">
            No namespaces configured yet.
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            Add one to document which data this agent depends on.
          </Typography>
        </Paper>
      ) : (
        <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#fafafa' }}>
                <TableCell>Namespace</TableCell>
                <TableCell>Access</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="right">Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {configs.map((c) => {
                const style = accessChipStyle[c.access] || accessChipStyle.both;
                const recordCount = existingStats[c.namespace];
                return (
                  <TableRow key={c.namespace} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 500 }}>
                        {c.namespace}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={style.label}
                        size="small"
                        sx={{ height: 20, fontSize: '0.7rem', bgcolor: style.bgcolor, color: style.color }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {c.description || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {recordCount != null ? (
                        <Chip
                          label={`${recordCount.toLocaleString()} record${recordCount === 1 ? '' : 's'}`}
                          size="small"
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      ) : (
                        <Chip
                          label="New"
                          size="small"
                          sx={{ height: 20, fontSize: '0.7rem', bgcolor: '#f1f5f9', color: '#475569' }}
                        />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit" arrow>
                        <IconButton size="small" onClick={() => openEdit(c)}>
                          <EditIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remove" arrow>
                        <IconButton size="small" onClick={() => handleDelete(c.namespace)}>
                          <DeleteOutlineIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}

      <ConfigDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
        initialConfig={editing}
        suggestions={suggestions}
        usedNamespaces={usedNamespaces}
      />
    </Box>
  );
};

DataStoreConfigAccordion.propTypes = {
  agentName: PropTypes.string,
  value: PropTypes.array,
  onChange: PropTypes.func.isRequired,
};

export default DataStoreConfigAccordion;
