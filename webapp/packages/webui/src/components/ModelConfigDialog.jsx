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
  };

  const handleParamChange = (paramName, value) => {
    setCurrentModelParams(prev => ({
      ...prev,
      [paramName]: value,
    }));
  };

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
            value={controlledValue}
            label={paramConfig.description || paramName}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
          >
            {paramConfig.choices.map((choice, index) => (
              <MenuItem key={index} value={index}>{choice}</MenuItem>
            ))}
          </Select>
        </FormControl>
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
  loadingProviders: PropTypes.bool.isRequired,
  providersError: PropTypes.string,
};

ModelConfigDialog.defaultProps = {
  providersError: null,
  onSave: null,
};

export default ModelConfigDialog;