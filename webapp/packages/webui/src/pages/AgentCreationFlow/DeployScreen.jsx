import React, { useState } from 'react';
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
} from '@mui/material';
import PublishIcon from '@mui/icons-material/Publish';

const DeployScreen = () => {
  const [deploymentType, setDeploymentType] = useState('');
  const [hostingPlatform, setHostingPlatform] = useState('');

  const handleDeploy = () => {
    // This button is disabled for POC, so this function won't be called initially.
    console.log('Deploying agent with:', { deploymentType, hostingPlatform });
    // In a real scenario, this would trigger the deployment process.
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Deploy Your Agent
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose how your agent will interact and where it will be hosted.
      </Typography>

      <FormControl component="fieldset" fullWidth sx={{ mb: 3 }}>
        <FormLabel component="legend">Deployment Protocol</FormLabel>
        <RadioGroup
          row
          aria-label="deployment-type"
          name="deployment-type-group"
          value={deploymentType}
          onChange={(e) => setDeploymentType(e.target.value)}
        >
          <FormControlLabel value="A2A" control={<Radio />} label="Agent-to-Agent (A2A)" />
          <FormControlLabel value="MCP" control={<Radio />} label="Model Context Protocol (MCP)" />
          <FormControlLabel value="REST" control={<Radio />} label="REST API" />
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
          <FormControlLabel value="GCPCloudRun" control={<Radio />} label="GCP Cloud Run" />
          <FormControlLabel value="AWSFargate" control={<Radio />} label="AWS Fargate" />
          <FormControlLabel value="Docker" control={<Radio />} label="Docker Container" />
        </RadioGroup>
      </FormControl>

      <Button
        variant="contained"
        color="primary"
        startIcon={<PublishIcon />}
        onClick={handleDeploy}
        disabled // Disabled for POC as per requirement
        fullWidth
      >
        Deploy Agent
      </Button>
    </Paper>
  );
};

export default DeployScreen;
