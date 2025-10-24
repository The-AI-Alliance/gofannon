// webapp/packages/webui/src/pages/DemoCreationFlow/SelectModelScreen.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDemoFlow } from './DemoCreationFlowContext';
import chatService from '../../services/chatService';
import {
  Paper,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert
} from '@mui/material';
import ModelConfigDialog from '../../components/ModelConfigDialog';

const SelectModelScreen = () => {
  const { setModelConfig } = useDemoFlow();
  const navigate = useNavigate();

  const [dialogOpen, setDialogOpen] = useState(true);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelParamSchema, setModelParamSchema] = useState({});
  const [currentModelParams, setCurrentModelParams] = useState({});
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState(null);

  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      try {
        const data = await chatService.getProviders();
        setProviders(data);
        const firstProvider = Object.keys(data)[0];
        if (firstProvider) {
          setSelectedProvider(firstProvider);
          const firstModel = Object.keys(data[firstProvider].models)[0];
          if (firstModel) {
            setSelectedModel(firstModel);
            const params = data[firstProvider].models[firstModel].parameters;
            setModelParamSchema(params);
            const defaults = Object.fromEntries(
              Object.entries(params).map(([key, val]) => [key, val.default])
            );
            setCurrentModelParams(defaults);
          }
        }
      } catch (err) {
        setProvidersError(err.message || 'Failed to fetch providers');
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, []);

  const handleSave = () => {
    setModelConfig({
      provider: selectedProvider,
      model: selectedModel,
      parameters: currentModelParams,
    });
    setDialogOpen(false);
    navigate('/create-demo/canvas');
  };

  const handleClose = () => {
      setDialogOpen(false);
      navigate(-1); // Go back
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Step 2: Select a Model
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Choose the AI model that will generate the code for your demo application.
      </Typography>
      {loadingProviders && <CircularProgress />}
      {providersError && <Alert severity="error">{providersError}</Alert>}
      {!loadingProviders && !providersError && (
          <Button onClick={() => setDialogOpen(true)} variant="contained">
              Choose Model
          </Button>
      )}

      <ModelConfigDialog
        open={dialogOpen}
        onClose={handleClose}
        onSave={handleSave}
        title="Select Demo App Composer Model"
        providers={providers}
        selectedProvider={selectedProvider}
        setSelectedProvider={setSelectedProvider}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        modelParamSchema={modelParamSchema}
        setModelParamSchema={setModelParamSchema}
        currentModelParams={currentModelParams}
        setCurrentModelParams={setCurrentModelParams}
        loadingProviders={loadingProviders}
        providersError={providersError}
      />
    </Paper>
  );
};

export default SelectModelScreen;