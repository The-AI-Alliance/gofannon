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
  Alert,
  Chip,
} from '@mui/material';
import {
  Send as SendIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import chatService from '../services/chatService';
import ModelConfigDialog from '../components/ModelConfigDialog';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // State for Model Configuration
  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false);
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [modelParamSchema, setModelParamSchema] = useState({});
  const [currentModelParams, setCurrentModelParams] = useState({});
  const [selectedBuiltInTool, setSelectedBuiltInTool] = useState('');
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Correctly initialize session ID from the service instance.
    setSessionId(chatService.sessionId);
  }, []);

  // Fetch providers on component mount
  useEffect(() => {
    const fetchProviders = async () => {
      setLoadingProviders(true);
      setProvidersError(null);
      try {
        const providersData = await chatService.getProviders();
        setProviders(providersData);
  
        // Find first provider with a model and set it as default
        const providerKeys = Object.keys(providersData);
        let defaultProviderSet = false;
        for (const provider of providerKeys) {
          const models = Object.keys(providersData[provider].models || {});
          if (models.length > 0) {
            setSelectedProvider(provider);
            const defaultModel = models[0];
            setSelectedModel(defaultModel);
            const modelParams = providersData[provider].models[defaultModel].parameters;
            setModelParamSchema(modelParams);
  
            const defaultParams = {};
            Object.keys(modelParams).forEach(key => {
              defaultParams[key] = modelParams[key].default;
            });
            setCurrentModelParams(defaultParams);
            setSelectedBuiltInTool(''); // Reset tool on provider change
            defaultProviderSet = true;
            break; // exit after finding the first valid provider/model
          }
        }
        if (!defaultProviderSet) {
           setProvidersError('No available models found across all providers.');
        }
      } catch (err) {
        setProvidersError('Failed to fetch AI providers: ' + err.message);
        console.error("Error fetching providers for chat:", err);
      } finally {
        setLoadingProviders(false);
      }
    };
    fetchProviders();
  }, []);

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

      const response = await chatService.sendMessage(
        messagesForBackend,
        {
          provider: selectedProvider,
          model: selectedModel,
          // config: currentModelParams,
          parameters: currentModelParams,
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

  const isChatReady = !loading && sessionId && selectedProvider && selectedModel;

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            AI Chat
          </Typography>
          {loadingProviders ? (
            <CircularProgress size={24} />
          ) : selectedModel ? (
            <Chip
              label={`${selectedProvider}/${selectedModel}`}
              color="primary"
              variant="outlined"
              sx={{ mr: 2 }}
            />
          ) : null}
          <IconButton onClick={() => setIsModelConfigOpen(true)}>
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
                  sx={{ color: message.role === 'user' ? 'primary.contrastText' : 'text.secondary', mb: message.thoughts ? 1 : 0 }}
                />
                {message.thoughts && (
                  <Accordion sx={{ boxShadow: 'none', '&:before': { display: 'none' }, bgcolor: 'transparent', color: 'inherit' }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: message.role === 'user' ? 'primary.contrastText' : 'text.primary' }} />} sx={{ p: 0 }}>
                      <Typography variant="caption">Show Thoughts</Typography>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 0 }}>
                      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.8rem', margin: 0 }}>
                        {JSON.stringify(message.thoughts, null, 2)}
                      </pre>
                    </AccordionDetails>
                  </Accordion>
                )}
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
            disabled={!isChatReady || loadingProviders}
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={!isChatReady || !input.trim() || loadingProviders}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>

      <ModelConfigDialog
        open={isModelConfigOpen}
        onClose={() => setIsModelConfigOpen(false)}
        title="Chat Model Configuration"
        providers={providers}
        selectedProvider={selectedProvider}
        setSelectedProvider={setSelectedProvider}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        modelParamSchema={modelParamSchema}
        setModelParamSchema={setModelParamSchema}
        currentModelParams={currentModelParams}
        setCurrentModelParams={setCurrentModelParams}
        selectedBuiltInTool={selectedBuiltInTool}
        setSelectedBuiltInTool={setSelectedBuiltInTool}
        loadingProviders={loadingProviders}
        providersError={providersError}
      />
    </Container>
  );
};

export default ChatPage;