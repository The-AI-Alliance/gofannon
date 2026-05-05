import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import StorageIcon from '@mui/icons-material/Storage';
import dataStoreService from '../services/dataStoreService';

// Human-readable byte formatting. Matches the "1.2 MB" / "340 KB" style in
// the mockup.
const formatBytes = (n) => {
  if (n == null) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// Relative time from an ISO timestamp. Matches "2h ago" / "1d ago".
const relativeTime = (iso) => {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return 'just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  const d = Math.floor(diffSec / 86400);
  if (d < 7) return `${d}d ago`;
  const w = Math.floor(d / 7);
  if (w < 5) return `${w}w ago`;
  return new Date(iso).toLocaleDateString();
};

const DataStoresPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({ namespaces: [], totalRecordCount: 0, totalSizeBytes: 0 });
  const [clearTarget, setClearTarget] = useState(null); // namespace name or null
  const [clearBusy, setClearBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const resp = await dataStoreService.listNamespaces();
      setData(resp || { namespaces: [], totalRecordCount: 0, totalSizeBytes: 0 });
    } catch (err) {
      setError(err.message || 'Failed to load data stores.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleConfirmClear = async () => {
    if (!clearTarget) return;
    setClearBusy(true);
    try {
      await dataStoreService.clearNamespace(clearTarget);
      setClearTarget(null);
      await load();
    } catch (err) {
      setError(err.message || 'Failed to clear namespace.');
    } finally {
      setClearBusy(false);
    }
  };

  const namespaces = data.namespaces || [];

  return (
    <Box sx={{ p: 3, maxWidth: 1400, margin: '0 auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton size="small" onClick={() => navigate('/')} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 600, flexGrow: 1 }}>
          Data Stores
        </Typography>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Box>

      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
          <Typography variant="caption" color="text.secondary">Namespaces</Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>{namespaces.length}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
          <Typography variant="caption" color="text.secondary">Records</Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {(data.totalRecordCount || 0).toLocaleString()}
          </Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
          <Typography variant="caption" color="text.secondary">Total size</Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {formatBytes(data.totalSizeBytes || 0)}
          </Typography>
        </Paper>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Paper sx={{ overflow: 'hidden' }}>
        <TableContainer>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : namespaces.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <StorageIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
              <Typography color="text.secondary" variant="body2">
                No data stores yet. Namespaces are created automatically the first time an agent writes data.
              </Typography>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#fafafa' }}>
                  <TableCell>Namespace</TableCell>
                  <TableCell>Agents</TableCell>
                  <TableCell align="right">Records</TableCell>
                  <TableCell align="right">Size</TableCell>
                  <TableCell>Updated</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {namespaces.map((ns) => (
                  <TableRow
                    key={ns.namespace}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/data-stores/${encodeURIComponent(ns.namespace)}`)}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>
                        {ns.namespace}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {(ns.agents || []).slice(0, 3).map((a) => (
                          <Chip
                            key={a}
                            label={a}
                            size="small"
                            sx={{ height: 20, fontSize: '0.7rem', bgcolor: '#e0f2fe', color: '#075985' }}
                          />
                        ))}
                        {(ns.agents || []).length > 3 && (
                          <Chip
                            label={`+${ns.agents.length - 3}`}
                            size="small"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        {(ns.recordCount || 0).toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" color="text.secondary">
                        {formatBytes(ns.sizeBytes)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {relativeTime(ns.updatedAt)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="Browse" arrow>
                        <IconButton
                          size="small"
                          onClick={() => navigate(`/data-stores/${encodeURIComponent(ns.namespace)}`)}
                        >
                          <VisibilityIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Clear namespace (delete all records)" arrow>
                        <IconButton
                          size="small"
                          onClick={() => setClearTarget(ns.namespace)}
                        >
                          <DeleteOutlineIcon sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      </Paper>

      <Dialog open={Boolean(clearTarget)} onClose={() => !clearBusy && setClearTarget(null)}>
        <DialogTitle>Clear namespace?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This permanently deletes every record in the{' '}
            <code>{clearTarget}</code> namespace. Agents that depend on this
            data will lose access. This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearTarget(null)} disabled={clearBusy}>Cancel</Button>
          <Button
            onClick={handleConfirmClear}
            color="error"
            variant="contained"
            disabled={clearBusy}
            startIcon={clearBusy ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {clearBusy ? 'Clearing…' : 'Clear'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DataStoresPage;
