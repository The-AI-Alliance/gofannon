import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Button, Paper, TextField, Stack } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PublishIcon from '@mui/icons-material/Publish';
import { useAgentFlow } from './AgentCreationFlowContext';

const CodeEditorScreen = () => {
  const { generatedCode } = useAgentFlow();
  const navigate = useNavigate();

  const handleRunInSandbox = () => {
    // As per requirements: "For now simply navigate to the Chat endpoint"
    navigate('/chat');
  };

  const handleDeploy = () => {
    navigate('/create-agent/deploy');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 900, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 4: Agent Code
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        This is the generated Python code for your agent. (Editor disabled for POC)
      </Typography>

      <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default', mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6">Python Code</Typography>
          <Button size="small" startIcon={<EditIcon />} disabled>Edit</Button>
        </Box>
        <TextField
          fullWidth
          multiline
          minRows={15}
          maxRows={25}
          value={generatedCode}
          InputProps={{
            readOnly: true,
            style: {
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              color: 'lightcoral', // Styling for code to distinguish it
              backgroundColor: '#1e1e1e',
            }
          }}
          sx={{ '& .MuiInputBase-root': { p: 1 } }}
        />
      </Box>

      <Stack direction="row" spacing={2} justifyContent="flex-end">
        <Button
          variant="outlined"
          startIcon={<PlayArrowIcon />}
          onClick={handleRunInSandbox}
        >
          Run in Sandbox
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={<PublishIcon />}
          onClick={handleDeploy}
        >
          Deploy
        </Button>
      </Stack>
    </Paper>
  );
};

export default CodeEditorScreen;
