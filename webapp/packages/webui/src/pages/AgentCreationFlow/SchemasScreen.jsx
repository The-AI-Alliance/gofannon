import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Chip,
  CircularProgress
} from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import EditIcon from '@mui/icons-material/Edit';
import SettingsIcon from '@mui/icons-material/Settings'; 
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import { useAgentFlow } from './AgentCreationFlowContext';
import chatService from '../../services/chatService'; // Re-use chatService to fetch providers
import agentService from '../../services/agentService'; // Import the new agent service
import ModelConfigDialog from '../../components/ModelConfigDialog'; // Import the new component

const SchemasScreen = () => {
  const { tools, description, inputSchema, outputSchema, setGeneratedCode, invokableModels, setInvokableModels } = useAgentFlow();
  const navigate = useNavigate();

  // State for Model Configuration
  const [modelConfigDialogOpen, setModelConfigDialogOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelParamSchema, setModelParamSchema] = useState({});
  const [currentModelParams, setCurrentModelParams] = useState({});
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState(null);

  // State for build process
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildError, setBuildError] = useState(null);

  
  // State for the invokable models dialog
  const [invokableModelDialogOpen, setInvokableModelDialogOpen] = useState(false);
  const [currentInvokableProvider, setCurrentInvokableProvider] = useState('');
  const [currentInvokableModel, setCurrentInvokableModel] = useState('');
  const [currentInvokableSchema, setCurrentInvokableSchema] = useState({});
  const [currentInvokableParams, setCurrentInvokableParams] = useState({});

  // Fetch providers on component mount
  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      setProvidersError(null);
      try {
        const providersData = await chatService.getProviders();
        setProviders(providersData);
  
        const providerKeys = Object.keys(providersData);
        if (providerKeys.length > 0) {
          const defaultProvider = providerKeys[0];
          setSelectedProvider(defaultProvider);
  
          const models = Object.keys(providersData[defaultProvider].models);
          if (models.length > 0) {
            const defaultModel = models[0];
            setSelectedModel(defaultModel);
            const modelParams = providersData[defaultProvider].models[defaultModel].parameters;
            setModelParamSchema(modelParams);
  
            const defaultParams = {};
            Object.keys(modelParams).forEach(key => {
              defaultParams[key] = modelParams[key].default;
            });
            setCurrentModelParams(defaultParams);
          } else {
            setSelectedModel('');
            setModelParamSchema({});
            setCurrentModelParams({});
          }
        } else {
          setProvidersError('No AI providers found.');
        }
      } catch (err) {
        setProvidersError('Failed to fetch AI providers: ' + err.message);
        console.error("Error fetching providers for agent creation:", err);
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, []);

  const handleBuild = async () => {
    if (!selectedProvider || !selectedModel) {
      setProvidersError('Please select a model for code generation.');
      return;
    }
    setBuildError(null);
    setIsBuilding(true);

    const agentConfig = {
      tools,
      description,
      inputSchema,
      outputSchema,
      invokableModels,
      modelConfig: {
        provider: selectedProvider,
        model: selectedModel,
        parameters: currentModelParams,
      },
    };

    try {
      const response = await agentService.generateCode(agentConfig);
      setGeneratedCode(response.code);
      navigate('/create-agent/code');
    } catch (err) {
      setBuildError(err.message || 'An unexpected error occurred while building the agent.');
    } finally {
      setIsBuilding(false);
    }
  };

  const handleAddInvokableModel = () => {
    const newModel = {
        provider: currentInvokableProvider,
        model: currentInvokableModel,
        parameters: currentInvokableParams,
    };
    setInvokableModels(prev => [...prev, newModel]);
    setInvokableModelDialogOpen(false);
  };
  
  const handleDeleteInvokableModel = (index) => {
    setInvokableModels(invokableModels.filter((_, i) => i !== index));
  };

  const openAddModelDialog = () => {
    // Reset to defaults before opening
    setCurrentInvokableProvider(selectedProvider);
    setCurrentInvokableModel(selectedModel);
    setInvokableModelDialogOpen(true);
  };
  
  const isModelSelected = selectedProvider && selectedModel;

  return (
    <Paper sx={{ p: 3, maxWidth: 800, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 3: Define Input/Output JSON (Optional)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        By default, input has `inputText` and output has `outputText`. You can
        optionally define more complex JSON structures here. (Edit disabled for POC)
      </Typography>

      {providersError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setProvidersError(null)}>
          {providersError}
        </Alert>
      )}

      {buildError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setBuildError(null)}>
          {buildError}
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6\">Input JSON Schema</Typography>
              <Button size="small" startIcon={<EditIcon />} disabled>Edit</Button>
            </Box>
            <Box sx={{ bgcolor: 'grey.900', p: 1, borderRadius: 1, overflowX: 'auto' }}>
              <code style={{ whiteSpace: 'pre-wrap', color: 'lightgreen', display: 'block' }}>
                {JSON.stringify(inputSchema, null, 2)}
              </code>
            </Box>
          </Box>
        </Grid>
        <Grid item xs={12} md={6}>
          <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6\">Output JSON Schema</Typography>
              <Button size="small" startIcon={<EditIcon />} disabled>Edit</Button>
            </Box>
            <Box sx={{ bgcolor: 'grey.900', p: 1, borderRadius: 1, overflowX: 'auto' }}>
              <code style={{ whiteSpace: 'pre-wrap', color: 'lightgreen', display: 'block' }}>
                {JSON.stringify(outputSchema, null, 2)}
              </code>
            </Box>
          </Box>
        </Grid>
      </Grid>

      <Divider sx={{ my: 3 }} />

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Models the Agent Can Invoke</Typography>
        <Button
            variant="outlined"
            startIcon={<AddCircleOutlineIcon />}
            onClick={openAddModelDialog}
            disabled={loadingProviders || providersError}
        >
            Add Model
        </Button>
      </Box>

      {invokableModels.length === 0 ? (
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          No invokable models added. The agent will not be able to call other LLMs.
        </Typography>
      ) : (
        <List dense sx={{ mb: 3, border: '1px solid #ddd', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
          {invokableModels.map((model, index) => (
            <ListItem
              key={index}
              secondaryAction={
                <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteInvokableModel(index)}>
                  <DeleteIcon />
                </IconButton>
              }
            >
              <ListItemText
                primary={`${model.provider}/${model.model}`}
                secondary={
                  Object.keys(model.parameters).length > 0
                    ? `Params: ${Object.keys(model.parameters).join(', ')}`
                    : 'Default parameters'
                }
              />
            </ListItem>
          ))}
        </List>
      )}

      <Divider sx={{ my: 3 }} />

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h6">Model for Code Generation</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {loadingProviders ? (
            <CircularProgress size={20} />
          ) : isModelSelected ? (
            <Chip 
              label={`${selectedProvider}/${selectedModel}`}
              color="secondary" 
              variant="outlined"
            />
          ) : (
            <Typography color="text.secondary">No model selected</Typography>
          )}
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setModelConfigDialogOpen(true)}
            disabled={loadingProviders || providersError}
          >
            {isModelSelected ? 'Change Model' : 'Choose Model'}
          </Button>
        </Box>
      </Box>

      <Button
        variant="contained"
        color="primary"
        onClick={handleBuild}
        fullWidth
        startIcon={isBuilding ? <CircularProgress size={20} color="inherit" /> : <CodeIcon />}
        disabled={!isModelSelected || isBuilding}
      >
        {isBuilding ? 'Building...' : 'Build Agent Code'}
      </Button>

      <ModelConfigDialog
        open={invokableModelDialogOpen}
        onClose={() => setInvokableModelDialogOpen(false)}
        onSave={handleAddInvokableModel}
        title="Add an Invokable Model for the Agent"
        providers={providers}
        selectedProvider={currentInvokableProvider}
        setSelectedProvider={setCurrentInvokableProvider}
        selectedModel={currentInvokableModel}
        setSelectedModel={setCurrentInvokableModel}
        modelParamSchema={currentInvokableSchema}
        setModelParamSchema={setCurrentInvokableSchema}
        currentModelParams={currentInvokableParams}
        setCurrentModelParams={setCurrentInvokableParams}
        loadingProviders={loadingProviders}
        providersError={providersError}
      />

      <ModelConfigDialog
        open={modelConfigDialogOpen}
        onClose={() => setModelConfigDialogOpen(false)}
        title="Configure Agent Code Generation Model"
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

export default SchemasScreen;
