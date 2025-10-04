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
  Chip,
  CircularProgress
} from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import EditIcon from '@mui/icons-material/Edit';
import SettingsIcon from '@mui/icons-material/Settings'; // Import SettingsIcon
import { useAgentFlow } from './AgentCreationFlowContext';
import chatService from '../../services/chatService'; // Re-use chatService to fetch providers
import ModelConfigDialog from '../../components/ModelConfigDialog'; // Import the new component

const SchemasScreen = () => {
  const { tools, description, inputSchema, outputSchema, setGeneratedCode } = useAgentFlow();
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

  const mockBackendCallAndGenerateCode = (agentModelConfig) => {
    // Extract model configuration for the generated code
    const { provider, model, parameters } = agentModelConfig;

    const mockPythonCode = `
import json

def agent_handler(input_data):
    """
    This is a mock agent handler.
    It receives input_data as a JSON string and returns an output_data JSON string.
    
    Agent Description: ${description || "No description provided."}

    Tools: ${
      Object.entries(tools)
        .filter(([, selectedTools]) => selectedTools.length > 0)
        .map(([url, selectedTools]) => 
          `${url} (using: ${selectedTools.join(', ')})`
        )
        .join('\n      ')
      || "No tools defined."
    }

    Input Schema:\n    ${JSON.stringify(inputSchema, null, 2)}

    Output Schema:\n    ${JSON.stringify(outputSchema, null, 2)}

    Model for Code Generation:
      Provider: ${provider || 'N/A'}
      Model: ${model || 'N/A'}
      Parameters: ${JSON.stringify(parameters, null, 2)}
    """
    
    # Parse the input JSON
    input_obj = json.loads(input_data)
    
    # Process the input - for now, just echo and add a greeting
    output_obj = {
        "outputText": f"Hello from your agent! You said: '{input_obj.get('inputText', '')}'"
    }
    
    # Return the output as a JSON string
    return json.dumps(output_obj)

if __name__ == "__main__":
    # Example usage for testing
    test_input = json.dumps({"inputText": "What is the weather like today?"})
    result = agent_handler(test_input)
    print(f"Agent Output: {result}")
`;
    setGeneratedCode(mockPythonCode);
  };

  const handleBuild = () => {
    if (!selectedProvider || !selectedModel) {
      setProvidersError('Please select a model for code generation.');
      return;
    }
    mockBackendCallAndGenerateCode({
      provider: selectedProvider,
      model: selectedModel,
      parameters: currentModelParams,
    });
    navigate('/create-agent/code');
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
        startIcon={<CodeIcon />}
        disabled={!isModelSelected}
      >
        Build Agent Code
      </Button>

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