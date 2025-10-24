// webapp/packages/webui/src/pages/DemoCreationFlow/CanvasScreen.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useDemoFlow } from './DemoCreationFlowContext';
import demoService from '../../services/demoService';
import config from '../../config';
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
  Tooltip
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';

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

  useEffect(() => {
    const editDemoId = searchParams.get('edit');
    if (editDemoId && !editLoaded) {
      const loadDemoForEditing = async () => {
        setIsEditLoading(true);
        setError(null);
        try {
          const demoData = await demoService.getDemo(editDemoId);
          // Populate the context
          setSelectedApis(demoData.selectedApis);
          setModelConfig(demoData.modelConfig);
          setUserPrompt(demoData.userPrompt);
          setGeneratedCode(demoData.generatedCode);
          setAppName(demoData.name);
          setDescription(demoData.description);
          setEditLoaded(true); // Mark as loaded
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
   
  useEffect(() => {
    if (!isEditLoading && !modelConfig && selectedApis.length === 0 && !searchParams.get('edit')) {
      navigate('/create-demo/select-apis');
    }
  }, [modelConfig, selectedApis, navigate, isEditLoading, searchParams]);

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
    try {
      const code = await demoService.generateDemoAppCode({
        userPrompt,
        selectedApis,
        modelConfig,
      });
      setGeneratedCode(code);
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

  return (
    <Paper sx={{ p: 3, height: '85vh', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Create Demo App
      </Typography>

      {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ flexGrow: 1, display: 'flex', gap: 2, mt: 2, minHeight: 0 }}>
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
              disabled={isLoading || !userPrompt}
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
        <Box sx={{ flex: 1, border: '1px solid grey', borderRadius: 1 }}>
          <iframe
            srcDoc={iframeSrcDoc}
            title="Demo App Preview"
            sandbox="allow-scripts allow-forms"
            width="100%"
            height="100%"
            style={{ border: 'none' }}
          />
        </Box>
      </Box>
    </Paper>
  );
};

export default CanvasScreen;