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
  FormGroup,
  Checkbox,
  FormControlLabel,
  Tooltip,
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
  const hasValue = (val) => val !== undefined && val !== null;

  const getMutuallyExclusiveParams = (paramName, schema = modelParamSchema) => {
    if (!schema) return [];
    const paramConfig = schema[paramName] || {};
    const forward = paramConfig.mutually_exclusive_with || [];
    const reverse = Object.entries(schema)
      .filter(([otherName, config]) => (config?.mutually_exclusive_with || []).includes(paramName))
      .map(([otherName]) => otherName);
    return Array.from(new Set([...forward, ...reverse]));
  };

  const buildDefaultParams = (paramSchema) => {
    const defaults = {};
    Object.entries(paramSchema || {}).forEach(([key, param]) => {
      if (param.default === null || param.default === undefined) return;
      const conflicts = getMutuallyExclusiveParams(key, paramSchema);
      const conflictAlreadySet = conflicts.some((conflict) => hasValue(defaults[conflict]));
      if (conflictAlreadySet) return;
      defaults[key] = param.default;
    });
    return defaults;
  };

  const clearParamValue = (paramName) => {
    setCurrentModelParams((prev) => {
      const updated = { ...prev };
      delete updated[paramName];
      return updated;
    });
  };

  const handleProviderChange = (e) => {
    const provider = e.target.value;
    setSelectedProvider(provider);
    
    const models = Object.keys(providers[provider]?.models || {});
    if (models.length > 0) {
      const defaultModel = models[0];
      setSelectedModel(defaultModel);
      const modelParams = providers[provider].models[defaultModel].parameters; 
      setModelParamSchema(modelParams);
      
      setCurrentModelParams(buildDefaultParams(modelParams));
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
    
    setCurrentModelParams(buildDefaultParams(modelParams));
    // Reset built-in tool selection when model changes
    if (setSelectedBuiltInTool) setSelectedBuiltInTool('');
  };

  const handleParamChange = (paramName, value) => {
    setCurrentModelParams(prev => ({
      ...Object.fromEntries(
        Object.entries(prev).filter(
          ([key]) => !getMutuallyExclusiveParams(paramName).includes(key)
        )
      ),
      [paramName]: value,
    }));
  };

  const isParamDisabled = (paramName) => {
    const conflicts = getMutuallyExclusiveParams(paramName);
    return conflicts.some((conflict) => hasValue(currentModelParams[conflict]));
  };

  const getDisableReason = (paramName) => {
    const conflicts = getMutuallyExclusiveParams(paramName).filter((conflict) =>
      hasValue(currentModelParams[conflict])
    );

    if (!conflicts.length) {
      return '';
    }

    const formattedConflicts = conflicts.join(', ');
    return `Clear ${formattedConflicts} to configure ${paramName}.`;
  };

  const renderClearAction = (paramName) => {
    if (!getMutuallyExclusiveParams(paramName).length || !hasValue(currentModelParams[paramName])) {
      return null;
    }

    return (
      <Button size="small" variant="text" onClick={() => clearParamValue(paramName)}>
        Clear
      </Button>
    );
  };

  const builtInToolsForModel =
    providers?.[selectedProvider]?.models?.[selectedModel]?.built_in_tools || [];
  
  const renderSchemaParamControls = () => {
    if (!modelParamSchema || Object.keys(modelParamSchema).length === 0) {
        return <Typography color="text.secondary">This agent has no configurable input parameters.</Typography>;
    }

    const fields = Object.entries(modelParamSchema).map(([paramName, paramConfig]) => {
      // Don't render a field for inputText, as it comes from the main chat input
      if (paramName === 'inputText') {
        return null;
      }
      const value = currentModelParams[paramName];
      const controlledValue = value !== undefined ? value : (paramConfig.default || '');
      
      return (
        <TextField
          key={paramName}
          fullWidth
          label={paramConfig.description || paramName}
          value={controlledValue}
          onChange={(e) => handleParamChange(paramName, e.target.value)}
          sx={{ mb: 2 }}
          type={paramConfig.type === 'integer' || paramConfig.type === 'float' ? 'number' : 'text'}
          helperText={`Type: ${paramConfig.type}`}
        />
      );
    }).filter(Boolean); // remove nulls

    return fields.length > 0 ? fields : <Typography color="text.secondary">The primary input for this agent is the chat message. It has no other configurable parameters.</Typography>;
  };

  const renderParamControl = (paramName, paramConfig) => {
    const value = currentModelParams[paramName];
    const controlledValue = value !== undefined ? value : paramConfig.default;
    const disabled = isParamDisabled(paramName);
    const disableReason = getDisableReason(paramName);
    const clearAction = renderClearAction(paramName);
    const wrapWithTooltip = (node) => (
      disabled ? (
        <Tooltip key={paramName} title={disableReason} placement="top">
          <Box component="span" sx={{ display: 'block', width: '100%' }}>
            {node}
          </Box>
        </Tooltip>
      ) : node
    );

    if (paramConfig.type === 'float' || paramConfig.type === 'integer') {
      return wrapWithTooltip(
        <Box key={paramName} sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography gutterBottom variant="body2" color="text.secondary" sx={{ mr: 1 }}>
              {paramConfig.description || paramName}: <Typography component="span" variant="body1" color="text.primary">{controlledValue}</Typography>
            </Typography>
            {clearAction}
          </Box>
          <Slider
            value={controlledValue}
            onChange={(e, newValue) => handleParamChange(paramName, newValue)}
            min={paramConfig.min}
            max={paramConfig.max}
            step={paramConfig.type === 'float' ? (paramConfig.step || 0.1) : 1} 
            marks
            valueLabelDisplay="auto"
            disabled={disabled}
          />
        </Box>
      );
    }

    if (paramConfig.type === 'choice') {
      return wrapWithTooltip(
        <FormControl fullWidth key={paramName} sx={{ mb: 2 }} disabled={disabled}>
          <InputLabel>{paramConfig.description || paramName}</InputLabel>
          <Select
            value={controlledValue} // controlledValue will now be the string choice
            label={paramConfig.description || paramName}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            disabled={disabled}
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

      return wrapWithTooltip(
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
                    disabled={disabled}
                  />
                }
                label={choice}
                disabled={disabled}
              />
            ))}
          </FormGroup>
        </Box>
      );
    }

    return wrapWithTooltip(
      <TextField
        key={paramName}
        fullWidth
        label={paramConfig.description || paramName}
        value={controlledValue}
        onChange={(e) => handleParamChange(paramName, e.target.value)}
        sx={{ mb: 2 }}
        type={paramConfig.type === 'integer' ? 'number' : 'text'}
        disabled={disabled}
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
                      onChange={(e) => {
                        if (setSelectedBuiltInTool) {
                          setSelectedBuiltInTool(e.target.value);
                        }
                      }}
                      label="Built-in Tool (Optional)"
                      renderValue={(selected) => {
                        if (!selected) return <em>None</em>;
                        const tool = builtInToolsForModel.find(t => t.id === selected);
                        return tool ? tool.id : selected;
                      }}
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
              {selectedProvider === 'gofannon' ? 'Agent Input Parameters' : 'Model Parameters'}
            </Typography>
            
            {selectedModel && (
              selectedProvider === 'gofannon'
                ? renderSchemaParamControls()
                : Object.keys(modelParamSchema)
                    .filter(paramName => {
                      const param = modelParamSchema[paramName];
                      // Skip params with null default
                      if (param.default === null) return false;
                      return true;
                    })
                    .map(paramName =>
                      renderParamControl(paramName, modelParamSchema[paramName])
                    )
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
