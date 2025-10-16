import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Paper,
  Alert,
  Tabs,
  Tab,
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel, 
  ListItemIcon, 
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import BuildIcon from '@mui/icons-material/Build';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useAgentFlow } from './AgentCreationFlowContext';
import agentService from '../../services/agentService';
import ToolsSelectionDialog from './ToolsSelectionDialog'; 


const ToolsScreen = () => {
  const { tools, setTools, swaggerSpecs, setSwaggerSpecs, gofannonAgents, setGofannonAgents } = useAgentFlow();
  const [currentToolUrl, setCurrentToolUrl] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const [toolsDialog, setToolsDialog] = useState({ open: false, mcpUrl: '', existingSelectedTools: [] });
  const [tabIndex, setTabIndex] = useState(0);

  // State for Gofannon Agents tab
  const [availableAgents, setAvailableAgents] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState('');


  const handleTabChange = (event, newValue) => {
    setTabIndex(newValue);
    setError(null); // Clear errors when switching tabs
  };

  const handleAddTool = () => {
    if (!currentToolUrl.trim()) {
      setError('Tool URL cannot be empty.');
      return;
    }
    try {
      new URL(currentToolUrl); // Validate URL format
    } catch (e) {
      setError('Invalid URL format.');
      return;
    }

    if (tools[currentToolUrl]) {
      setError('This URL is already added.');
      return;
    }

    setTools(prev => ({
      ...prev,
      [currentToolUrl]: prev[currentToolUrl] || [], // Keep existing selections or start with empty array
    }));
    setCurrentToolUrl('');
    setError(null);
  };

  const handleDeleteTool = (urlToDelete) => {
    setTools(prev => {
      const newTools = { ...prev };
      delete newTools[urlToDelete];
      return newTools;
    });
    setError(null);
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (swaggerSpecs.some(spec => spec.name === file.name)) {
        setError(`A spec with the name "${file.name}" has already been uploaded.`);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        setSwaggerSpecs(prev => [...prev, { name: file.name, content }]);
        setError(null);
      };
      reader.onerror = () => {
        setError("Failed to read the file.");
      };
      reader.readAsText(file);
    }
    event.target.value = null; // Allow re-uploading the same file
  };

  const handleAddGofannonAgent = () => {
    if (!selectedAgentId) return;
    if (gofannonAgents.some(agent => agent.id === selectedAgentId)) {
        setError('This agent has already been added.');
        return;
    }
    const agentToAdd = availableAgents.find(agent => agent._id === selectedAgentId);
    if (agentToAdd) {
        setGofannonAgents(prev => [...prev, { id: agentToAdd._id, name: agentToAdd.name }]);
        setSelectedAgentId('');
        setError(null);
    }
  };

  const handleDeleteGofannonAgent = (agentId) => {
    setGofannonAgents(prev => prev.filter(agent => agent.id !== agentId));
  };

  const handleDeleteSpec = (specName) => {
    setSwaggerSpecs(prev => prev.filter(spec => spec.name !== specName));
  };
  
  const handleContinue = () => {
    const hasMcpTools = Object.values(tools).some(selected => selected.length > 0);
    if (!hasMcpTools && swaggerSpecs.length === 0 && gofannonAgents.length === 0) {
      setError('Please add and select at least one tool or agent to continue.');
      return;
    }
    navigate('/create-agent/description');
  };

  const handleOpenToolsDialog = (mcpUrl) => {
    setToolsDialog({
      open: true,
      mcpUrl: mcpUrl,
      existingSelectedTools: tools[mcpUrl] || [], // Pass currently selected tools
    });
  };

  const handleSaveSelectedTools = (mcpUrl, selectedNames) => {
    setTools(prev => ({ ...prev, [mcpUrl]: selectedNames }));
  };

  React.useEffect(() => {
    const fetchAgents = async () => {
        setLoadingAgents(true);
        try {
            const agents = await agentService.getAgents();
            setAvailableAgents(agents);
        } catch (err) {
            setError('Failed to load available agents.');
        } finally {
            setLoadingAgents(false);
        }
    };
    if (tabIndex === 2) { // The new Gofannon tab
        fetchAgents();
    }    
  }, [tabIndex]);

  return (
    <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 1: Add Your Agent's Tools
      </Typography>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabIndex} onChange={handleTabChange} aria-label="tool type tabs">
          <Tab label="MCP Servers" />
          <Tab label="Swagger / OpenAPI" />
          <Tab label="Gofannon" />
        </Tabs>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {tabIndex === 0 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter full URLs for remote Model Context Protocol (MCP) servers.
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField
              fullWidth
              label="MCP Server URL (e.g., https://mcp.example.com)"
              variant="outlined"
              value={currentToolUrl}
              onChange={(e) => setCurrentToolUrl(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddTool();
                }
              }}
            />
            <Button variant="contained" onClick={handleAddTool}>
              Add
            </Button>
          </Box>      

          {Object.keys(tools).length > 0 && (
            <List dense sx={{ border: '1px solid #ccc', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
              {Object.keys(tools).map((url) => (
                <ListItem
                  key={url}
                  secondaryAction={
                    <>
                      <IconButton
                        edge="end"
                        aria-label="list-tools"
                        onClick={() => handleOpenToolsDialog(url)}
                        sx={{ mr: 1 }}
                      >
                        <BuildIcon />
                      </IconButton>
                      <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteTool(url)}>
                        <DeleteIcon />
                      </IconButton>
                    </>
                  }
                >
                  <ListItemText primary={url} secondary={tools[url] && tools[url].length > 0 ? `Selected: ${tools[url].join(', ')}` : "No tools selected"} />
                </ListItem>
              ))}
            </List>
          )}
        </Box>      
      )}

      {tabIndex === 1 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload a Swagger or OpenAPI specification file (JSON or YAML). All endpoints will be exposed as tools.
          </Typography>
          <Button
            variant="outlined"
            component="label"
            fullWidth
            startIcon={<UploadFileIcon />}
            sx={{ mb: 2 }}
          >
            Upload Spec File
            <input type="file" hidden accept=".json,.yaml,.yml" onChange={handleFileChange} />
          </Button>
          {swaggerSpecs.length > 0 && (
            <List dense sx={{ border: '1px solid #ccc', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
              {swaggerSpecs.map((spec) => (
                <ListItem
                  key={spec.name}
                  secondaryAction={
                    <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteSpec(spec.name)}>
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemText primary={spec.name} />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      )}


      {tabIndex === 2 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select other saved agents to make them available as tools for this agent.
          </Typography>
          {loadingAgents ? <CircularProgress /> : (
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="gofannon-agent-select-label">Select an Agent</InputLabel>
              <Select
                labelId="gofannon-agent-select-label"
                value={selectedAgentId}
                label="Select an Agent"
                onChange={(e) => setSelectedAgentId(e.target.value)}
              >
                {availableAgents.map((agent) => (
                  <MenuItem key={agent._id} value={agent._id}>
                    {agent.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleAddGofannonAgent} disabled={!selectedAgentId}>
              Add
            </Button>
          </Box>
          )}

          {gofannonAgents.length > 0 && (
             <List dense sx={{ border: '1px solid #ccc', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
             {gofannonAgents.map((agent) => (
               <ListItem
                 key={agent.id}
                 secondaryAction={
                   <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteGofannonAgent(agent.id)}>
                     <DeleteIcon />
                   </IconButton>
                 }
               >
                 <ListItemIcon>
                    <SmartToyIcon />
                 </ListItemIcon>
                 <ListItemText primary={agent.name} />
               </ListItem>
             ))}
           </List>
          )}
        </Box>
      )}
      
      <ToolsSelectionDialog
        open={toolsDialog.open}
        onClose={() => setToolsDialog({ ...toolsDialog, open: false })}
        mcpUrl={toolsDialog.mcpUrl}
        existingSelectedTools={toolsDialog.existingSelectedTools}
        onSaveSelectedTools={handleSaveSelectedTools}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={handleContinue}
        fullWidth
        sx={{ mt: 2 }}
      >
        Continue
      </Button>
    </Paper>
  );
};

export default ToolsScreen;
