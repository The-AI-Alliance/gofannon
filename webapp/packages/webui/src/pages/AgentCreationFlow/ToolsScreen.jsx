import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Paper,
  Alert,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { useAgentFlow } from './AgentCreationFlowContext';

const ToolsScreen = () => {
  const { tools, setTools } = useAgentFlow();
  const [currentToolUrl, setCurrentToolUrl] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleAddTool = () => {
    if (!currentToolUrl.trim()) {
      setError('Tool URL cannot be empty.');
      return;
    }
    try {
      new URL(currentToolUrl); // Validate URL format
    } catch (e) {
      setError('Invalid URL format.');
      return;
    }

    if (tools[currentToolUrl]) {
      setError('This URL is already added.');
      return;
    }

    setTools(prev => ({
      ...prev,
      [currentToolUrl]: [], // Value is an empty array as per requirement
    }));
    setCurrentToolUrl('');
    setError(null);
  };

  const handleDeleteTool = (urlToDelete) => {
    setTools(prev => {
      const newTools = { ...prev };
      delete newTools[urlToDelete];
      return newTools;
    });
    setError(null);
  };

  const handleContinue = () => {
    // Optionally add validation for at least one tool
    if (Object.keys(tools).length === 0) {
      setError('Please add at least one tool URL to continue.');
      return;
    }
    navigate('/create-agent/description');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 1: Enter Your Tools (MCP Server Addresses)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Enter full URLs for remote Model Context Protocol (MCP) servers your agent can use.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          fullWidth
          label="Tool URL (e.g., https://mcp.example.com)"
          variant="outlined"
          value={currentToolUrl}
          onChange={(e) => setCurrentToolUrl(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddTool();
            }
          }}
        />
        <Button variant="contained" onClick={handleAddTool}>
          Add
        </Button>
      </Box>

      {Object.keys(tools).length > 0 && (
        <List dense sx={{ border: '1px solid #ccc', borderRadius: 1, maxHeight: 200, overflow: 'auto', mb: 2 }}>
          {Object.keys(tools).map((url) => (
            <ListItem
              key={url}
              secondaryAction={
                <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteTool(url)}>
                  <DeleteIcon />
                </IconButton>
              }
            >
              <ListItemText primary={url} />
            </ListItem>
          ))}
        </List>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleContinue}
        fullWidth
      >
        Continue
      </Button>
    </Paper>
  );
};

export default ToolsScreen;
