// webapp/packages/webui/src/pages/DemoCreationFlow/SaveDemoScreen.jsx
import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import { useDemoFlow } from './DemoCreationFlowContext';
import demoService from '../../services/demoService';

const SaveDemoScreen = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editDemoId = searchParams.get('edit');  
  const demoFlowContext = useDemoFlow();
  
  const { appName, setAppName, description, setDescription } = demoFlowContext;
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    if (!appName.trim()) {
      setError('App name is required.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    const demoData = {
      name: appName,
      description,
      selectedApis: demoFlowContext.selectedApis,
      modelConfig: demoFlowContext.modelConfig,
      userPrompt: demoFlowContext.userPrompt,
      generatedCode: demoFlowContext.generatedCode,
    };

    try {
      if (editDemoId) {
        await demoService.updateDemo(editDemoId, demoData);
      } else {
        await demoService.saveDemo(demoData);
      }
      setSuccess(true);
      setTimeout(() => navigate('/demo-apps'), 1500);
    } catch (err) {
      setError(err.message || 'Failed to save demo app.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom> {editDemoId ? 'Update Your Demo App' : 'Save Your Demo App'} </Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{`App ${editDemoId ? 'updated' : 'saved'}! Redirecting...`}</Alert>}

      <TextField
        fullWidth
        required
        label="App Name"
        value={appName}
        onChange={(e) => setAppName(e.target.value)}
        sx={{ mb: 2 }}
        disabled={isLoading}
      />
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Description (Optional)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        sx={{ mb: 3 }}
        disabled={isLoading}
      />
      <Button
        fullWidth
        variant="contained"
        onClick={handleSave}
        disabled={isLoading || !appName.trim()}
        startIcon={isLoading ? <CircularProgress size={20} /> : <SaveIcon />}
      >
        {isLoading ? 'Saving...' : (editDemoId ? 'Update App' : 'Save App')}
      </Button>
    </Paper>
  );
};

export default SaveDemoScreen;