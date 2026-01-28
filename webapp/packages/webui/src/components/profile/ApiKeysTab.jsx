import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  TextField,
  Button,
  Alert,
  AlertTitle,
  Chip,
  IconButton,
  InputAdornment,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Save,
  Delete,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import userService from '../../services/userService';

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', description: 'GPT-4, GPT-3.5, and other OpenAI models' },
  { id: 'anthropic', name: 'Anthropic', description: 'Claude models' },
  { id: 'gemini', name: 'Google Gemini', description: 'Google Gemini models' },
  { id: 'perplexity', name: 'Perplexity', description: 'Perplexity AI models' },
];

const ApiKeyRow = ({ provider, apiKey, onSave, onDelete, isLoading }) => {
  const [value, setValue] = useState('');
  const [showValue, setShowValue] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const hasKey = Boolean(apiKey);

  const handleSave = () => {
    if (value.trim()) {
      onSave(provider.id, value.trim());
      setIsEditing(false);
      setValue('');
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setValue('');
  };

  const handleDelete = () => {
    onDelete(provider.id);
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Stack spacing={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="subtitle1" fontWeight="medium">
              {provider.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {provider.description}
            </Typography>
          </Box>
          <Chip
            icon={hasKey ? <CheckCircle /> : <Cancel />}
            label={hasKey ? 'Configured' : 'Not configured'}
            color={hasKey ? 'success' : 'default'}
            size="small"
          />
        </Box>

        <Divider />

        {isEditing ? (
          <TextField
            fullWidth
            label="API Key"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            type={showValue ? 'text' : 'password'}
            placeholder={`Enter your ${provider.name} API key`}
            disabled={isLoading}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowValue(!showValue)}
                    edge="end"
                    size="small"
                  >
                    {showValue ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        ) : (
          <TextField
            fullWidth
            label="API Key"
            value={hasKey ? '••••••••••••••••••••••••••' : ''}
            disabled
            placeholder="No API key configured"
          />
        )}

        <Box display="flex" gap={1} justifyContent="flex-end">
          {isEditing ? (
            <>
              <Button
                variant="outlined"
                size="small"
                onClick={handleCancel}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={isLoading ? <CircularProgress size={16} /> : <Save />}
                onClick={handleSave}
                disabled={isLoading || !value.trim()}
              >
                Save
              </Button>
            </>
          ) : (
            <>
              {hasKey && (
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<Delete />}
                  onClick={handleDelete}
                  disabled={isLoading}
                >
                  Remove
                </Button>
              )}
              <Button
                variant="contained"
                size="small"
                onClick={() => setIsEditing(true)}
                disabled={isLoading}
              >
                {hasKey ? 'Update' : 'Add Key'}
              </Button>
            </>
          )}
        </Box>
      </Stack>
    </Paper>
  );
};

const ApiKeysTab = () => {
  const [apiKeys, setApiKeys] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingProvider, setSavingProvider] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await userService.getApiKeys();
      setApiKeys(data);
    } catch (err) {
      setError(err.message || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (provider, apiKey) => {
    try {
      setSavingProvider(provider);
      setError(null);
      setSuccessMessage(null);
      await userService.updateApiKey(provider, apiKey);
      await loadApiKeys();
      setSuccessMessage(`${PROVIDERS.find((p) => p.id === provider)?.name} API key saved successfully.`);
    } catch (err) {
      setError(err.message || `Failed to save ${provider} API key`);
    } finally {
      setSavingProvider(null);
    }
  };

  const handleDelete = async (provider) => {
    try {
      setSavingProvider(provider);
      setError(null);
      setSuccessMessage(null);
      await userService.deleteApiKey(provider);
      await loadApiKeys();
      setSuccessMessage(`${PROVIDERS.find((p) => p.id === provider)?.name} API key removed successfully.`);
    } catch (err) {
      setError(err.message || `Failed to remove ${provider} API key`);
    } finally {
      setSavingProvider(null);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        API Keys
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <AlertTitle>About API Keys</AlertTitle>
        Configure your own API keys for LLM providers. These keys are stored securely in your
        profile and take precedence over system-wide keys. If you don&apos;t provide a key for a
        provider, the system will fall back to using environment variables (if configured).
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Stack spacing={1}>
          {PROVIDERS.map((provider) => (
            <ApiKeyRow
              key={provider.id}
              provider={provider}
              apiKey={apiKeys[`${provider.id}ApiKey`]}
              onSave={handleSave}
              onDelete={handleDelete}
              isLoading={savingProvider === provider.id}
            />
          ))}
        </Stack>
      )}
    </Box>
  );
};

export default ApiKeysTab;
