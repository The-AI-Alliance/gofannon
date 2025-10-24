// webapp/packages/webui/src/pages/DemoCreationFlow/SelectApisScreen.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDemoFlow } from './DemoCreationFlowContext';
import agentService from '../../services/agentService';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  ListItemIcon,
} from '@mui/material';
import ApiIcon from '@mui/icons-material/Api';

const SelectApisScreen = () => {
  const { selectedApis, setSelectedApis } = useDemoFlow();
  const [availableApis, setAvailableApis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchApis = async () => {
      setLoading(true);
      setError(null);
      try {
        const apis = await agentService.getDeployments();
        setAvailableApis(apis);
      } catch (err) {
        setError(err.message || "Failed to load available APIs.");
      } finally {
        setLoading(false);
      }
    };
    fetchApis();
  }, []);

  const handleToggle = (api) => {
    const currentIndex = selectedApis.findIndex(item => item.friendlyName === api.friendlyName);
    const newSelected = [...selectedApis];

    if (currentIndex === -1) {
      newSelected.push(api);
    } else {
      newSelected.splice(currentIndex, 1);
    }
    setSelectedApis(newSelected);
  };

  const handleContinue = () => {
    if (selectedApis.length === 0) {
      setError("Please select at least one API to continue.");
      return;
    }
    navigate('/create-demo/select-model');
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 700, margin: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Step 1: Select APIs for Your Demo
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Choose which deployed agents (APIs) your new web application will be able to call.
      </Typography>

      {loading && <CircularProgress />}
      {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
      
      {!loading && (
        <List sx={{ width: '100%', bgcolor: 'background.paper', maxHeight: '50vh', overflow: 'auto' }}>
          {availableApis.map((api) => {
            const labelId = `checkbox-list-label-${api.friendlyName}`;
            const isSelected = selectedApis.some(item => item.friendlyName === api.friendlyName);
            return (
              <ListItem
                key={api.friendlyName}
                secondaryAction={<Checkbox edge="end" onChange={() => handleToggle(api)} checked={isSelected} />}
                disablePadding
                button
                onClick={() => handleToggle(api)}
              >
                <ListItemIcon>
                    <ApiIcon />
                </ListItemIcon>
                <ListItemText id={labelId} primary={api.friendlyName} secondary={api.description} />
              </ListItem>
            );
          })}
        </List>
      )}

      <Button
        variant="contained"
        onClick={handleContinue}
        disabled={loading || selectedApis.length === 0}
        fullWidth
        sx={{ mt: 3 }}
      >
        Continue
      </Button>
    </Paper>
  );
};

export default SelectApisScreen;