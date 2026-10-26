import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Button,
  Tooltip,
  InputAdornment,
  Alert,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';

/**
 * Editor for an agent's per-run environment variables.
 *
 * Mirrors the existing SchemaEditor's pattern: it owns the row-level UI
 * (add/delete/edit) and pushes the full updated list back up via setEnvVars
 * on every change. The parent component is responsible for persisting the
 * field on save -- this component never calls the API directly.
 *
 * Values are masked by default (password-input style) with a per-row
 * reveal toggle. This is purely a frontend convenience to avoid shoulder-
 * surfing in shared screens; values are still sent in cleartext over the
 * (TLS-protected) save request and stored encrypted at rest by the
 * backend's Fernet key.
 *
 * Empty rows (no key) are filtered out before save by the parent's save
 * handler; this keeps the editor relaxed about trailing empty rows while
 * the user is mid-edit.
 */
const EnvVarsEditor = ({ envVars = [], setEnvVars }) => {
  // Per-row reveal toggle. Keyed by index because keys themselves can be
  // duplicated transiently while the user is typing.
  const [revealed, setRevealed] = useState({});

  const handleAdd = () => {
    setEnvVars([...envVars, { key: '', value: '' }]);
  };

  const handleRemove = (index) => {
    setEnvVars(envVars.filter((_, i) => i !== index));
    // Drop the reveal flag for the removed index and renumber the rest.
    const next = {};
    Object.entries(revealed).forEach(([k, v]) => {
      const i = parseInt(k, 10);
      if (i < index) next[i] = v;
      else if (i > index) next[i - 1] = v;
    });
    setRevealed(next);
  };

  const handleKeyChange = (index, value) => {
    const next = [...envVars];
    next[index] = { ...next[index], key: value };
    setEnvVars(next);
  };

  const handleValueChange = (index, value) => {
    const next = [...envVars];
    next[index] = { ...next[index], value };
    setEnvVars(next);
  };

  const toggleReveal = (index) => {
    setRevealed((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  // Detect duplicate keys (case-sensitive). os.getenv is case-sensitive on
  // Linux which is where the backend runs, so we flag duplicates as the
  // user types rather than letting them save a list where two rows fight
  // for the same key.
  const keyCounts = envVars.reduce((acc, { key }) => {
    if (key) acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const duplicates = Object.entries(keyCounts)
    .filter(([, count]) => count > 1)
    .map(([k]) => k);

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Key/value pairs that will be available to the agent's code at run time
        via <code>os.getenv("KEY")</code> or <code>os.environ["KEY"]</code>.
        Values are encrypted at rest. Other agents running in the same process
        do not see your env vars.
      </Typography>

      {duplicates.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Duplicate keys: {duplicates.map((k) => <code key={k} style={{ marginRight: 8 }}>{k}</code>)}
          {' '}-- only the last value for each key will be used at runtime.
        </Alert>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 2 }}>
        {envVars.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            No env vars configured. Click &ldquo;Add variable&rdquo; below to add one.
          </Typography>
        )}

        {envVars.map((row, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              gap: 1,
              alignItems: 'flex-start',
            }}
          >
            <TextField
              label="Key"
              value={row.key || ''}
              onChange={(e) => handleKeyChange(index, e.target.value)}
              placeholder="MY_API_KEY"
              size="small"
              sx={{ flex: '0 0 32%', fontFamily: 'monospace' }}
              InputProps={{ sx: { fontFamily: 'monospace' } }}
              error={duplicates.includes(row.key)}
            />
            <TextField
              label="Value"
              value={row.value || ''}
              onChange={(e) => handleValueChange(index, e.target.value)}
              type={revealed[index] ? 'text' : 'password'}
              size="small"
              sx={{ flex: 1, fontFamily: 'monospace' }}
              InputProps={{
                sx: { fontFamily: 'monospace' },
                endAdornment: (
                  <InputAdornment position="end">
                    <Tooltip title={revealed[index] ? 'Hide' : 'Reveal'}>
                      <IconButton
                        size="small"
                        onClick={() => toggleReveal(index)}
                        edge="end"
                      >
                        {revealed[index] ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </InputAdornment>
                ),
              }}
            />
            <Tooltip title="Remove this variable">
              <IconButton
                size="small"
                onClick={() => handleRemove(index)}
                sx={{ mt: 0.5 }}
                aria-label="remove env var"
              >
                <DeleteOutlineIcon />
              </IconButton>
            </Tooltip>
          </Box>
        ))}
      </Box>

      <Button
        variant="outlined"
        startIcon={<AddIcon />}
        onClick={handleAdd}
        size="small"
      >
        Add variable
      </Button>
    </Box>
  );
};

EnvVarsEditor.propTypes = {
  envVars: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      value: PropTypes.string,
    }),
  ),
  setEnvVars: PropTypes.func.isRequired,
};

export default EnvVarsEditor;
