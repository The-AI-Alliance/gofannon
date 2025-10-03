// webapp/packages/webui/src/pages/AgentCreationFlow/ToolsSelectionDialog.jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControlLabel,
  Checkbox,
  FormGroup,
  CircularProgress,
  Typography,
  Alert,
  Box,
} from '@mui/material';
import mcpService from '../../services/mcpService';

const ToolsSelectionDialog = ({
  open,
  onClose,
  mcpUrl,
  existingSelectedTools, // Array of tool names already selected for this MCP server
  onSaveSelectedTools,  // Callback to save selected tool names
}) => {
  const [availableTools, setAvailableTools] = useState([]); // All tools fetched from the MCP server
  const [selectedToolNames, setSelectedToolNames] = useState(new Set()); // Tool names currently checked in the dialog
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && mcpUrl) {
      setLoading(true);
      setError(null);
      setSelectedToolNames(new Set(existingSelectedTools)); // Initialize with existing selections
      
      mcpService.listTools(mcpUrl)
        .then(tools => {
          setAvailableTools(tools);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message || 'Failed to fetch tools.');
          setLoading(false);
          setAvailableTools([]); // Clear tools on error
        });
    } else {
      // Reset state when dialog closes
      setAvailableTools([]);
      setSelectedToolNames(new Set());
      setError(null);
    }
  }, [open, mcpUrl, existingSelectedTools]); // Re-run effect when these props change

  const handleCheckboxChange = (toolName) => {
    setSelectedToolNames(prev => {
      const newSet = new Set(prev);
      if (newSet.has(toolName)) {
        newSet.delete(toolName);
      } else {
        newSet.add(toolName);
      }
      return newSet;
    });
  };

  const handleSave = () => {
    onSaveSelectedTools(mcpUrl, Array.from(selectedToolNames));
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Select Tools from {mcpUrl}</DialogTitle>
      <DialogContent>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
            <CircularProgress />
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ my: 2 }}>
            {error}
          </Alert>
        )}
        {!loading && !error && availableTools.length === 0 && (
          <Typography sx={{ my: 2 }}>No tools found on this server.</Typography>
        )}
        {!loading && !error && availableTools.length > 0 && (
          <FormGroup>
            {availableTools.map((tool) => (
              <FormControlLabel
                key={tool.name}
                control={
                  <Checkbox
                    checked={selectedToolNames.has(tool.name)}
                    onChange={() => handleCheckboxChange(tool.name)}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body1">{tool.name}</Typography>
                    {tool.description && (
                      <Typography variant="caption" color="text.secondary">
                        {tool.description}
                      </Typography>
                    )}
                  </Box>
                }
              />
            ))}
          </FormGroup>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={loading}>
          Save Selected Tools
        </Button>
      </DialogActions>
    </Dialog>
  );
};

ToolsSelectionDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  mcpUrl: PropTypes.string.isRequired,
  existingSelectedTools: PropTypes.arrayOf(PropTypes.string).isRequired,
  onSaveSelectedTools: PropTypes.func.isRequired,
};

export default ToolsSelectionDialog;
