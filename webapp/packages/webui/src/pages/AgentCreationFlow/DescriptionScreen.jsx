import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, Paper } from '@mui/material';
import { useAgentFlow } from './AgentCreationFlowContext';

const DescriptionScreen = () => {
  const { description, setDescription } = useAgentFlow();
  const navigate = useNavigate();

  const handleContinue = () => {
    navigate('/create-agent/schemas');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 2: What Will This Agent Do?
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Provide a detailed description of your agent's purpose and functionality.
      </Typography>

      <TextField
        fullWidth
        multiline
        rows={6}
        label="Agent Description"
        variant="outlined"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        sx={{ mb: 3 }}
        placeholder="E.g., 'This agent will monitor stock prices, summarize daily news, and provide recommendations based on user queries.'"
      />

      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
        <Button
          variant="outlined"
          disabled // Disabled as per requirement for now
        >
          Do I Need Any More Tools?
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleContinue}
        >
          Continue
        </Button>
      </Box>
    </Paper>
  );
};

export default DescriptionScreen;
