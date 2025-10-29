// webapp/packages/webui/src/pages/DemoCreationFlow/CanvasScreen.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useDemoFlow } from './DemoCreationFlowContext';
import demoService from '../../services/demoService';
import config from '../../config';
import chatService from '../../services/chatService'; // Import chatService for getProviders
import agentService from '../../services/agentService'; // Import agentService for getDeployments
import ModelConfigDialog from '../../components/ModelConfigDialog'; // Reused
import DemoApiSelectionDialog from './DemoApiSelectionDialog'; // New Component

import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Alert,
  Stack,
  IconButton,
  Tooltip,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import SettingsIcon from '@mui/icons-material/Settings';
import ApiIcon from '@mui/icons-material/Api';
import Chip from '@mui/material/Chip';


const CanvasScreen = () => {
  const {
    selectedApis,
    setSelectedApis,
    modelConfig,
    setModelConfig,
    userPrompt,
    setUserPrompt,
    generatedCode,
    setGeneratedCode,
    appName,
    setAppName,
    description,
    setDescription,
  } = useDemoFlow();

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [iframeSrcDoc, setIframeSrcDoc] = useState('');
  const [isEditLoading, setIsEditLoading] = useState(false);
  const [editLoaded, setEditLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState('canvas'); // 'canvas' or 'code'

  // State for Model Configuration Dialog
  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [localSelectedProvider, setLocalSelectedProvider] = useState(''); // Local state for dialog
  const [localSelectedModel, setLocalSelectedModel] = useState(''); // Local state for dialog
  const [localModelParamSchema, setLocalModelParamSchema] = useState({}); // Local state for dialog
  const [localCurrentModelParams, setLocalCurrentModelParams] = useState({}); // Local state for dialog
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState(null);

  // State for API Selection Dialog
  const [isApiSelectionDialogOpen, setIsApiSelectionDialogOpen] = useState(false);

  const [generationThoughts, setGenerationThoughts] = useState(null);
  // Effect to load demo for editing
  useEffect(() => {
    const editDemoId = searchParams.get('edit');
    if (editDemoId && !editLoaded) {
      const loadDemoForEditing = async () => {
        setIsEditLoading(true);
        setError(null);
        try {
          const demoData = await demoService.getDemo(editDemoId);
          setSelectedApis(demoData.selectedApis);
          setModelConfig(demoData.modelConfig);
          setUserPrompt(demoData.userPrompt);
          setGeneratedCode(demoData.generatedCode);
          setAppName(demoData.name);
          setDescription(demoData.description);
          setEditLoaded(true);
        } catch (err) {
          setError(err.message || 'Failed to load demo for editing.');
        } finally {
          setIsEditLoading(false);
        }
      };
      loadDemoForEditing();
    } else {
        setIsEditLoading(false);
    }
  }, [searchParams, editLoaded, setSelectedApis, setModelConfig, setUserPrompt, setGeneratedCode, setAppName, setDescription]);
   
  // Redirect if essential context data is missing (not in edit mode)
  useEffect(() => {
    if (!isEditLoading && !modelConfig && selectedApis.length === 0 && !searchParams.get('edit')) {
      navigate('/create-demo/select-apis');
    }
  }, [modelConfig, selectedApis, navigate, isEditLoading, searchParams]);

  // Effect to fetch providers on component mount and initialize model config dialog's local state
  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      setProvidersError(null);
      try {
        const providersData = await chatService.getProviders();
        setProviders(providersData);
  
        // Initialize local dialog state with context's modelConfig, or first available model
        if (modelConfig) {
            setLocalSelectedProvider(modelConfig.provider);
            setLocalSelectedModel(modelConfig.model);
            const paramsSchema = providersData[modelConfig.provider]?.models[modelConfig.model]?.parameters || {};
            setLocalModelParamSchema(paramsSchema);
            setLocalCurrentModelParams(modelConfig.parameters);
        } else {
            const providerKeys = Object.keys(providersData);
            if (providerKeys.length > 0) {
                const defaultProvider = providerKeys[0];
                setLocalSelectedProvider(defaultProvider);
                const models = Object.keys(providersData[defaultProvider].models || {});
                if (models.length > 0) {
                    const defaultModel = models[0];
                    setLocalSelectedModel(defaultModel);
                    const modelParams = providersData[defaultProvider].models[defaultModel].parameters;
                    setLocalModelParamSchema(modelParams);
                    const defaultParams = {};
                    Object.keys(modelParams).forEach(key => {
                        defaultParams[key] = modelParams[key].default;
                    });
                    setLocalCurrentModelParams(defaultParams);
                }
            }
        }
      } catch (err) {
        setProvidersError('Failed to fetch AI providers: ' + err.message);
        console.error("Error fetching providers for demo creation:", err);
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, [modelConfig]); // Re-run if modelConfig changes (e.g., loaded from edit)


  const generateIframeContent = (code) => {
    const { html, css, js } = code;
    const apiBaseUrl = config.api.baseUrl;

    return `
      <html>
        <head>
          <style>${css}</style>
        </head>
        <body>
          ${html}
          <script>
            const API_BASE_URL = "${apiBaseUrl}";
          </script>
          <script type="module">
            try {
              ${js}
            } catch (e) {
              console.error("Error executing demo app script:", e);
              const errorDiv = document.createElement('div');
              errorDiv.style.position = 'fixed';
              errorDiv.style.bottom = '10px';
              errorDiv.style.left = '10px';
              errorDiv.style.padding = '10px';
              errorDiv.style.backgroundColor = 'red';
              errorDiv.style.color = 'white';
              errorDiv.style.zIndex = '9999';
              errorDiv.textContent = 'Error in script: ' + e.message;
              document.body.appendChild(errorDiv);
            }
          </script>
        </body>
      </html>
    `;
  };

  useEffect(() => {
    setIframeSrcDoc(generateIframeContent(generatedCode));
  }, [generatedCode]);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);

    if (!modelConfig) {
        setError('Please select a model for code generation.');
        setIsLoading(false);
        return;
    }
    if (selectedApis.length === 0) {
        setError('Please select at least one API for your demo app.');
        setIsLoading(false);
        return;
    }
    if (!userPrompt.trim()) {
        setError('Please describe your app to generate code.');
        setIsLoading(false);
        return;
    }

    try {
      const code = await demoService.generateDemoAppCode({
        userPrompt,
        selectedApis,
        modelConfig,
      });
      setGeneratedCode(code);
      setGenerationThoughts(response.thoughts);
      setActiveTab('canvas'); // Switch to canvas view after generation
    } catch (err) {
      setError(err.message || "Failed to generate code.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = () => {
    const editDemoId = searchParams.get('edit');
    if (editDemoId) {
        navigate(`/create-demo/save?edit=${editDemoId}`);
    } else {
        navigate('/create-demo/save');
    }
  };

  const handleOpenModelConfig = () => {
    // Sync local dialog state with context's modelConfig before opening
    if (modelConfig) {
      setLocalSelectedProvider(modelConfig.provider);
      setLocalSelectedModel(modelConfig.model);
      const paramsSchema = providers[modelConfig.provider]?.models[modelConfig.model]?.parameters || {};
      setLocalModelParamSchema(paramsSchema);
      setLocalCurrentModelParams(modelConfig.parameters);
    }
    setIsModelConfigOpen(true);
  };

  const handleSaveModelConfig = () => {
    setModelConfig({
      provider: localSelectedProvider,
      model: localSelectedModel,
      parameters: localCurrentModelParams,
    });
    setIsModelConfigOpen(false);
  };
  
  const handleSaveSelectedApis = (apis) => {
    setSelectedApis(apis);
    setIsApiSelectionDialogOpen(false);
  };

  const handleCodeChange = (part, value) => {
    setGeneratedCode(prev => ({ ...prev, [part]: value }));
  };

  const isModelSelected = localSelectedProvider && localSelectedModel;

  if (isEditLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 3, height: '85vh', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Create Demo App
      </Typography>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{mb: 2}}>{error}</Alert>}

      {/* Model Selector at the top */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Demo App Composer Model</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {loadingProviders ? (
            <CircularProgress size={20} />
          ) : isModelSelected ? (
            <Chip
              label={`${localSelectedProvider}/${localSelectedModel}`}
              color="primary"
              variant="outlined"
            />
          ) : (
            <Typography color="text.secondary">No model selected</Typography>
          )}
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={handleOpenModelConfig}
            disabled={loadingProviders || providersError}
          >
            {isModelSelected ? 'Change Model' : 'Choose Model'}
          </Button>
        </Box>
      </Box>

      {/* API/Tools Button */}
      <Box sx={{ mb: 2 }}>
        <Button
            variant="outlined"
            startIcon={<ApiIcon />}
            onClick={() => setIsApiSelectionDialogOpen(true)}
            disabled={loadingProviders}
            fullWidth
        >
            Manage APIs for Demo ({selectedApis.length} selected)
        </Button>
      </Box>
      
      <Divider sx={{ my: 2 }} />

      <Box sx={{ flexGrow: 1, display: 'flex', gap: 2, minHeight: 0 }}>
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Describe your app"
            multiline
            rows={10}
            fullWidth
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            placeholder="e.g., 'Create a simple form with a text input and a button. When the button is clicked, call the 'my_api' API with the input text and display the result.'"
          />
          <Stack direction="row" spacing={2} justifyContent="flex-end">
            <Button
              variant="contained"
              onClick={handleGenerate}
              disabled={isLoading || !userPrompt || !isModelSelected || selectedApis.length === 0}
              startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
            >
              {isLoading ? 'Generating...' : 'Generate'}
            </Button>
            <Tooltip title={!generatedCode.html ? "Generate code before saving" : ""}>
                <span>
                    <Button
                        variant="outlined"
                        onClick={handleSave}
                        startIcon={<SaveIcon />}
                        disabled={!generatedCode.html}
                    >
                        Save App
                    </Button>
                </span>
            </Tooltip>
          </Stack>
        </Box>
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid grey', borderRadius: 1 }}>
          <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} aria-label="canvas-code tabs" sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab value="canvas" label="Canvas" />
            <Tab value="code" label="Code" />
            {generationThoughts && <Tab value="thoughts" label="Thoughts" />}
          </Tabs>

          <Box sx={{ flexGrow: 1, p: 1, overflow: 'auto' }}>
            {activeTab === 'canvas' && (
              <iframe
                srcDoc={iframeSrcDoc}
                title="Demo App Preview"
                sandbox="allow-scripts allow-forms allow-popups allow-modals allow-same-origin"
                width="100%"
                height="100%"
                style={{ border: 'none' }}
              />
            )}
            {activeTab === 'code' && (
              <Stack spacing={2} sx={{ height: '100%' }}>
                <TextField
                  fullWidth
                  multiline
                  minRows={8}
                  label="HTML"
                  value={generatedCode.html}
                  onChange={(e) => handleCodeChange('html', e.target.value)}
                  InputProps={{
                    style: { fontFamily: 'monospace', fontSize: '0.9rem' }
                  }}
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={8}
                  label="CSS"
                  value={generatedCode.css}
                  onChange={(e) => handleCodeChange('css', e.target.value)}
                  InputProps={{
                    style: { fontFamily: 'monospace', fontSize: '0.9rem' }
                  }}
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={8}
                  label="JavaScript"
                  value={generatedCode.js}
                  onChange={(e) => handleCodeChange('js', e.target.value)}
                  InputProps={{
                    style: { fontFamily: 'monospace', fontSize: '0.9rem' }
                  }}
                />
              </Stack>
            )}
             {activeTab === 'thoughts' && (
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.paper', height: '100%' }}>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
                        {JSON.stringify(generationThoughts, null, 2)}
                    </pre>
                </Paper>
            )}
          </Box>
        </Box>
      </Box>

      <ModelConfigDialog
        open={isModelConfigOpen}
        onClose={() => setIsModelConfigOpen(false)}
        onSave={handleSaveModelConfig}
        title="Configure Demo App Composer Model"
        providers={providers}
        selectedProvider={localSelectedProvider}
        setSelectedProvider={setLocalSelectedProvider}
        selectedModel={localSelectedModel}
        setSelectedModel={setLocalSelectedModel}
        modelParamSchema={localModelParamSchema}
        setModelParamSchema={setLocalModelParamSchema}
        currentModelParams={localCurrentModelParams}
        setCurrentModelParams={setLocalCurrentModelParams}
        loadingProviders={loadingProviders}
        providersError={providersError}
      />

      <DemoApiSelectionDialog
        open={isApiSelectionDialogOpen}
        onClose={() => setIsApiSelectionDialogOpen(false)}
        existingSelectedApis={selectedApis}
        onSaveSelectedApis={handleSaveSelectedApis}
      />
    </Paper>
  );
};

export default CanvasScreen;