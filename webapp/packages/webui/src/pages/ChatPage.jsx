import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Alert,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Send as SendIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useNavigate, useLocation } from 'react-router-dom';
import chatService from '../services/chatService';
import ModelConfigDialog from '../components/ModelConfigDialog';

const ChatPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const initialMessageSent = useRef(false);

  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelParamSchema, setModelParamSchema] = useState({});
  const [currentModelParams, setCurrentModelParams] = useState({});
  const [selectedBuiltInTool, setSelectedBuiltInTool] = useState('');
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState(null);

  // Temporary state for dialog editing (so Cancel works properly)
  const [dialogProvider, setDialogProvider] = useState('');
  const [dialogModel, setDialogModel] = useState('');
  const [dialogParamSchema, setDialogParamSchema] = useState({});
  const [dialogParams, setDialogParams] = useState({});
  const [dialogBuiltInTool, setDialogBuiltInTool] = useState('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    setSessionId(chatService.sessionId);
  }, []);

  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      setProvidersError(null);
      try {
        const providersData = await chatService.getProviders();
        setProviders(providersData);
        
        // Check if we have initial state from FloatingChat
        const initialState = location.state;
        
        // Try to get saved selection from sessionStorage
        const savedProvider = sessionStorage.getItem('chat_provider');
        const savedModel = sessionStorage.getItem('chat_model');
        
        if (initialState?.provider && initialState?.model) {
          // Use the provider/model passed from FloatingChat
          const provider = initialState.provider;
          const model = initialState.model;
          
          setSelectedProvider(provider);
          setSelectedModel(model);
          
          // Save to sessionStorage for persistence
          sessionStorage.setItem('chat_provider', provider);
          sessionStorage.setItem('chat_model', model);
          
          const modelParams = providersData[provider]?.models?.[model]?.parameters || {};
          setModelParamSchema(modelParams);
          
          const defaultParams = {};
          Object.keys(modelParams).forEach(key => {
            if (modelParams[key].default !== null) {
              // Skip top_p for Anthropic - use temperature by default (they're mutually exclusive)
              if (key === 'top_p' && provider === 'anthropic') {
                return;
              }
              defaultParams[key] = modelParams[key].default;
            }
          });
          setCurrentModelParams(defaultParams);
          setSelectedBuiltInTool('');
        } else if (savedProvider && savedModel && providersData[savedProvider]?.models?.[savedModel]) {
          // Restore from sessionStorage
          setSelectedProvider(savedProvider);
          setSelectedModel(savedModel);
          
          const modelParams = providersData[savedProvider]?.models?.[savedModel]?.parameters || {};
          setModelParamSchema(modelParams);
          
          const defaultParams = {};
          Object.keys(modelParams).forEach(key => {
            if (modelParams[key].default !== null) {
              if (key === 'top_p' && savedProvider === 'anthropic') {
                return;
              }
              defaultParams[key] = modelParams[key].default;
            }
          });
          setCurrentModelParams(defaultParams);
          setSelectedBuiltInTool('');
        } else {
          // Use default provider/model
          const providerKeys = Object.keys(providersData);
          let defaultProviderSet = false;
          for (const provider of providerKeys) {
            const models = Object.keys(providersData[provider].models || {});
            if (models.length > 0) {
              setSelectedProvider(provider);
              const defaultModel = models[0];
              setSelectedModel(defaultModel);
              
              // Save to sessionStorage
              sessionStorage.setItem('chat_provider', provider);
              sessionStorage.setItem('chat_model', defaultModel);
              
              const modelParams = providersData[provider].models[defaultModel].parameters;
              setModelParamSchema(modelParams);
    
              const defaultParams = {};
              Object.keys(modelParams).forEach(key => {
                if (modelParams[key].default !== null) {
                  // Skip top_p for Anthropic - use temperature by default (they're mutually exclusive)
                  if (key === 'top_p' && provider === 'anthropic') {
                    return;
                  }
                  defaultParams[key] = modelParams[key].default;
                }
              });
              setCurrentModelParams(defaultParams);
              setSelectedBuiltInTool('');
              defaultProviderSet = true;
              break;
            }
          }
          if (!defaultProviderSet) {
             setProvidersError('No available models found across all providers.');
          }
        }
      } catch (err) {
        setProvidersError('Failed to fetch AI providers: ' + err.message);
        console.error("Error fetching providers for chat:", err);
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, [location.state]);

  // Auto-send initial message from FloatingChat
  useEffect(() => {
    const sendInitialMessage = async () => {
      const initialState = location.state;
      if (
        initialState?.initialMessage && 
        !initialMessageSent.current && 
        !loadingProviders && 
        sessionId && 
        selectedProvider && 
        selectedModel
      ) {
        initialMessageSent.current = true;
        
        const userMessage = {
          role: 'user',
          content: initialState.initialMessage,
          timestamp: new Date().toISOString(),
        };

        setMessages([userMessage]);
        setLoading(true);
        setError(null);

        try {
          // Clean up params for Anthropic - ensure we don't send both temperature and top_p
          let cleanedParams = { ...currentModelParams };
          if (selectedProvider === 'anthropic' && cleanedParams.temperature !== undefined && cleanedParams.top_p !== undefined) {
            // Prefer temperature, remove top_p
            delete cleanedParams.top_p;
          }

          const response = await chatService.sendMessage(
            [{ role: 'user', content: initialState.initialMessage }],
            {
              provider: selectedProvider,
              model: selectedModel,
              parameters: cleanedParams,
              builtInTool: selectedBuiltInTool,          
            }
          );

          const assistantMessage = {
            role: 'assistant',
            content: response.content,
            thoughts: response.thoughts,
            timestamp: new Date().toISOString(),
          };

          setMessages(prev => [...prev, assistantMessage]);
        } catch (err) {
          setError('Failed to send message: ' + err.message);
          console.error("Error sending initial message:", err);
        } finally {
          setLoading(false);
        }
        
        // Clear the location state to prevent re-sending on refresh
        window.history.replaceState({}, document.title);
      }
    };
    
    sendInitialMessage();
  }, [loadingProviders, sessionId, selectedProvider, selectedModel, location.state, currentModelParams, selectedBuiltInTool]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || !selectedProvider || !selectedModel) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const messagesForBackend = updatedMessages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      // Clean up params for Anthropic - ensure we don't send both temperature and top_p
      let cleanedParams = { ...currentModelParams };
      if (selectedProvider === 'anthropic' && cleanedParams.temperature !== undefined && cleanedParams.top_p !== undefined) {
        // Prefer temperature, remove top_p
        delete cleanedParams.top_p;
      }

      const response = await chatService.sendMessage(
        messagesForBackend,
        {
          provider: selectedProvider,
          model: selectedModel,
          parameters: cleanedParams,
          builtInTool: selectedBuiltInTool,          
        }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        thoughts: response.thoughts,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
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

  // Model config dialog handlers
  const handleOpenModelConfig = () => {
    // Copy current state to dialog state
    setDialogProvider(selectedProvider);
    setDialogModel(selectedModel);
    setDialogParamSchema(modelParamSchema);
    setDialogParams(currentModelParams);
    setDialogBuiltInTool(selectedBuiltInTool);
    setIsModelConfigOpen(true);
  };

  const handleCancelModelConfig = () => {
    setIsModelConfigOpen(false);
  };

  const handleSaveModelConfig = () => {
    // Copy dialog state to actual state
    setSelectedProvider(dialogProvider);
    setSelectedModel(dialogModel);
    setModelParamSchema(dialogParamSchema);
    
    // Save to sessionStorage for persistence
    sessionStorage.setItem('chat_provider', dialogProvider);
    sessionStorage.setItem('chat_model', dialogModel);
    
    // Clean up params for Anthropic - ensure we don't save both temperature and top_p
    let cleanedParams = { ...dialogParams };
    if (dialogProvider === 'anthropic' && cleanedParams.temperature !== undefined && cleanedParams.top_p !== undefined) {
      // Prefer temperature, remove top_p
      delete cleanedParams.top_p;
    }
    setCurrentModelParams(cleanedParams);
    
    setSelectedBuiltInTool(dialogBuiltInTool);
    setIsModelConfigOpen(false);
  };

  const isChatReady = !loading && sessionId && selectedProvider && selectedModel;

  return (
    <Box sx={{ height: 'calc(100vh - 56px)', display: 'flex', flexDirection: 'column', bgcolor: '#f8f9fa' }}>
      {/* Centered container to match agent/runs page widths */}
      <Box sx={{ maxWidth: 800, width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', height: '100%', pt: 4, px: 2 }}>
        {/* Header */}
        <Paper 
          sx={{ 
            px: 2, 
            py: 1.5, 
            display: 'flex', 
            alignItems: 'center', 
            borderRadius: 2,
            border: '1px solid #e4e4e7',
            bgcolor: '#fff',
            mb: 2
          }}
          elevation={0}
        >
          <IconButton size="small" onClick={() => navigate(-1)} sx={{ mr: 1 }}>
            <ArrowBackIcon sx={{ fontSize: 20 }} />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600, fontSize: '1rem' }}>
            Chat
          </Typography>
          {loadingProviders ? (
            <CircularProgress size={20} />
          ) : selectedModel ? (
            <Chip
              label={`${selectedProvider}/${selectedModel}`}
              size="small"
              sx={{ 
                mr: 1,
                bgcolor: '#f4f4f5',
                color: '#52525b',
                fontWeight: 500,
                fontSize: '0.75rem'
              }}
            />
          ) : null}
          <IconButton size="small" onClick={handleOpenModelConfig}>
            <SettingsIcon sx={{ fontSize: 20 }} />
          </IconButton>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

      {/* Messages */}
      {/* Messages area */}
      <Paper 
        elevation={0} 
        sx={{ 
          flexGrow: 1, 
          display: 'flex', 
          flexDirection: 'column',
          border: '1px solid #e4e4e7',
          borderRadius: 2,
          overflow: 'hidden',
          mb: 2
        }}
      >
        <List sx={{ flexGrow: 1, overflow: 'auto', p: 2, bgcolor: '#fafafa' }}>
        {messages.length === 0 && (
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            height: '100%',
            gap: 1
          }}>
            <BotIcon sx={{ fontSize: 48, color: '#d4d4d8' }} />
            <Typography variant="body1" color="text.secondary">
              Start a conversation
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Ask me anything
            </Typography>
          </Box>
        )}
        {messages.map((message, index) => (
          <ListItem
            key={index}
            alignItems="flex-start"
            sx={{
              flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
              px: 0,
            }}
          >
            <Box sx={{ 
              mx: 1, 
              mt: 0.5,
              p: 0.5,
              borderRadius: '50%',
              bgcolor: message.role === 'user' ? '#18181b' : '#e4e4e7',
              color: message.role === 'user' ? '#fff' : '#52525b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {message.role === 'user' ? <PersonIcon sx={{ fontSize: 18 }} /> : <BotIcon sx={{ fontSize: 18 }} />}
            </Box>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                maxWidth: '70%',
                bgcolor: message.role === 'user' ? '#18181b' : '#ffffff',
                color: message.role === 'user' ? '#fff' : '#18181b',
                borderRadius: 2,
                border: message.role === 'user' ? 'none' : '1px solid #e4e4e7',
              }}
            >
              <ListItemText
                primary={<Typography sx={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>{message.content}</Typography>}
                secondary={
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : '#a1a1aa',
                      mt: 0.5,
                      display: 'block'
                    }}
                  >
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </Typography>
                }
                sx={{ m: 0 }}
              />
              {message.thoughts && (
                <Accordion 
                  sx={{ 
                    boxShadow: 'none', 
                    '&:before': { display: 'none' }, 
                    bgcolor: 'transparent',
                    mt: 1
                  }}
                >
                  <AccordionSummary 
                    expandIcon={<ExpandMoreIcon sx={{ color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : '#71717a', fontSize: 18 }} />} 
                    sx={{ p: 0, minHeight: 'auto', '& .MuiAccordionSummary-content': { m: 0 } }}
                  >
                    <Typography variant="caption" sx={{ color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : '#71717a' }}>
                      Show Thoughts
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails sx={{ p: 0, pt: 1 }}>
                    <pre style={{ 
                      whiteSpace: 'pre-wrap', 
                      wordBreak: 'break-all', 
                      fontSize: '0.75rem', 
                      margin: 0,
                      color: message.role === 'user' ? 'rgba(255,255,255,0.8)' : '#52525b'
                    }}>
                      {JSON.stringify(message.thoughts, null, 2)}
                    </pre>
                  </AccordionDetails>
                </Accordion>
              )}
            </Paper>
          </ListItem>
        ))}
        {loading && (
          <ListItem sx={{ px: 0 }}>
            <Box sx={{ 
              mx: 1, 
              p: 0.5,
              borderRadius: '50%',
              bgcolor: '#e4e4e7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <BotIcon sx={{ fontSize: 18, color: '#52525b' }} />
            </Box>
            <CircularProgress size={20} sx={{ ml: 1 }} />
          </ListItem>
        )}
        <div ref={messagesEndRef} />
      </List>

      {/* Input area inside the same Paper */}
      <Box 
        sx={{ 
          p: 2, 
          borderTop: '1px solid #e4e4e7',
          bgcolor: '#fff'
        }}
      >
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={!isChatReady || loadingProviders}
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                bgcolor: '#f4f4f5',
                '& fieldset': { borderColor: '#e4e4e7' },
                '&:hover fieldset': { borderColor: '#a1a1aa' },
                '&.Mui-focused fieldset': { borderColor: '#18181b' },
              }
            }}
          />
          <IconButton
            onClick={handleSend}
            disabled={!isChatReady || !input.trim() || loadingProviders}
            sx={{ 
              bgcolor: '#18181b', 
              color: '#fff',
              '&:hover': { bgcolor: '#27272a' },
              '&.Mui-disabled': { bgcolor: '#e4e4e7', color: '#a1a1aa' }
            }}
          >
            <SendIcon sx={{ fontSize: 20 }} />
          </IconButton>
        </Box>
      </Box>
      </Paper>
      </Box>

      <ModelConfigDialog
        open={isModelConfigOpen}
        onClose={handleCancelModelConfig}
        onSave={handleSaveModelConfig}
        title="Chat Model Configuration"
        providers={providers}
        selectedProvider={dialogProvider}
        setSelectedProvider={setDialogProvider}
        selectedModel={dialogModel}
        setSelectedModel={setDialogModel}
        modelParamSchema={dialogParamSchema}
        setModelParamSchema={setDialogParamSchema}
        currentModelParams={dialogParams}
        setCurrentModelParams={setDialogParams}
        selectedBuiltInTool={dialogBuiltInTool}
        setSelectedBuiltInTool={setDialogBuiltInTool}
        loadingProviders={loadingProviders}
        providersError={providersError}
      />
    </Box>
  );
};

export default ChatPage;