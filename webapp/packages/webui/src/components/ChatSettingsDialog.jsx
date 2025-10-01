// webapp/packages/webui/src/components/ChatSettingsDialog.jsx
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Typography,
  Box,
} from '@mui/material';

const ChatSettingsDialog = ({ open, onClose, settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(localSettings);
  };

  const handleReset = () => {
    setLocalSettings(settings);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Chat Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Model</InputLabel>
            <Select
              value={localSettings.model}
              label="Model"
              onChange={(e) => handleChange('model', e.target.value)}
            >
              <MenuItem value="llama2">Llama 2</MenuItem>
              <MenuItem value="mistral">Mistral</MenuItem>
              <MenuItem value="codellama">Code Llama</MenuItem>
              <MenuItem value="gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
            </Select>
          </FormControl>

          <Box>
            <Typography gutterBottom>
              Temperature: {localSettings.temperature}
            </Typography>
            <Slider
              value={localSettings.temperature}
              onChange={(e, value) => handleChange('temperature', value)}
              min={0}
              max={2}
              step={0.1}
              marks
              valueLabelDisplay="auto"
            />
            <Typography variant="caption" color="text.secondary">
              Controls randomness: 0 = focused, 2 = creative
            </Typography>
          </Box>

          <TextField
            label="Max Tokens"
            type="number"
            value={localSettings.maxTokens}
            onChange={(e) => handleChange('maxTokens', parseInt(e.target.value))}
            inputProps={{ min: 100, max: 4000 }}
            helperText="Maximum length of the response"
          />

          <TextField
            label="System Prompt"
            multiline
            rows={4}
            value={localSettings.systemPrompt}
            onChange={(e) => handleChange('systemPrompt', e.target.value)}
            helperText="Instructions for the AI's behavior"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleReset}>Reset</Button>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ChatSettingsDialog;