import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  List,
  Chip,
  ListItem,
  ListItemText,
  ListItemIcon,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  IconButton,
  DialogTitle,
  Grid,
  Divider,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  InputAdornment,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import WebIcon from '@mui/icons-material/Web';
import ArticleIcon from '@mui/icons-material/Article';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import RefreshIcon from '@mui/icons-material/Refresh';
import CodeIcon from '@mui/icons-material/Code';
import AddIcon from '@mui/icons-material/Add';
import BuildIcon from '@mui/icons-material/Build';
import UploadFileIcon from '@mui/icons-material/UploadFile';

import { useAgentFlow } from './AgentCreationFlow/AgentCreationFlowContextValue';
import agentService from '../services/agentService';
import chatService from '../services/chatService';
import CodeEditor from '../components/CodeEditor';
import SpecViewerModal from '../components/SpecViewerModal';
import ModelConfigDialog from '../components/ModelConfigDialog';
import SchemaEditor from '../components/SchemaEditor';
import ToolsSelectionDialog from './AgentCreationFlow/ToolsSelectionDialog';

const ViewAgent = () => {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const agentFlowContext = useAgentFlow();

  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [deleteConfirmationOpen, setDeleteConfirmationOpen] = useState(false);  
  const [viewingSpec, setViewingSpec] = useState({ open: false, name: '', content: '' });
  
  // State for deployment
  const [deployment, setDeployment] = useState(null);
  const [isUndeploying, setIsUndeploying] = useState(false);

  // State for model management
  const [providers, setProviders] = useState({});
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const [modelDialogMode, setModelDialogMode] = useState('invokable');
  // For invokable models: index being edited in-place, or null for "add new".
  // Composer is always a single config so it doesn't need an index.
  const [editingInvokableIndex, setEditingInvokableIndex] = useState(null);
  const [dialogProvider, setDialogProvider] = useState('');
  const [dialogModel, setDialogModel] = useState('');
  const [dialogParamSchema, setDialogParamSchema] = useState({});
  const [dialogParams, setDialogParams] = useState({});
  const [dialogBuiltInTool, setDialogBuiltInTool] = useState('');

  // State for tools management
  const [toolsTabIndex, setToolsTabIndex] = useState(0);
  const [currentToolUrl, setCurrentToolUrl] = useState('');
  const [toolsDialog, setToolsDialog] = useState({ open: false, mcpUrl: '', existingSelectedTools: [] });
  const [specUrl, setSpecUrl] = useState('');
  const [isFetchingSpec, setIsFetchingSpec] = useState(false);
  const [availableAgents, setAvailableAgents] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState('');

  const isCreationFlow = !agentId;
  const hasCode = agent?.code && agent.code.trim() !== '';

  // Session storage key for persisting edits
  const sessionStorageKey = agentId ? `agent_edit_${agentId}` : 'agent_create_draft';

  // Track if initial load has been done for creation flow
  const initialLoadDone = React.useRef(false);

  useEffect(() => {
    if (agentId) {
        const fetchDeploymentStatus = async () => {
            try {
                const status = await agentService.getDeployment(agentId);
                setDeployment(status);
            } catch {
                const deploymentError = 'Could not fetch deployment status.';
                setError(prev => prev ? `${prev}\n${deploymentError}` : deploymentError);
            }
        };
        fetchDeploymentStatus();
    }
  }, [agentId]);

  // Fetch providers for model selection
  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      try {
        const providersData = await chatService.getProviders();
        setProviders(providersData);
        const defaultProvider = Object.keys(providersData)[0];
        if (defaultProvider) {
          setDialogProvider(defaultProvider);
          const models = Object.keys(providersData[defaultProvider]?.models || {});
          if (models.length > 0) {
            setDialogModel(models[0]);
          }
        }
      } catch (err) {
        console.error('Error fetching providers:', err);
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, []);

  // Fetch available agents when Gofannon tab is selected
  useEffect(() => {
    const fetchAgents = async () => {
      setLoadingAgents(true);
      try {
        const agents = await agentService.getAgents();
        // Filter out current agent if editing
        const filtered = agentId ? agents.filter(a => a._id !== agentId) : agents;
        setAvailableAgents(filtered);
      } catch (err) {
        console.error('Failed to load available agents:', err);
      } finally {
        setLoadingAgents(false);
      }
    };
    if (toolsTabIndex === 2) {
      fetchAgents();
    }
  }, [toolsTabIndex, agentId]);

  // Persist agent edits to sessionStorage when agent state changes
  useEffect(() => {
    if (agent && !loading) {
      sessionStorage.setItem(sessionStorageKey, JSON.stringify(agent));
    }
  }, [agent, loading, sessionStorageKey]);

  const loadAgentData = useCallback(async () => {
    if (isCreationFlow && initialLoadDone.current) {
      return;
    }
    
    setError(null);
    setLoading(true);
    
    try {
      // If starting fresh (from Create button), clear any old draft
      if (location.state?.fresh && isCreationFlow) {
        sessionStorage.removeItem(sessionStorageKey);
      }
      
      // Check sessionStorage for unsaved edits (only if not starting fresh)
      const savedEdits = !location.state?.fresh ? sessionStorage.getItem(sessionStorageKey) : null;
      if (savedEdits) {
        try {
          const parsed = JSON.parse(savedEdits);
          setAgent(parsed);
          if (isCreationFlow) {
            initialLoadDone.current = true;
          }
          setLoading(false);
          return;
        } catch (e) {
          console.warn('Failed to parse saved edits from sessionStorage:', e);
          sessionStorage.removeItem(sessionStorageKey);
        }
      }

      if (isCreationFlow) {
        setAgent({
          name: agentFlowContext.friendlyName || '',
          description: agentFlowContext.description || '',
          tools: agentFlowContext.tools || {},
          swaggerSpecs: agentFlowContext.swaggerSpecs || [],
          gofannonAgents: agentFlowContext.gofannonAgents || [],
          code: agentFlowContext.generatedCode || '',
          inputSchema: agentFlowContext.inputSchema || { inputText: "string" },
          outputSchema: agentFlowContext.outputSchema || { outputText: "string" },
          invokableModels: agentFlowContext.invokableModels || [],
          composerModelConfig: agentFlowContext.composerModelConfig,
          docstring: agentFlowContext.docstring || '',
          friendlyName: agentFlowContext.friendlyName || '',
        });
        initialLoadDone.current = true;

      } else {
        const data = await agentService.getAgent(agentId);
        
        if (data.gofannonAgents && data.gofannonAgents.length > 0) {
            const allAgents = await agentService.getAgents();
            const agentMap = new Map(allAgents.map(a => [a._id, a.name]));
            data.gofannonAgents = data.gofannonAgents.map(id => ({
                id,
                name: agentMap.get(id) || id,
            }));
        }
        
        setAgent(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [agentId, isCreationFlow, sessionStorageKey, location.state]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadAgentData();
  }, [loadAgentData]);

  // Sync helper for creation flow
  const syncToContext = useCallback((field, value) => {
    if (!isCreationFlow) return;
    switch (field) {
      case 'description': agentFlowContext.setDescription(value); break;
      case 'code': agentFlowContext.setGeneratedCode(value); break;
      case 'tools': agentFlowContext.setTools(value); break;
      case 'swaggerSpecs': agentFlowContext.setSwaggerSpecs(value); break;
      case 'gofannonAgents': agentFlowContext.setGofannonAgents(value); break;
      case 'inputSchema': agentFlowContext.setInputSchema(value); break;
      case 'outputSchema': agentFlowContext.setOutputSchema(value); break;
      case 'invokableModels': agentFlowContext.setInvokableModels(value); break;
      case 'composerModelConfig': agentFlowContext.setComposerModelConfig(value); break;
      default: break;
    }
  }, [isCreationFlow, agentFlowContext]);

  const handleRunInSandbox = () => {
    if (agentId) {
      navigate(`/agent/${agentId}/sandbox`);
    } else {
      navigate('/create-agent/sandbox');
    }
  };

  const handleDeploy = () => {
    if (agentId) {
      navigate(`/agent/${agentId}/deploy`);
    } else {
      navigate('/create-agent/deploy');
    }
  };

  const handleUpdateAgent = async () => {
    if (!agentId || !agent) return;
    setError(null);
    setSuccessMessage('');
    setIsSaving(true);

    try {
      // Keep friendlyName in lockstep with name on every save so the
      // deployment slug never drifts from the display name.
      const canonicalName = sanitizeAgentName(agent.name);
      const updatePayload = {
        name: canonicalName,
        description: agent.description,
        code: agent.code,
        tools: agent.tools,
        swaggerSpecs: agent.swaggerSpecs,
        gofannonAgents: agent.gofannonAgents?.map(ga => typeof ga === 'string' ? ga : ga.id),
        inputSchema: agent.inputSchema,
        outputSchema: agent.outputSchema,
        invokableModels: agent.invokableModels,
        composerModelConfig: agent.composerModelConfig,
        docstring: agent.docstring,
        friendlyName: canonicalName,
      };
      await agentService.updateAgent(agentId, updatePayload);
      setSuccessMessage('Agent updated successfully!');
      // Clear session storage since changes are now saved to database
      sessionStorage.removeItem(sessionStorageKey);
    } catch (err) {
      setError(err.message || 'Failed to update agent.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNewAgent = async () => {
    if (!agent) return;
    
    // Validate required fields
    if (!agent.name || !agent.name.trim()) {
      setError('Agent name is required. Set one in the Name & Description section.');
      return;
    }
    if (!agent.description || !agent.description.trim()) {
      setError('Agent description is required.');
      return;
    }
    if (!agent.code || !agent.code.trim()) {
      setError('Agent code is required. Please generate code before saving.');
      return;
    }

    setError(null);
    setSuccessMessage('');
    setIsSaving(true);

    try {
      // name is the canonical identifier; friendlyName is always kept
      // identical so the deployment URL slug matches.
      const canonicalName = sanitizeAgentName(agent.name);
      const agentData = {
        name: canonicalName,
        description: agent.description,
        code: agent.code,
        tools: agent.tools,
        swaggerSpecs: agent.swaggerSpecs,
        gofannonAgents: agent.gofannonAgents?.map(ga => typeof ga === 'string' ? ga : ga.id),
        inputSchema: agent.inputSchema,
        outputSchema: agent.outputSchema,
        invokableModels: agent.invokableModels,
        composerModelConfig: agent.composerModelConfig,
        docstring: agent.docstring,
        friendlyName: canonicalName,
      };
      const savedAgent = await agentService.saveAgent(agentData);
      setSuccessMessage('Agent saved successfully!');
      // Clear session storage since agent is now saved
      sessionStorage.removeItem(sessionStorageKey);
      // Stay on the agent: navigate to the persisted detail page (replace so
      // Back doesn't return to the creation flow), not home.
      if (savedAgent && savedAgent._id) {
        navigate(`/agent/${savedAgent._id}`, { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Failed to save agent.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleGenerateCode = async () => {
    if (!agent.composerModelConfig) {
      setError('Please select a composer model before generating code.');
      return;
    }
    if (!agent.description || agent.description.trim() === '') {
      setError('Description is required to generate code.');
      return;
    }

    setError(null);
    setIsGenerating(true);

    try {
      const agentConfig = {
        tools: agent.tools || {},
        description: agent.description,
        inputSchema: agent.inputSchema,
        outputSchema: agent.outputSchema,
        invokableModels: agent.invokableModels || [],
        swaggerSpecs: agent.swaggerSpecs || [],
        gofannonAgents: (agent.gofannonAgents || []).map(ga => typeof ga === 'string' ? ga : ga.id),
        builtInTools: agent.composerModelConfig?.builtInTool ? [agent.composerModelConfig.builtInTool] : [],
        modelConfig: {
          provider: agent.composerModelConfig.provider,
          model: agent.composerModelConfig.model,
          parameters: agent.composerModelConfig.parameters || {},
        },
      };

      const response = await agentService.generateCode(agentConfig);
      
      setAgent(prev => {
        // Only adopt the LLM-proposed friendlyName if the user hasn't named
        // the agent yet. Otherwise preserve what they typed. Whatever wins,
        // name and friendlyName stay in lockstep and get sanitized.
        const hadUserName = !!(prev.name && prev.name.trim());
        const proposed = response.friendlyName || '';
        const resolvedRaw = hadUserName ? prev.name : proposed;
        const resolved = sanitizeAgentName(resolvedRaw);
        return {
          ...prev,
          code: response.code,
          docstring: response.docstring,
          friendlyName: resolved,
          name: resolved,
        };
      });

      if (isCreationFlow) {
        agentFlowContext.setGeneratedCode(response.code);
        agentFlowContext.setDocstring(response.docstring);
        // Mirror the resolved name — if the user had already set one, keep it.
        const hadUserName = !!(agent?.name && agent.name.trim());
        const resolved = sanitizeAgentName(hadUserName ? agent.name : (response.friendlyName || ''));
        agentFlowContext.setFriendlyName(resolved);
      }

      setSuccessMessage('Code generated successfully!');
    } catch (err) {
      setError(err.message || 'Failed to generate code.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Agent names are used as slugs for deployment URLs and for Gofannon
  // inter-agent dispatch. Only [A-Za-z0-9_] is valid. Any other character
  // the user types is substituted with '_' live so what-you-see-is-what-
  // you-save. friendlyName is always kept identical to name.
  const sanitizeAgentName = (value) => (value || '').replace(/[^A-Za-z0-9_]/g, '_');

  const handleFieldChange = (field, value) => {
    if (field === 'name') {
      const cleaned = sanitizeAgentName(value);
      setAgent((prev) => ({ ...prev, name: cleaned, friendlyName: cleaned }));
      setSuccessMessage('');
      syncToContext('name', cleaned);
      // Keep the creation-flow context's friendlyName in sync too so the
      // deploy screen and sandbox see the same value.
      if (isCreationFlow) {
        agentFlowContext.setFriendlyName(cleaned);
      }
      return;
    }
    setAgent((prev) => ({ ...prev, [field]: value }));
    setSuccessMessage('');
    syncToContext(field, value);
  };

  const handleViewSpec = (spec) => {
    setViewingSpec({ open: true, name: spec.name, content: spec.content });
  };

  // ========== Tools Management ==========
  const handleAddMcpServer = () => {
    if (!currentToolUrl.trim()) {
      setError('Tool URL cannot be empty.');
      return;
    }
    try {
      new URL(currentToolUrl);
    } catch {
      setError('Invalid URL format.');
      return;
    }

    if (agent.tools[currentToolUrl]) {
      setError('This URL is already added.');
      return;
    }

    const newTools = { ...agent.tools, [currentToolUrl]: [] };
    setAgent(prev => ({ ...prev, tools: newTools }));
    syncToContext('tools', newTools);
    setCurrentToolUrl('');
    setError(null);
  };

  const handleDeleteMcpServer = (urlToDelete) => {
    const newTools = { ...agent.tools };
    delete newTools[urlToDelete];
    setAgent(prev => ({ ...prev, tools: newTools }));
    syncToContext('tools', newTools);
  };

  const handleOpenToolsDialog = (mcpUrl) => {
    setToolsDialog({
      open: true,
      mcpUrl: mcpUrl,
      existingSelectedTools: agent.tools[mcpUrl] || [],
    });
  };

  const handleSaveSelectedTools = (mcpUrl, selectedNames) => {
    const newTools = { ...agent.tools, [mcpUrl]: selectedNames };
    setAgent(prev => ({ ...prev, tools: newTools }));
    syncToContext('tools', newTools);
  };

  const handleFetchSpec = async () => {
    if (!specUrl.trim()) {
      setError('Spec URL cannot be empty.');
      return;
    }
    setIsFetchingSpec(true);
    setError(null);
    try {
      const specData = await agentService.fetchSpecFromUrl(specUrl);
      if (agent.swaggerSpecs.some(spec => spec.name === specData.name)) {
        setError(`A spec with the name "${specData.name}" already exists.`);
      } else {
        const newSpecs = [...agent.swaggerSpecs, specData];
        setAgent(prev => ({ ...prev, swaggerSpecs: newSpecs }));
        syncToContext('swaggerSpecs', newSpecs);
        setSpecUrl('');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch spec from URL.');
    } finally {
      setIsFetchingSpec(false);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (agent.swaggerSpecs.some(spec => spec.name === file.name)) {
        setError(`A spec with the name "${file.name}" has already been uploaded.`);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        const newSpecs = [...agent.swaggerSpecs, { name: file.name, content }];
        setAgent(prev => ({ ...prev, swaggerSpecs: newSpecs }));
        syncToContext('swaggerSpecs', newSpecs);
        setError(null);
      };
      reader.onerror = () => setError("Failed to read the file.");
      reader.readAsText(file);
    }
    event.target.value = null;
  };

  const handleDeleteSpec = (specName) => {
    const newSpecs = agent.swaggerSpecs.filter(spec => spec.name !== specName);
    setAgent(prev => ({ ...prev, swaggerSpecs: newSpecs }));
    syncToContext('swaggerSpecs', newSpecs);
  };

  const handleAddGofannonAgent = () => {
    if (!selectedAgentId) return;
    if (agent.gofannonAgents.some(a => a.id === selectedAgentId)) {
      setError('This agent has already been added.');
      return;
    }
    const agentToAdd = availableAgents.find(a => a._id === selectedAgentId);
    if (agentToAdd) {
      const newAgents = [...agent.gofannonAgents, { id: agentToAdd._id, name: agentToAdd.name }];
      setAgent(prev => ({ ...prev, gofannonAgents: newAgents }));
      syncToContext('gofannonAgents', newAgents);
      setSelectedAgentId('');
      setError(null);
    }
  };

  const handleDeleteGofannonAgent = (agentIdToDelete) => {
    const newAgents = agent.gofannonAgents.filter(a => a.id !== agentIdToDelete);
    setAgent(prev => ({ ...prev, gofannonAgents: newAgents }));
    syncToContext('gofannonAgents', newAgents);
  };

  // ========== Model Dialog Functions ==========
  // openModelDialog(mode)                   → add-new (invokable) or set-from-scratch (composer)
  // openModelDialog(mode, existing)         → edit composer, or preload dialog with existing values
  // openModelDialog('invokable', existing, i) → edit invokable model at index i in place
  const openModelDialog = (mode, existing = null, editIndex = null) => {
    setModelDialogMode(mode);
    setEditingInvokableIndex(mode === 'invokable' ? editIndex : null);

    // If we're editing an existing config, preload dialog state from it.
    // Only do so when the provider/model still exist in the currently
    // available providers set — otherwise fall through to defaults to avoid
    // showing a dead selection.
    const existingProviderExists =
      existing && providers[existing.provider] &&
      providers[existing.provider].models?.[existing.model];

    if (existingProviderExists) {
      setDialogProvider(existing.provider);
      setDialogModel(existing.model);
      const modelParams = providers[existing.provider].models[existing.model].parameters || {};
      setDialogParamSchema(modelParams);
      // Merge: start from the existing saved params, then make sure any
      // params the user hadn't set keep their schema defaults. This lets
      // new params added to a model since the agent was configured show
      // up with sensible defaults instead of undefined.
      const merged = {};
      Object.keys(modelParams).forEach(key => {
        if (modelParams[key].default !== null && modelParams[key].default !== undefined) {
          if (key === 'top_p' && existing.provider === 'anthropic') return;
          merged[key] = modelParams[key].default;
        }
      });
      Object.assign(merged, existing.parameters || {});
      setDialogParams(merged);
      setDialogBuiltInTool(existing.builtInTool || '');
      setModelDialogOpen(true);
      return;
    }

    // No existing config (or its provider/model is no longer available):
    // fall back to the first available provider and its defaults.
    const defaultProvider = Object.keys(providers)[0] || '';
    setDialogProvider(defaultProvider);
    const models = Object.keys(providers[defaultProvider]?.models || {});
    const defaultModel = models[0] || '';
    setDialogModel(defaultModel);
    
    const modelParams = providers[defaultProvider]?.models?.[defaultModel]?.parameters || {};
    setDialogParamSchema(modelParams);
    const defaultParams = {};
    Object.keys(modelParams).forEach(key => {
      if (modelParams[key].default !== null) {
        if (key === 'top_p' && defaultProvider === 'anthropic') return;
        defaultParams[key] = modelParams[key].default;
      }
    });
    setDialogParams(defaultParams);
    setDialogBuiltInTool('');
    setModelDialogOpen(true);
  };

  const handleDialogProviderChange = (newProvider) => {
    setDialogProvider(newProvider);
    const models = Object.keys(providers[newProvider]?.models || {});
    const firstModel = models[0] || '';
    setDialogModel(firstModel);
    const modelParams = providers[newProvider]?.models?.[firstModel]?.parameters || {};
    setDialogParamSchema(modelParams);
    const defaultParams = {};
    Object.keys(modelParams).forEach(key => {
      if (modelParams[key].default !== null) {
        if (key === 'top_p' && newProvider === 'anthropic') return;
        defaultParams[key] = modelParams[key].default;
      }
    });
    setDialogParams(defaultParams);
    setDialogBuiltInTool('');
  };

  const handleDialogModelChange = (newModel) => {
    setDialogModel(newModel);
    const modelParams = providers[dialogProvider]?.models?.[newModel]?.parameters || {};
    setDialogParamSchema(modelParams);
    const defaultParams = {};
    Object.keys(modelParams).forEach(key => {
      if (modelParams[key].default !== null) {
        if (key === 'top_p' && dialogProvider === 'anthropic') return;
        defaultParams[key] = modelParams[key].default;
      }
    });
    setDialogParams(defaultParams);
    setDialogBuiltInTool('');
  };

  const handleSaveInvokableModel = () => {
    if (!dialogProvider || !dialogModel) return;
    const newModel = {
      provider: dialogProvider,
      model: dialogModel,
      parameters: dialogParams,
      builtInTool: dialogBuiltInTool || null,
    };
    let newInvokableModels;
    if (editingInvokableIndex !== null && editingInvokableIndex >= 0) {
      // Replace in place
      newInvokableModels = (agent.invokableModels || []).map((m, i) =>
        i === editingInvokableIndex ? newModel : m
      );
    } else {
      // Append
      newInvokableModels = [...(agent.invokableModels || []), newModel];
    }
    setAgent(prev => ({ ...prev, invokableModels: newInvokableModels }));
    syncToContext('invokableModels', newInvokableModels);
    setEditingInvokableIndex(null);
    setModelDialogOpen(false);
  };

  const handleRemoveInvokableModel = (index) => {
    const newInvokableModels = agent.invokableModels.filter((_, i) => i !== index);
    setAgent(prev => ({ ...prev, invokableModels: newInvokableModels }));
    syncToContext('invokableModels', newInvokableModels);
  };

  const handleSetComposerModel = () => {
    if (!dialogProvider || !dialogModel) return;
    const newComposerConfig = {
      provider: dialogProvider,
      model: dialogModel,
      parameters: dialogParams,
      builtInTool: dialogBuiltInTool || null,
    };
    setAgent(prev => ({ ...prev, composerModelConfig: newComposerConfig }));
    syncToContext('composerModelConfig', newComposerConfig);
    setModelDialogOpen(false);
  };

  const handleDeleteAgent = async () => {
    if (!agentId) return;
    setDeleteConfirmationOpen(false);
    setError(null);
    setIsSaving(true);

    try {
      await agentService.deleteAgent(agentId);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Failed to delete agent.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUndeploy = async () => {
    if (!agentId || !deployment?.is_deployed) return;
    setIsUndeploying(true);
    setError(null);
    try {
        await agentService.undeployAgent(agentId);
        setDeployment({ is_deployed: false });
    } catch (err) {
        setError(err.message || 'Failed to undeploy agent.');
    } finally {
        setIsUndeploying(false);
    }
  };

  const handleInputSchemaChange = (newSchema) => {
    setAgent(prev => ({ ...prev, inputSchema: newSchema }));
    syncToContext('inputSchema', newSchema);
  };

  const handleOutputSchemaChange = (newSchema) => {
    setAgent(prev => ({ ...prev, outputSchema: newSchema }));
    syncToContext('outputSchema', newSchema);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!agent) {
    return <Alert severity="warning">No agent data found.</Alert>;
  }
  
  return (
    <Paper sx={{ p: 3, maxWidth: 900, margin: 'auto', mt: 4 }}>
        <Typography variant="h5" component="h2" gutterBottom>
            {isCreationFlow 
              ? (hasCode ? 'Review Your Agent' : 'Create New Agent')
              : `Agent: ${agent.name}`}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {isCreationFlow 
              ? (hasCode 
                  ? 'Review the generated code. Edit and regenerate as needed.'
                  : 'Configure your agent\'s tools, description, schemas, and models, then generate code.')
              : 'View and edit your agent configuration.'}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage('')}>
          {successMessage}
        </Alert>}

        {/* Tools & Specs Section */}
        <Accordion defaultExpanded={!hasCode}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Tools & Capabilities</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                    <Tabs value={toolsTabIndex} onChange={(e, v) => setToolsTabIndex(v)}>
                        <Tab label="MCP Servers" />
                        <Tab label="Swagger / OpenAPI" />
                        <Tab label="Gofannon Agents" />
                    </Tabs>
                </Box>

                {/* MCP Servers Tab */}
                {toolsTabIndex === 0 && (
                    <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Connect to Model Context Protocol (MCP) servers to access external tools.
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                            <TextField
                                fullWidth
                                label="MCP Server URL"
                                variant="outlined"
                                size="small"
                                value={currentToolUrl}
                                onChange={(e) => setCurrentToolUrl(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleAddMcpServer()}
                            />
                            <Button variant="contained" onClick={handleAddMcpServer}>Add</Button>
                        </Box>
                        {Object.keys(agent.tools || {}).length > 0 && (
                            <List dense sx={{ border: '1px solid #444', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
                                {Object.keys(agent.tools).map((url) => (
                                    <ListItem
                                        key={url}
                                        secondaryAction={
                                            <>
                                                <IconButton onClick={() => handleOpenToolsDialog(url)} sx={{ mr: 1 }}>
                                                    <BuildIcon />
                                                </IconButton>
                                                <IconButton onClick={() => handleDeleteMcpServer(url)}>
                                                    <DeleteIcon />
                                                </IconButton>
                                            </>
                                        }
                                    >
                                        <ListItemIcon><WebIcon /></ListItemIcon>
                                        <ListItemText 
                                            primary={url} 
                                            secondary={agent.tools[url]?.length > 0 ? `Selected: ${agent.tools[url].join(', ')}` : "No tools selected"} 
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        )}
                    </Box>
                )}

                {/* Swagger Tab */}
                {toolsTabIndex === 1 && (
                    <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Add OpenAPI/Swagger specs to expose REST APIs as tools.
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                            <TextField
                                fullWidth
                                label="Spec URL"
                                variant="outlined"
                                size="small"
                                value={specUrl}
                                onChange={(e) => setSpecUrl(e.target.value)}
                                disabled={isFetchingSpec}
                            />
                            <Button variant="contained" onClick={handleFetchSpec} disabled={isFetchingSpec}>
                                {isFetchingSpec ? <CircularProgress size={20} /> : 'Fetch'}
                            </Button>
                        </Box>
                        <Divider sx={{ my: 2 }}>OR</Divider>
                        <Button
                            variant="outlined"
                            component="label"
                            fullWidth
                            startIcon={<UploadFileIcon />}
                            sx={{ mb: 2 }}
                        >
                            Upload Spec File
                            <input type="file" hidden accept=".json,.yaml,.yml" onChange={handleFileUpload} />
                        </Button>
                        {agent.swaggerSpecs?.length > 0 && (
                            <List dense sx={{ border: '1px solid #444', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
                                {agent.swaggerSpecs.map((spec) => (
                                    <ListItem
                                        key={spec.name}
                                        secondaryAction={
                                            <>
                                                <IconButton onClick={() => handleViewSpec(spec)} sx={{ mr: 1 }}>
                                                    <VisibilityIcon />
                                                </IconButton>
                                                <IconButton onClick={() => handleDeleteSpec(spec.name)}>
                                                    <DeleteIcon />
                                                </IconButton>
                                            </>
                                        }
                                    >
                                        <ListItemIcon><ArticleIcon /></ListItemIcon>
                                        <ListItemText primary={spec.name} />
                                    </ListItem>
                                ))}
                            </List>
                        )}
                    </Box>
                )}

                {/* Gofannon Agents Tab */}
                {toolsTabIndex === 2 && (
                    <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Use other saved agents as callable tools.
                        </Typography>
                        {loadingAgents ? <CircularProgress size={24} /> : (
                            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                                <FormControl fullWidth size="small">
                                    <InputLabel>Select an Agent</InputLabel>
                                    <Select
                                        value={selectedAgentId}
                                        label="Select an Agent"
                                        onChange={(e) => setSelectedAgentId(e.target.value)}
                                    >
                                        {availableAgents.map((a) => (
                                            <MenuItem key={a._id} value={a._id}>{a.name}</MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <Button variant="contained" onClick={handleAddGofannonAgent} disabled={!selectedAgentId}>
                                    Add
                                </Button>
                            </Box>
                        )}
                        {agent.gofannonAgents?.length > 0 && (
                            <List dense sx={{ border: '1px solid #444', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
                                {agent.gofannonAgents.map((ga) => (
                                    <ListItem
                                        key={ga.id}
                                        secondaryAction={
                                            <IconButton onClick={() => handleDeleteGofannonAgent(ga.id)}>
                                                <DeleteIcon />
                                            </IconButton>
                                        }
                                    >
                                        <ListItemIcon><SmartToyIcon /></ListItemIcon>
                                        <ListItemText primary={ga.name} />
                                    </ListItem>
                                ))}
                            </List>
                        )}
                    </Box>
                )}
            </AccordionDetails>
        </Accordion>

        {/* Description Section */}
        <Accordion defaultExpanded={!hasCode}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Name & Description</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <TextField 
                    fullWidth
                    label="Agent Name"
                    value={agent.name || ''}
                    onChange={(e) => handleFieldChange('name', e.target.value)}
                    placeholder="my_agent_name"
                    sx={{ mb: 2 }}
                    required
                    helperText="Used as the deployment URL slug (/rest/<name>) and for inter-agent calls."
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <Tooltip
                            arrow
                            title={
                              "Names must be letters, digits, and underscores only. " +
                              "Spaces and other punctuation are converted to underscores as you type. " +
                              "This becomes the URL slug when the agent is deployed, so pick something stable."
                            }
                          >
                            <HelpOutlineIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                          </Tooltip>
                        </InputAdornment>
                      ),
                    }}
                />
                <TextField 
                    fullWidth
                    multiline
                    rows={4}
                    label="Agent Description"
                    value={agent.description || ''}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                    placeholder="Describe what your agent should do. Be specific about its purpose, inputs, outputs, and how it should use the available tools..."
                />
            </AccordionDetails>
        </Accordion>

        {/* Schemas Section */}
        <Accordion defaultExpanded={!hasCode}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Input/Output Schemas</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Define the JSON structure for your agent's input and output.
                </Typography>
                <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                        <SchemaEditor
                            title="Input Schema"
                            schema={agent.inputSchema || {}}
                            setSchema={handleInputSchemaChange}
                        />
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <SchemaEditor
                            title="Output Schema"
                            schema={agent.outputSchema || {}}
                            setSchema={handleOutputSchemaChange}
                        />
                    </Grid>
                </Grid>
            </AccordionDetails>
        </Accordion>

        {/* Model Configuration Section */}
        <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Model Configuration</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                        Composer Model
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                        The model used to generate agent code.
                    </Typography>
                    {agent.composerModelConfig ? (
                        <Chip 
                            label={`${agent.composerModelConfig.provider}/${agent.composerModelConfig.model}${agent.composerModelConfig.builtInTool ? ` + ${agent.composerModelConfig.builtInTool}` : ''}`} 
                            color="primary" 
                            sx={{ mr: 1, mt: 1 }}
                            onDelete={() => {
                                setAgent(prev => ({ ...prev, composerModelConfig: null }));
                                syncToContext('composerModelConfig', null);
                            }}
                        />
                    ) : (
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mt: 1 }}>
                            No composer model configured.
                        </Typography>
                    )}
                    <Button 
                        size="small" 
                        startIcon={<EditIcon />} 
                        onClick={() => openModelDialog('composer', agent.composerModelConfig)}
                        sx={{ ml: 1, mt: 1 }}
                        disabled={loadingProviders}
                    >
                        {agent.composerModelConfig ? 'Change' : 'Set Model'}
                    </Button>
                </Box>

                <Divider sx={{ my: 2 }} />

                <Box>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                        Invokable Models
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                        Models the agent can call at runtime.
                    </Typography>
                    {agent.invokableModels?.length > 0 ? (
                        <Box sx={{ mt: 1 }}>
                            {agent.invokableModels.map((m, idx) => (
                                <Tooltip key={idx} title="Click to edit. X to remove." arrow>
                                    <Chip 
                                        label={`${m.provider}/${m.model}${m.builtInTool ? ` + ${m.builtInTool}` : ''}`} 
                                        sx={{ mr: 1, mb: 1, cursor: 'pointer' }}
                                        onClick={() => openModelDialog('invokable', m, idx)}
                                        onDelete={() => handleRemoveInvokableModel(idx)}
                                    />
                                </Tooltip>
                            ))}
                        </Box>
                    ) : (
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mt: 1 }}>
                            No invokable models configured.
                        </Typography>
                    )}
                    <Button 
                        size="small" 
                        startIcon={<AddIcon />} 
                        onClick={() => openModelDialog('invokable')}
                        sx={{ mt: 1 }}
                        disabled={loadingProviders}
                    >
                        Add Model
                    </Button>
                </Box>
            </AccordionDetails>
        </Accordion>

        {/* Docstring Section */}
        {agent.docstring && (
            <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Generated Docstring</Typography>
                </AccordionSummary>
                <AccordionDetails>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.paper', overflowX: 'auto', border: '1px solid #444' }}>
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
                            {agent.docstring}
                        </pre>
                    </Paper>
                </AccordionDetails>
            </Accordion>
        )}

        {/* Agent Code Section */}
        {hasCode && (
            <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Agent Code</Typography>
                </AccordionSummary>
                <AccordionDetails>
                    <CodeEditor code={agent.code} onCodeChange={(newCode) => handleFieldChange('code', newCode)} isReadOnly={false}/>
                </AccordionDetails>
            </Accordion>
        )}

        {/* Deployments Section */}
        {!isCreationFlow && deployment?.is_deployed && (
            <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Deployments</Typography>
                </AccordionSummary>
                <AccordionDetails>
                    <Typography variant="subtitle1" gutterBottom>Internal REST Endpoint</Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.paper', fontFamily: 'monospace' }}>
                        <Chip label="POST" color="success" size="small" sx={{ mr: 1 }} />
                        <Typography component="span" sx={{ fontWeight: 'bold' }}>{`/rest/${deployment.friendly_name}`}</Typography>
                    </Paper>
                    <Button
                        variant="contained"
                        color="error"
                        startIcon={isUndeploying ? <CircularProgress size={20} color="inherit" /> : <DeleteIcon />}
                        onClick={handleUndeploy}
                        disabled={isUndeploying}
                        sx={{ mt: 2 }}
                    >
                        {isUndeploying ? 'Undeploying...' : 'Undeploy'}
                    </Button>
                </AccordionDetails>
            </Accordion>
        )}

        {/* Action Buttons */}
        <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{mt: 3}} flexWrap="wrap" useFlexGap>
            {!isCreationFlow && (
                <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => setDeleteConfirmationOpen(true)}
                    disabled={isSaving}
                >
                    Delete Agent
                </Button>
            )}

            {/* Generate/Regenerate Code Button */}
            <Button
                variant={hasCode ? "outlined" : "contained"}
                color={hasCode ? "secondary" : "primary"}
                startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : (hasCode ? <RefreshIcon /> : <CodeIcon />)}
                onClick={handleGenerateCode}
                disabled={isGenerating || !agent.composerModelConfig}
            >
                {isGenerating ? 'Generating...' : (hasCode ? 'Regenerate Code' : 'Generate Code')}
            </Button>

            {/* Only show these when code exists */}
            {hasCode && (
                <>
                    <Button variant="outlined" startIcon={<PlayArrowIcon />} onClick={handleRunInSandbox}>
                        Run in Sandbox
                    </Button>
                    
                    <Button variant="outlined" color="secondary" startIcon={<PublishIcon />} onClick={handleDeploy}>
                        Deploy Agent
                    </Button>

                    {isCreationFlow ? (
                        <Button
                            variant="contained"
                            color="primary"
                            startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                            onClick={handleSaveNewAgent}
                            disabled={isSaving || isGenerating || !hasCode}
                        >
                            {isSaving ? 'Saving...' : 'Save Agent'}
                        </Button>
                    ) : (
                        <Button
                            variant="contained"
                            color="primary"
                            startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                            onClick={handleUpdateAgent}
                            disabled={isSaving || isGenerating}
                        >
                            {isSaving ? 'Updating...' : 'Update Agent'}
                        </Button>
                    )}
                </>
            )}
        </Stack>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteConfirmationOpen} onClose={() => setDeleteConfirmationOpen(false)}>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogContent>
                <DialogContentText>
                    Are you sure you want to permanently delete this agent? This action cannot be undone.
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setDeleteConfirmationOpen(false)}>Cancel</Button>
                <Button onClick={handleDeleteAgent} color="error" variant="contained">Delete</Button>
            </DialogActions>
        </Dialog> 

        {/* Model Config Dialog */}
        <ModelConfigDialog
            open={modelDialogOpen}
            onClose={() => {
              setModelDialogOpen(false);
              setEditingInvokableIndex(null);
            }}
            onSave={modelDialogMode === 'composer' ? handleSetComposerModel : handleSaveInvokableModel}
            title={
              modelDialogMode === 'composer'
                ? (agent?.composerModelConfig ? 'Edit Composer Model' : 'Set Composer Model')
                : (editingInvokableIndex !== null ? 'Edit Invokable Model' : 'Add Invokable Model')
            }
            providers={providers}
            selectedProvider={dialogProvider}
            setSelectedProvider={handleDialogProviderChange}
            selectedModel={dialogModel}
            setSelectedModel={handleDialogModelChange}
            modelParamSchema={dialogParamSchema}
            setModelParamSchema={setDialogParamSchema}
            currentModelParams={dialogParams}
            setCurrentModelParams={setDialogParams}
            selectedBuiltInTool={dialogBuiltInTool}
            setSelectedBuiltInTool={setDialogBuiltInTool}
            loadingProviders={loadingProviders}
            providersError={null}
        />

        {/* Tools Selection Dialog */}
        <ToolsSelectionDialog
            open={toolsDialog.open}
            onClose={() => setToolsDialog({ ...toolsDialog, open: false })}
            mcpUrl={toolsDialog.mcpUrl}
            existingSelectedTools={toolsDialog.existingSelectedTools}
            onSaveSelectedTools={handleSaveSelectedTools}
        />

        <SpecViewerModal
            open={viewingSpec.open}
            onClose={() => setViewingSpec({ open: false, name: '', content: '' })}
            specName={viewingSpec.name}
            specContent={viewingSpec.content}
        />       
    </Paper>
  );
};

export default ViewAgent;