import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  TextField,
  Button,
  Alert,
  Chip,
  IconButton,
  InputAdornment,
  CircularProgress,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Save as SaveIcon,
  Delete as DeleteIcon,
  CheckCircle,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import userService from '../../services/userService';

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', description: 'GPT-4, GPT-3.5, and other OpenAI models' },
  { id: 'anthropic', name: 'Anthropic', description: 'Claude models' },
  { id: 'gemini', name: 'Google Gemini', description: 'Google Gemini models' },
  { id: 'perplexity', name: 'Perplexity', description: 'Perplexity AI models' },
  { id: 'openrouter', name: 'OpenRouter', description: 'Unified access to xAI Grok, DeepSeek, Qwen, Llama, and many other models' },
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

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {provider.name}
            </Typography>
            {hasKey && (
              <Chip
                icon={<CheckCircle sx={{ fontSize: 14 }} />}
                label="Configured"
                size="small"
                color="success"
                sx={{ height: 20, fontSize: '0.68rem' }}
              />
            )}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            {provider.description}
          </Typography>

          <Box sx={{ mt: 1.5 }}>
            {isEditing ? (
              <TextField
                fullWidth
                size="small"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                type={showValue ? 'text' : 'password'}
                placeholder={`Enter your ${provider.name} API key`}
                disabled={isLoading}
                autoFocus
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowValue(!showValue)}
                        edge="end"
                        size="small"
                      >
                        {showValue ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            ) : (
              <TextField
                fullWidth
                size="small"
                value={hasKey ? '••••••••••••••••••••••••••' : ''}
                disabled
                placeholder="No API key configured"
              />
            )}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0, mt: 0.25 }}>
          {isEditing ? (
            <>
              <Button size="small" onClick={handleCancel} disabled={isLoading}>
                Cancel
              </Button>
              <Button
                size="small"
                variant="contained"
                startIcon={isLoading ? <CircularProgress size={14} color="inherit" /> : <SaveIcon sx={{ fontSize: 16 }} />}
                onClick={handleSave}
                disabled={isLoading || !value.trim()}
              >
                Save
              </Button>
            </>
          ) : (
            <>
              {hasKey && (
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => onDelete(provider.id)}
                  disabled={isLoading}
                  title="Remove API key"
                  aria-label={`Remove ${provider.name} API key`}
                >
                  <DeleteIcon sx={{ fontSize: 18 }} />
                </IconButton>
              )}
              <Button
                size="small"
                variant={hasKey ? 'outlined' : 'contained'}
                onClick={() => setIsEditing(true)}
                disabled={isLoading}
              >
                {hasKey ? 'Update' : 'Add key'}
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

const ApiKeysTab = () => {
  const navigate = useNavigate();
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

  // Match the app's "page chrome" pattern used by DataStoresPage,
  // SavedAgentsPage, etc.: constrained max width, back-arrow + h5
  // title, optional helper text below.
  return (
    <Box sx={{ p: 3, maxWidth: 900, margin: '0 auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <IconButton size="small" onClick={() => navigate('/')} sx={{ mr: 1 }}>
          <ArrowBackIcon sx={{ fontSize: 20 }} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          API Keys
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Configure your own API keys for LLM providers. Keys you set here take
        precedence over system-wide environment variables. Stored encrypted on
        the server and only visible to you.
      </Typography>

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
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Stack spacing={1.5}>
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
