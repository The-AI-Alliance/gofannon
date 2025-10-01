import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Container,
  Paper,
  TextField,
  IconButton,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Divider,
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
  Alert,
  Chip,
} from '@mui/material';
import {
  Send as SendIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import chatService from '../services/chatService';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelConfig, setModelConfig] = useState({});
  const [currentModelParams, setCurrentModelParams] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    initializeChat();
  }, []);

  const initializeChat = async () => {
    try {
      const session = await chatService.createSession();
      setSessionId(session.session_id);
      
      const providersData = await chatService.getProviders();
      setProviders(providersData);
      
      const providerKeys = Object.keys(providersData);
      if (providerKeys.length > 0) {
        const defaultProvider = providerKeys[0];
        setSelectedProvider(defaultProvider);
        
        const models = Object.keys(providersData[defaultProvider].models);
        if (models.length > 0) {
          setSelectedModel(models[0]);
          const modelParams = providersData[defaultProvider].models[models[0]];
          setModelConfig(modelParams);
          
          const defaultParams = {};
          Object.keys(modelParams).forEach(key => {
            defaultParams[key] = modelParams[key].default;
          });
          setCurrentModelParams(defaultParams);
        }
      }
    } catch (err) {
      setError('Failed to initialize chat: ' + err.message);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !sessionId) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const response = await chatService.sendMessage(
        input,
        {
          provider: selectedProvider,
          model: selectedModel,
          config: currentModelParams,
        }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError('Failed to send message: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleProviderChange = (e) => {
    const provider = e.target.value;
    setSelectedProvider(provider);
    
    const models = Object.keys(providers[provider].models);
    if (models.length > 0) {
      setSelectedModel(models[0]);
      const modelParams = providers[provider].models[models[0]];
      setModelConfig(modelParams);
      
      const defaultParams = {};
      Object.keys(modelParams).forEach(key => {
        defaultParams[key] = modelParams[key].default;
      });
      setCurrentModelParams(defaultParams);
    }
  };

  const handleModelChange = (e) => {
    const model = e.target.value;
    setSelectedModel(model);
    
    const modelParams = providers[selectedProvider].models[model];
    setModelConfig(modelParams);
    
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

    if (paramConfig.type === 'float' || paramConfig.type === 'int') {
      return (
        <Box key={paramName} sx={{ mb: 2 }}>
          <Typography gutterBottom>
            {paramName}: {value}
          </Typography>
          <Slider
            value={value === undefined ? paramConfig.default : value}
            onChange={(e, newValue) => handleParamChange(paramName, newValue)}
            min={paramConfig.min}
            max={paramConfig.max}
            step={paramConfig.type === 'float' ? 0.01 : 1}
            marks
            valueLabelDisplay="auto"
          />
        </Box>
      );
    }

    if (paramConfig.acceptable_values) {
      return (
        <FormControl key={paramName} fullWidth sx={{ mb: 2 }}>
          <InputLabel>{paramName}</InputLabel>
          <Select
            value={value === undefined ? paramConfig.default : value}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            label={paramName}
          >
            {paramConfig.acceptable_values.map(val => (
              <MenuItem key={val} value={val}>{val}</MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }

    return (
      <TextField
        key={paramName}
        fullWidth
        label={paramName}
        value={value === undefined ? paramConfig.default : value}
        onChange={(e) => handleParamChange(paramName, e.target.value)}
        sx={{ mb: 2 }}
      />
    );
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            AI Chat
          </Typography>
          <Chip 
            label={`${selectedProvider}/${selectedModel}`} 
            color="primary" 
            variant="outlined"
            sx={{ mr: 2 }}
          />
          <IconButton onClick={() => setConfigOpen(true)}>
            <SettingsIcon />
          </IconButton>
        </Box>

        {error && (
          <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <List sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
          {messages.map((message, index) => (
            <ListItem
              key={index}
              alignItems="flex-start"
              sx={{
                flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              <Box sx={{ mx: 1 }}>
                {message.role === 'user' ? <PersonIcon /> : <BotIcon />}
              </Box>
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  bgcolor: message.role === 'user' ? 'primary.light' : 'grey.100',
                  color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                  overflowWrap: 'break-word',
                }}
              >
                <ListItemText
                  primary={<Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>}
                  secondary={new Date(message.timestamp).toLocaleTimeString()}
                  sx={{ color: message.role === 'user' ? 'primary.contrastText' : 'text.secondary' }}
                />
              </Paper>
            </ListItem>
          ))}
          {loading && (
            <ListItem>
              <Box sx={{ mx: 1 }}>
                <BotIcon />
              </Box>
              <CircularProgress size={20} />
            </ListItem>
          )}
          <div ref={messagesEndRef} />
        </List>

        <Divider />
        
        <Box sx={{ p: 2, display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading || !sessionId}
          />
          <IconButton 
            color="primary" 
            onClick={handleSend}
            disabled={loading || !input.trim() || !sessionId}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>

      <Dialog open={configOpen} onClose={() => setConfigOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Model Configuration</DialogTitle>
        <DialogContent>
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
          
          {Object.keys(modelConfig).map(paramName => 
            renderParamControl(paramName, modelConfig[paramName])
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ChatPage;