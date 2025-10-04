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
import chatService from '../services/chatService';
import ModelConfigDialog from '../components/ModelConfigDialog'; // New component import

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [chatModelConfig, setChatModelConfig] = useState({
    provider: '',
    model: '',
    parameters: {},
  });
  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Initial setup: just get session ID. Model config will be handled by the dialog.
    const session = chatService.createSession(); // This just returns a local session ID for now
    setSessionId(session.session_id);
  }, []);

  // Function passed to ModelConfigDialog to update the chatModelConfig state
  const handleModelConfigSave = (newConfig) => {
    setChatModelConfig(newConfig);
    setIsModelConfigOpen(false); // Close the dialog after saving
  };

  const handleSend = async () => {
    if (!input.trim() || !sessionId || !chatModelConfig.provider || !chatModelConfig.model) return;

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
          provider: chatModelConfig.provider,
          model: chatModelConfig.model,
          config: chatModelConfig.parameters,
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

  const isChatReady = !loading && sessionId && chatModelConfig.provider && chatModelConfig.model;

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            AI Chat
          </Typography>
          <Chip
            label={`${chatModelConfig.provider}${chatModelConfig.model ? '/' + chatModelConfig.model : ''}`}
            color="primary"
            variant="outlined"
            sx={{ mr: 2 }}
          />
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

      {/* Model Configuration Dialog */}
      <ModelConfigDialog
        open={isModelConfigOpen}
        onClose={() => setIsModelConfigOpen(false)}
        title="Chat Model Configuration"
        initialConfig={chatModelConfig}
        onSave={handleModelConfigSave}
      />
    </Container>
  );
};

export default ChatPage;