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
  const [sessionId, setSessionId] = useState(null); // Retained for local session management if needed later
  const [configOpen, setConfigOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelParamSchema, setModelParamSchema] = useState({}); // Stores the schema for current model's parameters
  const [currentModelParams, setCurrentModelParams] = useState({}); // Stores the *values* for current model's parameters
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
      console.log("Providers data received: ", providersData);
      setProviders(providersData);
      
      const providerKeys = Object.keys(providersData);
      if (providerKeys.length > 0) {
        const defaultProvider = providerKeys[0];
        setSelectedProvider(defaultProvider);
        
        const models = Object.keys(providersData[defaultProvider].models);
        if (models.length > 0) {
          const defaultModel = models[0];
          setSelectedModel(defaultModel);
          // Access .parameters from the model object
          const modelParams = providersData[defaultProvider].models[defaultModel].parameters; 
          setModelParamSchema(modelParams);
          
          const defaultParams = {};
          Object.keys(modelParams).forEach(key => {
            defaultParams[key] = modelParams[key].default;
          });
          setCurrentModelParams(defaultParams);
        } else {
          // No models found for the default provider
          setSelectedModel('');
          setModelParamSchema({});
          setCurrentModelParams({});
        }
      } else {
        setError('No AI providers found.');
      }
    } catch (err) {
      setError('Failed to initialize chat: ' + err.message);
      console.error("Chat initialization error:", err);
    }
  };

  const handleSend = async () => {
    // Ensure input, session, and a selected model are available
    if (!input.trim() || !sessionId || !selectedProvider || !selectedModel) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(), // Keep timestamp for frontend display
    };

    // Update local messages state immediately to show user's message
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput(''); // Clear input field
    setLoading(true);
    setError(null);

    try {
      // Map local message objects to backend ChatMessage format ({role, content})
      // Ensure only 'role' and 'content' are sent to the backend
      const messagesForBackend = updatedMessages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      const response = await chatService.sendMessage(
        messagesForBackend, // Send the full conversation history
        {
          provider: selectedProvider,
          model: selectedModel,
          config: currentModelParams, // 'config' here will be mapped to 'parameters' in chatService
        }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]); // Add assistant's response to local state
    } catch (err) {
      setError('Failed to send message: ' + err.message);
      console.error("Error sending message:", err);
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
    
    const models = Object.keys(providers[provider]?.models || {});
    if (models.length > 0) {
      const defaultModel = models[0];
      setSelectedModel(defaultModel);
      const modelParams = providers[provider].models[defaultModel].parameters; // Access .parameters
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
    
    const modelParams = providers[selectedProvider].models[model].parameters; // Access .parameters
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
    // Ensure the value used by the control is the current state value, 
    // falling back to default if not yet set in state (e.g., on initial render before setCurrentModelParams)
    const controlledValue = value !== undefined ? value : paramConfig.default;

    if (paramConfig.type === 'float' || paramConfig.type === 'integer') { // 'int' changed to 'integer' to match provider_config.py
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
            // Step 0.1 for float, 1 for integer. Adjusted to 0.01 for more granular float control if needed.
            step={paramConfig.type === 'float' ? (paramConfig.step || 0.1) : 1} 
            marks
            valueLabelDisplay="auto"
          />
        </Box>
      );
    }

    // Default to TextField for other types (e.g., string). provider_config.py currently only has float/integer.
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

  const isChatReady = !loading && sessionId && selectedProvider && selectedModel;

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            AI Chat
          </Typography>
          <Chip 
            label={`${selectedProvider}${selectedModel ? '/' + selectedModel : ''}`} 
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
            disabled={!isChatReady}
          />
          <IconButton 
            color="primary" 
            onClick={handleSend}
            disabled={!isChatReady || !input.trim()}
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
          
          {selectedModel && Object.keys(modelParamSchema).map(paramName => 
            renderParamControl(paramName, modelParamSchema[paramName])
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
