// webapp/packages/webui/src/pages/DemoCreationFlow/DemoApiSelectionDialog.jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControlLabel,
  Checkbox,
  FormGroup,
  CircularProgress,
  Typography,
  Alert,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import ApiIcon from '@mui/icons-material/Api';
import agentService from '../../services/agentService'; // Import agentService

const DemoApiSelectionDialog = ({
  open,
  onClose,
  existingSelectedApis, // Array of full API deployment objects
  onSaveSelectedApis,  // Callback to save the updated array of API deployment objects
}) => {
  const [availableApis, setAvailableApis] = useState([]); // All tools fetched from the backend
  const [currentSelectedApis, setCurrentSelectedApis] = useState([]); // API deployment objects currently checked in the dialog
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      // Initialize with existing selections (deep copy to avoid direct mutation)
      setCurrentSelectedApis(JSON.parse(JSON.stringify(existingSelectedApis)));
      
      agentService.getDeployments()
        .then(apis => {
          setAvailableApis(apis);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message || 'Failed to fetch available APIs.');
          setLoading(false);
          setAvailableApis([]); // Clear tools on error
        });
    } else {
      // Reset state when dialog closes
      setAvailableApis([]);
      setCurrentSelectedApis([]);
      setError(null);
    }
  }, [open, existingSelectedApis]); // Re-run effect when these props change

  const handleToggle = (apiToToggle) => {
    setCurrentSelectedApis(prev => {
      const currentIndex = prev.findIndex(item => item.agentId === apiToToggle.agentId);
      const newSelected = [...prev];

      if (currentIndex === -1) {
        newSelected.push(apiToToggle);
      } else {
        newSelected.splice(currentIndex, 1);
      }
      return newSelected;
    });
  };

  const handleSave = () => {
    onSaveSelectedApis(currentSelectedApis);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Select APIs for Demo App</DialogTitle>
      <DialogContent>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
            <CircularProgress />
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ my: 2 }}>
            {error}
          </Alert>
        )}
        {!loading && !error && availableApis.length === 0 && (
          <Typography sx={{ my: 2 }}>No deployed APIs found.</Typography>
        )}
        {!loading && !error && availableApis.length > 0 && (
          <List sx={{ width: '100%', bgcolor: 'background.paper', maxHeight: '50vh', overflow: 'auto' }}>
            {availableApis.map((api) => {
              const isSelected = currentSelectedApis.some(item => item.agentId === api.agentId);
              return (
                <ListItem
                  key={api.agentId}
                  secondaryAction={
                    <Checkbox edge="end" onChange={() => handleToggle(api)} checked={isSelected} />
                  }
                  disablePadding
                  button
                  onClick={() => handleToggle(api)}
                >
                  <ListItemIcon>
                      <ApiIcon />
                  </ListItemIcon>
                  <ListItemText primary={api.friendlyName} secondary={api.description || "No description"} />
                </ListItem>
              );
            })}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={loading}>
          Save Selected APIs
        </Button>
      </DialogActions>
    </Dialog>
  );
};

DemoApiSelectionDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  existingSelectedApis: PropTypes.arrayOf(PropTypes.object).isRequired, // Expects array of API objects
  onSaveSelectedApis: PropTypes.func.isRequired,
};

export default DemoApiSelectionDialog;
