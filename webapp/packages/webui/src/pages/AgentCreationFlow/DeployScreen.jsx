import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Divider,
  Stack,
  CircularProgress,
  Alert,
} from '@mui/material';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import { useAgentFlow } from './AgentCreationFlowContext';
import agentService from '../../services/agentService';

const DeployScreen = () => {
  const [deploymentType, setDeploymentType] = useState('REST');
  const [hostingPlatform, setHostingPlatform] = useState('Internally');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const navigate = useNavigate();
  const agentFlowContext = useAgentFlow();

  const handleDeploy = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);
    try {
      // First, save the agent to ensure it has an ID
      const agentData = {
        name: agentFlowContext.friendlyName,
        description: agentFlowContext.description,
        code: agentFlowContext.generatedCode,
        docstring: agentFlowContext.docstring,
        friendlyName: agentFlowContext.friendlyName,
        tools: agentFlowContext.tools,
        swaggerSpecs: agentFlowContext.swaggerSpecs,
        inputSchema: agentFlowContext.inputSchema,
        outputSchema: agentFlowContext.outputSchema,
        invokableModels: agentFlowContext.invokableModels,
        gofannonAgents: (agentFlowContext.gofannonAgents || []).map(agent => agent.id),
      };
      const savedAgent = await agentService.saveAgent(agentData);
      
      // Then, deploy the newly saved agent
      await agentService.deployAgent(savedAgent._id);
      
      setSuccess(true);
      setTimeout(() => navigate(`/agent/${savedAgent._id}`), 2000);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during deployment.');
    } finally {
      setIsLoading(false);
    }
   };

  const handleSave = () => {
    navigate('/create-agent/save');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Deploy Your Agent
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose how your agent will interact and where it will be hosted. You can save the agent configuration now and deploy it later.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Agent deployed successfully! Redirecting...
        </Alert>
      )}

      <FormControl component="fieldset" fullWidth sx={{ mb: 3 }}>
        <FormLabel component="legend">Deployment Protocol</FormLabel>
        <RadioGroup
          row
          aria-label="deployment-type"
          name="deployment-type-group"
          value={deploymentType}
          onChange={(e) => setDeploymentType(e.target.value)}
        >
          <FormControlLabel value="A2A" disabled control={<Radio />} label="Agent-to-Agent (A2A)" />
          <FormControlLabel value="MCP" disabled control={<Radio />} label="Model Context Protocol (MCP)" />
          <FormControlLabel value="REST" control={<Radio checked />} label="REST API" />
       </RadioGroup>
      </FormControl>

      <Divider sx={{ my: 3 }} />

      <FormControl component="fieldset" fullWidth sx={{ mb: 3 }}>
        <FormLabel component="legend">Hosting Platform</FormLabel>
        <RadioGroup
          row
          aria-label="hosting-platform"
          name="hosting-platform-group"
          value={hostingPlatform}
          onChange={(e) => setHostingPlatform(e.target.value)}
        >
          <FormControlLabel value="Internally" control={<Radio checked />} label="Internally" />
          <FormControlLabel value="GCPCloudRun" disabled control={<Radio />} label="GCP Cloud Run" />
          <FormControlLabel value="AWSFargate" disabled control={<Radio />} label="AWS Fargate" />
          <FormControlLabel value="Docker" disabled control={<Radio />} label="Docker Container" />
        </RadioGroup>
      </FormControl>

      {/* Use Stack for button alignment */}
      <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ mt: 3 }}>
        <Button
          variant="outlined"
          color="secondary"
          startIcon={<SaveIcon />}
          onClick={handleSave}
        >
          Save Agent
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PublishIcon />}
          onClick={handleDeploy}
          disabled={isLoading || success}
        >
          {isLoading ? 'Deploying...' : 'Deploy Agent'}
        </Button>
      </Stack>
    </Paper>
  );
};

export default DeployScreen;