import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import WebIcon from '@mui/icons-material/Web';
import ArticleIcon from '@mui/icons-material/Article';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import Divider from '@mui/material/Divider';

import { useAgentFlow } from './AgentCreationFlow/AgentCreationFlowContext';
import agentService from '../services/agentService';
import CodeEditor from '../components/CodeEditor';
import SpecViewerModal from '../components/SpecViewerModal';

const ViewAgent = () => {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const agentFlowContext = useAgentFlow();

  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [deleteConfirmationOpen, setDeleteConfirmationOpen] = useState(false);  
  const [viewingSpec, setViewingSpec] = useState({ open: false, name: '', content: '' });
  
  // State for deployment
  const [deployment, setDeployment] = useState(null);
  const [isUndeploying, setIsUndeploying] = useState(false);

  const isCreationFlow = !agentId;

  useEffect(() => {
    if (agentId) { // Only for existing agents, not during creation flow
        const fetchDeploymentStatus = async () => {
            try {
                const status = await agentService.getDeployment(agentId);
                setDeployment(status);
            } catch (err) {
                // Don't block the page from rendering, just show an auxiliary error
                const deploymentError = 'Could not fetch deployment status.';
                setError(prev => prev ? `${prev}\n${deploymentError}` : deploymentError);
            }
        };
        fetchDeploymentStatus();
    }
  }, [agentId]);

    const loadAgentData = useCallback(async () => {
    setError(null);
    setLoading(true);
    
    try {
      if (isCreationFlow) {
        // In creation flow, data comes from context
        if (!agentFlowContext.generatedCode) {
            throw new Error("Agent code has not been generated yet. Please go back to the schemas screen.");
        }
        
        setAgent({
          name: agentFlowContext.friendlyName || '',
          description: agentFlowContext.description,
          tools: agentFlowContext.tools,
          swaggerSpecs: agentFlowContext.swaggerSpecs,
          gofannonAgents: agentFlowContext.gofannonAgents,
          code: agentFlowContext.generatedCode,
          inputSchema: agentFlowContext.inputSchema,
          outputSchema: agentFlowContext.outputSchema,
          invokableModels: agentFlowContext.invokableModels,
          docstring: agentFlowContext.docstring,
          friendlyName: agentFlowContext.friendlyName,
        });

      } else {
        // In view/edit mode, fetch from API
        const data = await agentService.getAgent(agentId);
        
        if (data.gofannonAgents && data.gofannonAgents.length > 0) {
            // To display names, we need to fetch all agents and create a map.
            const allAgents = await agentService.getAgents();
            const agentMap = new Map(allAgents.map(a => [a._id, a.name]));
            data.gofannonAgents = data.gofannonAgents.map(id => ({
                id: id,
                name: agentMap.get(id) || `Unknown Agent (ID: ${id})`
            }));
        } else {
            data.gofannonAgents = []; // Ensure it's an array
        }
        
        setAgent(data);
      }
    } catch (err) {
      setError(err.message || 'Failed to load agent data.');
    } finally {
      setLoading(false);
    }
  }, [agentId, isCreationFlow, agentFlowContext]);

  useEffect(() => {
    loadAgentData();
  }, [loadAgentData]);
  
  const handleFieldChange = (field, value) => {
    setAgent(prev => ({...prev, [field]: value}));
  };

  const handleViewSpec = (spec) => {
    setViewingSpec({ open: true, name: spec.name, content: spec.content });
};

  const updateContextAndNavigate = (path) => {
      // Update the context with the current agent state before navigating
      agentFlowContext.setDescription(agent.description);
      agentFlowContext.setGeneratedCode(agent.code);
      agentFlowContext.setTools(agent.tools);
      agentFlowContext.setSwaggerSpecs(agent.swaggerSpecs);
      agentFlowContext.setInputSchema(agent.inputSchema);
      agentFlowContext.setOutputSchema(agent.outputSchema);
      agentFlowContext.setInvokableModels(agent.invokableModels);
      agentFlowContext.setDocstring(agent.docstring);
      agentFlowContext.setGofannonAgents(agent.gofannonAgents);
      agentFlowContext.setFriendlyName(agent.friendlyName);
      navigate(path);
    
  };

  const handleRunInSandbox = () => {
    updateContextAndNavigate('/create-agent/sandbox');
  };

  const handleDeploy = () => {
    if (agentId) {
      // For saved agents, navigate directly to deploy screen with agentId
      navigate(`/agent/${agentId}/deploy`);
    } else {
      // For unsaved agents (creation flow), update context and navigate
      updateContextAndNavigate('/create-agent/deploy');
    }
  };

  const handleUpdateAgent = async () => {
    if (!agentId) return; // Should not happen if button is only for edit mode
    setError(null);
    setSaveSuccess(false);
    setIsSaving(true);
    try {
      await agentService.updateAgent(agentId, {
        name: agent.name,
        description: agent.description,
        code: agent.code,
      });
      setSaveSuccess(true);
    } catch (err) {
        setError(err.message || 'Failed to update agent.');
    } finally {
        setIsSaving(false);
    }
  };

  const handleDeleteAgent = async () => {
    if (!agentId) return;
    setDeleteConfirmationOpen(false);
    setError(null);
    setIsSaving(true); // Reuse saving state for loading indicator

    try {
      await agentService.deleteAgent(agentId);
      navigate('/agents', { replace: true }); // Redirect after deletion
    } catch (err) {
      setError(err.message || 'Failed to delete agent.');
      // Stay on the page to show the error
      setIsSaving(false);
    }
    // On success, isSaving will not be set to false because we navigate away.    
  };

  const handleUndeploy = async () => {
    if (!agentId) return;
    setIsUndeploying(true);
    setError(null);
    try {
        await agentService.undeployAgent(agentId);
        // Update UI immediately to reflect the undeployed state
        setDeployment({ is_deployed: false });
    } catch (err) {
        setError(err.message || 'Failed to undeploy agent.');
    } finally {
        setIsUndeploying(false);
    }
  };


  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!agent) {
    return <Alert severity="warning">No agent data found.</Alert>;
  }
  
  return (
    <Paper sx={{ p: 3, maxWidth: 900, margin: 'auto', mt: 4 }}>
        <Typography variant="h5" component="h2" gutterBottom>
            {isCreationFlow ? 'Review Your New Agent' : `Viewing Agent: ${agent.name}`}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {isCreationFlow ? 'Review the generated code and details below. You can make edits before proceeding.' : 'View and edit the details of your saved agent.'}
        </Typography>

        {saveSuccess && <Alert severity="success" onClose={() => setSaveSuccess(false)}>Agent updated successfully!</Alert>}

        <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Tools & Specs</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <Typography variant="subtitle1" gutterBottom>MCP Servers</Typography>
                {Object.keys(agent.tools).length > 0 ? (
                <List dense>
                    {Object.entries(agent.tools).map(([url, selectedTools]) => (
                        <ListItem key={url}>
                            <ListItemIcon><WebIcon /></ListItemIcon>
                            <ListItemText primary={url} secondary={selectedTools.length > 0 ? `Selected: ${selectedTools.join(', ')}` : "No specific tools selected"} />
                        </ListItem>
                    ))}
                </List>
                ) : (<Typography variant="body2" color="text.secondary">No MCP servers configured.</Typography>)}
                <Typography variant="subtitle1" gutterBottom sx={{mt: 2}}>Swagger/OpenAPI Specs</Typography>
                {agent.swaggerSpecs.length > 0 ? (
                <List dense>
                    {agent.swaggerSpecs.map(spec => (
                        <ListItem
                            key={spec.name}
                            secondaryAction={
                                <IconButton edge="end" aria-label="view" onClick={() => handleViewSpec(spec)}>
                                    <VisibilityIcon />
                                </IconButton>
                            }
                        >
                            <ListItemIcon><ArticleIcon /></ListItemIcon>
                            <ListItemText primary={spec.name} />
                        </ListItem>
                    ))}
                </List>
                ) : (<Typography variant="body2" color="text.secondary">No Swagger specs uploaded.</Typography>)}
                
                <Typography variant="subtitle1" gutterBottom sx={{mt: 2}}>Gofannon Agents</Typography>
                {agent.gofannonAgents && agent.gofannonAgents.length > 0 ? (
                <List dense>
                    {agent.gofannonAgents.map(ga => (
                        <ListItem key={ga.id}>
                            <ListItemIcon><SmartToyIcon /></ListItemIcon>
                            <ListItemText primary={ga.name} />
                        </ListItem>
                    ))}
                </List>
                ) : (<Typography variant="body2" color="text.secondary">No Gofannon agents configured.</Typography>)}
            </AccordionDetails>
        </Accordion>

        <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Description</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <TextField 
                    fullWidth
                    multiline
                    rows={4}
                    label="Agent Description"
                    value={agent.description}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                />
            </AccordionDetails>
        </Accordion>

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

        <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Agent Code</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <CodeEditor code={agent.code} onCodeChange={(newCode) => handleFieldChange('code', newCode)} isReadOnly={!isCreationFlow}/>
            </AccordionDetails>
        </Accordion>

        {!isCreationFlow && deployment && deployment.is_deployed && (
            <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Deployments</Typography>
                </AccordionSummary>
                <AccordionDetails>
                    <Typography variant="subtitle1" gutterBottom>Internal REST Endpoint</Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.paper', fontFamily: 'monospace' }}>
                        <Typography component="div" gutterBottom>
                            <Chip label="POST" color="success" size="small" sx={{ mr: 1 }} />
                            <Typography component="span" sx={{ fontWeight: 'bold' }}>{`/rest/${deployment.friendly_name}`}</Typography>
                        </Typography>
                        <Divider sx={{ my: 1 }} />
                        <Typography variant="body2" sx={{ mt: 1, fontWeight: 'bold' }}>Request Body:</Typography>
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0, padding: '8px', backgroundColor: '#2e2e2e', color: '#dddddd', borderRadius: '4px' }}>
                            {JSON.stringify(agent.inputSchema, null, 2)}
                        </pre>
                        <Typography variant="body2" sx={{ mt: 2, fontWeight: 'bold' }}>Success Response (200 OK):</Typography>
                        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0, padding: '8px', backgroundColor: '#2e2e2e', color: '#dddddd', borderRadius: '4px' }}>
                            {JSON.stringify(agent.outputSchema, null, 2)}
                        </pre>
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

        <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{mt: 3}}>
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
            <Button
                variant="outlined"
                startIcon={<PlayArrowIcon />}
                onClick={handleRunInSandbox}
            >
                Run in Sandbox
            </Button>
            
            <Button
                variant="outlined"
                color="secondary"
                startIcon={<PublishIcon />}
                onClick={handleDeploy}
                disabled={isCreationFlow && !agentFlowContext.friendlyName} // Disable if not saved
                title={isCreationFlow && !agentFlowContext.friendlyName ? "Please save your agent before deploying" : ""}
            >
                Deploy Agent
            </Button>
            {!isCreationFlow && (
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                    onClick={handleUpdateAgent}
                    disabled={isSaving}
                >
                    {isSaving ? 'Updating...' : 'Update Agent'}
                </Button>
            )}
        </Stack>

        <Dialog
            open={deleteConfirmationOpen}
            onClose={() => setDeleteConfirmationOpen(false)}
        >
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogContent>
                <DialogContentText>
                    Are you sure you want to permanently delete the agent "{agent?.name}"? This action cannot be undone.
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setDeleteConfirmationOpen(false)}>Cancel</Button>
                <Button onClick={handleDeleteAgent} color="error" variant="contained">
                    Delete
                </Button>
            </DialogActions>
        </Dialog> 
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
