// webapp/packages/webui/src/pages/DemoAppsPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  ListItemIcon,
  Divider,
  Container,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack
} from '@mui/material';
import WebIcon from '@mui/icons-material/Web';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import demoService from '../services/demoService';

const DemoAppsPage = () => {
  const navigate = useNavigate();
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState({ open: false, appId: null, appName: '' });

  useEffect(() => {
    const fetchApps = async () => {
      try {
        setLoading(true);
        setError(null);
        const savedApps = await demoService.getDemos();
        setApps(savedApps);
      } catch (err) {
        setError('Failed to load saved demo apps.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchApps();
  }, []);

  const handleEdit = (appId, event) => {
    event.stopPropagation();
    navigate(`/create-demo/canvas?edit=${appId}`);
  };
  
  const handleDeleteClick = (appId, appName, event) => {
    event.stopPropagation();
    setDeleteConfirmation({ open: true, appId, appName });
  };

  const handleConfirmDelete = async () => {
    const { appId } = deleteConfirmation;
    try {
      await demoService.deleteDemo(appId);
      setApps(prev => prev.filter(app => app._id !== appId));
    } catch (err) {
      setError(`Failed to delete app: ${err.message}`);
    } finally {
      setDeleteConfirmation({ open: false, appId: null, appName: '' });
    }
  };
  
  const handleViewApp = (appId) => {
    window.open(`/demos/${appId}`, '_blank');
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Demo Apps
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/create-demo')}
        >
          Create New Demo App
        </Button>
      </Box>
      
      <Paper sx={{ p: 3 }}>
        {loading && <Box sx={{ display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>}
        {error && <Alert severity="error">{error}</Alert>}
        {!loading && !error && (
          <List>
            {apps.length === 0 ? (
              <Typography color="text.secondary" textAlign="center">
                You haven't created any demo apps yet.
              </Typography>
            ) : (
              apps.map((app, index) => (
                <React.Fragment key={app._id}>
                  <ListItem
                    secondaryAction={
                      <Stack direction="row" spacing={1}>
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={() => handleViewApp(app._id)}
                        >
                            View
                        </Button>
                        <IconButton edge="end" aria-label="edit" onClick={(e) => handleEdit(app._id, e)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton edge="end" aria-label="delete" onClick={(e) => handleDeleteClick(app._id, app.name, e)}>
                          <DeleteIcon />
                        </IconButton>
                      </Stack>
                    }
                  >
                    <ListItemIcon><WebIcon /></ListItemIcon>
                    <ListItemText primary={app.name} secondary={app.description || "No description"} />
                  </ListItem>
                  {index < apps.length - 1 && <Divider />}
                </React.Fragment>
              ))
            )}
          </List>
        )}
      </Paper>
      
      <Dialog open={deleteConfirmation.open} onClose={() => setDeleteConfirmation({ open: false, appId: null, appName: '' })}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to permanently delete the app "{deleteConfirmation.appName}"?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmation({ open: false, appId: null, appName: '' })}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>      
    </Container>
  );
};

export default DemoAppsPage;