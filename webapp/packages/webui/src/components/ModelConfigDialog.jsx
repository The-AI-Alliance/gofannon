// webapp/packages/webui/src/components/ModelConfigDialog.jsx
import React from 'react';
import PropTypes from 'prop-types';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Typography,
  Box,
  Divider,
  TextField,
  CircularProgress,
  Alert,
  FormGroup, // Import FormGroup
  Checkbox, // Import Checkbox
  FormControlLabel, // Import FormControlLabel
} from '@mui/material';

const ModelConfigDialog = ({
  open,
  onClose,
  onSave,
  title,
  providers,
  selectedProvider,
  setSelectedProvider,
  selectedModel,
  setSelectedModel,
  modelParamSchema,
  setModelParamSchema,
  currentModelParams,
  setCurrentModelParams,
  selectedBuiltInTool,
  setSelectedBuiltInTool,
  loadingProviders,
  providersError,
}) => {

  const handleProviderChange = (e) => {
    const provider = e.target.value;
    setSelectedProvider(provider);
    
    const models = Object.keys(providers[provider]?.models || {});
    if (models.length > 0) {
      const defaultModel = models[0];
      setSelectedModel(defaultModel);
      const modelParams = providers[provider].models[defaultModel].parameters; 
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
    // Reset built-in tool selection when provider changes
    if (setSelectedBuiltInTool) setSelectedBuiltInTool('');
  };

  const handleModelChange = (e) => {
    const model = e.target.value;
    setSelectedModel(model);
    
    const modelParams = providers[selectedProvider].models[model].parameters; 

    setModelParamSchema(modelParams);
    
    const defaultParams = {};
    Object.keys(modelParams).forEach(key => {
      defaultParams[key] = modelParams[key].default;
    });
    setCurrentModelParams(defaultParams);
    // Reset built-in tool selection when model changes
    if (setSelectedBuiltInTool) setSelectedBuiltInTool('');
  };

  const handleParamChange = (paramName, value) => {
    setCurrentModelParams(prev => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const builtInToolsForModel =
  providers?.[selectedProvider]?.models?.[selectedModel]?.built_in_tools || [];

  const renderParamControl = (paramName, paramConfig) => {
    const value = currentModelParams[paramName];
    const controlledValue = value !== undefined ? value : paramConfig.default;

    if (paramConfig.type === 'float' || paramConfig.type === 'integer') {
      return (
        <Box key={paramName} sx={{ mb: 2 }}>
          <Typography gutterBottom variant="body2" color="text.secondary">
            {paramConfig.description || paramName}: <Typography component="span" variant="body1" color="text.primary">{controlledValue}</Typography>
          </Typography>
          <Slider
            value={controlledValue}
            onChange={(e, newValue) => handleParamChange(paramName, newValue)}
            min={paramConfig.min}
            max={paramConfig.max}
            step={paramConfig.type === 'float' ? (paramConfig.step || 0.1) : 1} 
            marks
            valueLabelDisplay="auto"
          />
        </Box>
      );
    }

    if (paramConfig.type === 'choice') {
      return (
        <FormControl fullWidth key={paramName} sx={{ mb: 2 }}>
          <InputLabel>{paramConfig.description || paramName}</InputLabel>
          <Select
            value={controlledValue} // controlledValue will now be the string choice
            label={paramConfig.description || paramName}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
          >
            {paramConfig.choices.map((choice) => ( // Iterate over choices directly
              <MenuItem key={choice} value={choice}>{choice}</MenuItem> // Value is the choice string
            ))}
          </Select>
        </FormControl>
      );
    }

    if (paramConfig.type === 'list_choice') { // New rendering for list_choice
      const selectedChoices = new Set(Array.isArray(controlledValue) ? controlledValue : []);
      
      const handleToggleChoice = (choice) => {
        const newSelected = new Set(selectedChoices);
        if (newSelected.has(choice)) {
          newSelected.delete(choice);
        } else {
          newSelected.add(choice);
        }
        handleParamChange(paramName, Array.from(newSelected)); // Update with array of selected strings
      };

      return (
        <Box key={paramName} sx={{ mb: 2 }}>
          <Typography gutterBottom variant="body2" color="text.secondary">
            {paramConfig.description || paramName}
          </Typography>
          <FormGroup>
            {paramConfig.choices.map((choice) => (
              <FormControlLabel
                key={choice}
                control={
                  <Checkbox
                    checked={selectedChoices.has(choice)}
                    onChange={() => handleToggleChoice(choice)}
                  />
                }
                label={choice}
              />
            ))}
          </FormGroup>
        </Box>
      );
    }

    return (
      <TextField
        key={paramName}
        fullWidth
        label={paramConfig.description || paramName}
        value={controlledValue}
        onChange={(e) => handleParamChange(paramName, e.target.value)}
        sx={{ mb: 2 }}
        type={paramConfig.type === 'integer' ? 'number' : 'text'}
      />
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {loadingProviders && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
            <CircularProgress />
          </Box>
        )}
        {providersError && (
          <Alert severity="error" sx={{ my: 2 }}>
            {providersError}
          </Alert>
        )}
        {!loadingProviders && !providersError && Object.keys(providers).length === 0 && (
          <Alert severity="warning" sx={{ my: 2 }}>
            No AI providers found. Please check your backend configuration.
          </Alert>
        )}

        {!loadingProviders && !providersError && Object.keys(providers).length > 0 && (
          <>
            <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
              <InputLabel>Provider</InputLabel>
              <Select
                value={selectedProvider}
                onChange={handleProviderChange}
                label="Provider"
              >
                {Object.keys(providers).map(provider => (
                  <MenuItem key={provider} value={provider}>{provider}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {selectedProvider && (
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Model</InputLabel>
                <Select
                  value={selectedModel}
                  onChange={handleModelChange}
                  label="Model"
                >
                  {Object.keys(providers[selectedProvider]?.models || {}).map(model => (
                    <MenuItem key={model} value={model}>{model}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}

            {Array.isArray(builtInToolsForModel) &&
                builtInToolsForModel.length > 0 && (
                  <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel>Built-in Tool (Optional)</InputLabel>
                    <Select
                      value={selectedBuiltInTool || ''}
                      onChange={(e) =>
                        setSelectedBuiltInTool
                          ? setSelectedBuiltInTool(e.target.value)
                          : null
                      }
                      label="Built-in Tool (Optional)"
                    >
                      <MenuItem value="">
                        <em>None</em>
                      </MenuItem>
                      {builtInToolsForModel.map((tool) => (
                        <MenuItem key={tool.id} value={tool.id}>
                          {/* Show id and description for clarity */}
                          <Box>
                            <Typography variant="body2">{tool.id}</Typography>
                            {tool.description && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                {tool.description}
                              </Typography>
                            )}
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}

            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Model Parameters
            </Typography>
            
            {selectedModel && Object.keys(modelParamSchema).map(paramName => 
              renderParamControl(paramName, modelParamSchema[paramName])
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{onSave ? 'Cancel' : 'Close'}</Button>
        {onSave && (
          <Button onClick={onSave} variant="contained" disabled={!selectedProvider || !selectedModel}>
            Save
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

ModelConfigDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  providers: PropTypes.object.isRequired,
  selectedProvider: PropTypes.string.isRequired,
  setSelectedProvider: PropTypes.func.isRequired,
  selectedModel: PropTypes.string.isRequired,
  setSelectedModel: PropTypes.func.isRequired,
  modelParamSchema: PropTypes.object.isRequired,
  setModelParamSchema: PropTypes.func.isRequired,
  currentModelParams: PropTypes.object.isRequired,
  setCurrentModelParams: PropTypes.func.isRequired,
  selectedBuiltInTool: PropTypes.string,
  setSelectedBuiltInTool: PropTypes.func,
  loadingProviders: PropTypes.bool.isRequired,
  providersError: PropTypes.string,
};

ModelConfigDialog.defaultProps = {
  providersError: null,
  onSave: null,
  selectedBuiltInTool: '',
  setSelectedBuiltInTool: () => {},
};

export default ModelConfigDialog;