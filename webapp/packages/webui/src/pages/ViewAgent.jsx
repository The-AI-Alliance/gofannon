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
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import WebIcon from '@mui/icons-material/Web';
import ArticleIcon from '@mui/icons-material/Article';

import { useAgentFlow } from './AgentCreationFlow/AgentCreationFlowContext';
import agentService from '../services/agentService';
import CodeEditor from '../components/CodeEditor';

const ViewAgent = () => {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const agentFlowContext = useAgentFlow();

  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const isCreationFlow = !agentId;

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
          name: '',
          description: agentFlowContext.description,
          tools: agentFlowContext.tools,
          swaggerSpecs: agentFlowContext.swaggerSpecs,
          code: agentFlowContext.generatedCode,
          inputSchema: agentFlowContext.inputSchema,
          outputSchema: agentFlowContext.outputSchema,
          invokableModels: agentFlowContext.invokableModels
          // docstring will be in context if coming from creation flow, but it's not directly used here yet
        });
      } else {
        // In view/edit mode, fetch from API
        const data = await agentService.getAgent(agentId);
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
      navigate(path);
    
  };

  const handleRunInSandbox = () => {
    updateContextAndNavigate('/create-agent/sandbox');
  };

  const handleDeploy = () => {
    updateContextAndNavigate('/create-agent/deploy');
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
                        <ListItem key={spec.name}>
                            <ListItemIcon><ArticleIcon /></ListItemIcon>
                            <ListItemText primary={spec.name} />
                        </ListItem>
                    ))}
                </List>
                ) : (<Typography variant="body2" color="text.secondary">No Swagger specs uploaded.</Typography>)}
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

        <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{mt: 3}}>
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
    </Paper>
  );
};

export default ViewAgent;
