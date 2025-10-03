import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Divider,
} from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import EditIcon from '@mui/icons-material/Edit';
import { useAgentFlow } from './AgentCreationFlowContext';

const SchemasScreen = () => {
  const { tools, description, inputSchema, outputSchema, setGeneratedCode } = useAgentFlow();
  const navigate = useNavigate();

  const mockBackendCallAndGenerateCode = () => {
    // This function simulates the backend call to generate code.
    // In a real scenario, you'd make an API request with `tools`, `description`, `inputSchema`, `outputSchema`.
    // For now, we set a mock "hello world" Python code.
    const mockPythonCode = `
import json

def agent_handler(input_data):
    """
    This is a mock agent handler.
    It receives input_data as a JSON string and returns an output_data JSON string.
    
    Agent Description: ${description || "No description provided."}
    Tools: ${Object.keys(tools).length > 0 ? Object.keys(tools).join(', ') : "No tools defined."}

    Input Schema:
    ${JSON.stringify(inputSchema, null, 2)}

    Output Schema:
    ${JSON.stringify(outputSchema, null, 2)}
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
    mockBackendCallAndGenerateCode();
    navigate('/create-agent/code');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 800, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Screen 3: Define Input/Output JSON (Optional)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        By default, input has `inputText` and output has `outputText`. You can
        optionally define more complex JSON structures here. (Edit disabled for POC)
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6">Input JSON Schema</Typography>
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
              <Typography variant="h6">Output JSON Schema</Typography>
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

      <Button
        variant="contained"
        color="primary"
        onClick={handleBuild}
        fullWidth
        startIcon={<CodeIcon />}
      >
        Build Agent Code
      </Button>
    </Paper>
  );
};

export default SchemasScreen;
