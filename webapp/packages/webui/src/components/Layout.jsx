import React from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  CssBaseline,
  Button,
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import config from '../config';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const appName = config?.app?.name || 'Gofannon WebApp';

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, cursor: 'pointer' }} onClick={() => navigate('/')}>
            {appName}
          </Typography>
          +          <Button 
            color="inherit" 
            startIcon={<SmartToyIcon />}
            onClick={() => navigate('/agents')}
            sx={{ mr: 1 }}
          >
            Agents
          </Button>
          <Button 
            color="inherit" 
            startIcon={<ChatIcon />}
            onClick={() => navigate('/chat')}
          >
            Chat
          </Button>
        </Toolbar>
      </AppBar>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
        }}
      >
        <Toolbar />
        <Container maxWidth="lg">
          {children}
        </Container>
      </Box>
    </Box>
  );
};

Layout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default Layout;