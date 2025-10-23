import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Divider,
  Stack,
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import FacebookIcon from '@mui/icons-material/Facebook';

// Custom hooks to abstract away the context consumers
import { useAuth } from '../contexts/AuthContext';
import { useConfig } from '../contexts/ConfigContext';

// A helper to map provider IDs to their respective icons and names
const socialProviderDetails = {
  google: {
    name: 'Google',
    icon: <GoogleIcon />,
  },
  facebook: {
    name: 'Facebook',
    icon: <FacebookIcon />,
  },
  // ... add other providers like 'github', 'twitter' as needed
};

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const {
    loginWithEmail,
    loginWithProvider,
    loginAsMockUser,
    error,
    loading,
    user,
  } = useAuth();

  const { config } = useConfig();
  const authProviderType = config.auth.provider;
  const enabledSocialProviders = config.auth.socialProviders || [];

  // Effect to redirect the user if they are already logged in
  useEffect(() => {
    if (user) {
      navigate('/'); // Redirect to the main app page
    }
  }, [user, navigate]);

  const handleEmailLogin = async (event) => {
    event.preventDefault();
    await loginWithEmail(email, password);
  };

  const handleProviderLogin = async (providerId) => {
    await loginWithProvider(providerId);
  };

  const handleMockLogin = async () => {
    await loginAsMockUser();
  };

  /**
   * Renders the login UI for local/mock development.
   */
  const renderMockLogin = () => (
    <>
      <Typography variant="h6" component="h2" gutterBottom>
        Local Development Mode
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Authentication is disabled. Click below to proceed as a mock user.
      </Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={handleMockLogin}
        disabled={loading}
        fullWidth
        size="large"
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Enter App'}
      </Button>
    </>
  );

  /**
   * Renders the standard login UI for providers like Firebase or Amplify.
   */
  const renderStandardLogin = () => (
    <>
      <Typography variant="h4" component="h1" gutterBottom>
        Login
      </Typography>
      <Box component="form" onSubmit={handleEmailLogin} noValidate sx={{ mt: 1 }}>
        <TextField
          margin="normal"
          required
          fullWidth
          id="email"
          label="Email Address"
          name="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          name="password"
          label="Password"
          type="password"
          id="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
        />
        <Button
          type="submit"
          fullWidth
          variant="contained"
          sx={{ mt: 3, mb: 2 }}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In'}
        </Button>
      </Box>

      {enabledSocialProviders.length > 0 && (
        <>
          <Divider sx={{ my: 2 }}>OR</Divider>
          <Stack spacing={2}>
            {enabledSocialProviders.map((providerId) => {
              const details = socialProviderDetails[providerId];
              if (!details) {
                console.warn(`Social provider "${providerId}" is not configured in LoginPage.jsx`);
                return null;
              }
              return (
                <Button
                  key={providerId}
                  fullWidth
                  variant="outlined"
                  startIcon={details.icon}
                  onClick={() => handleProviderLogin(providerId)}
                  disabled={loading}
                  sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                >
                  Sign in with {details.name}
                </Button>
              );
            })}
          </Stack>
        </>
      )}
    </>
  );

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: 3,
          boxShadow: 3,
          borderRadius: 2,
          bgcolor: 'background.paper',
        }}
      >
        {error && (
          <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
            {error}
          </Alert>
        )}

        {authProviderType === 'mock' ? renderMockLogin() : renderStandardLogin()}
      </Box>
    </Container>
  );
};

export default LoginPage;