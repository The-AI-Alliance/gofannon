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
  Paper,
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import FacebookIcon from '@mui/icons-material/Facebook';
import LockIcon from '@mui/icons-material/Lock';
import GitHubIcon from '@mui/icons-material/GitHub';
import BusinessIcon from '@mui/icons-material/Business';
import ScienceIcon from '@mui/icons-material/Science';
import { useAuth } from '../contexts/AuthContextValue';
import { useConfig } from '../contexts/ConfigContextValue';
import AnvilIcon from '../components/AnvilIcon';
import { fetchAuthProviders, sessionAuth } from '../services/authService';

// Legacy Firebase social providers shown when appConfig.auth.socialProviders
// is non-empty. Separate registry from the Phase B provider icons below so
// the two paths can co-exist during rollout.
const legacySocialProviderDetails = {
  google: {
    name: 'Google',
    icon: <GoogleIcon />,
  },
  facebook: {
    name: 'Facebook',
    icon: <FacebookIcon />,
  },
};

// Phase B provider icon picker. Keys match ``AuthProviderInfo.icon`` hints
// returned from the backend. Unknown icons fall back to a generic lock.
const providerIconFor = (iconHint) => {
  switch (iconHint) {
    case 'google':    return <GoogleIcon />;
    case 'github':    return <GitHubIcon />;
    case 'microsoft': return <BusinessIcon />;
    case 'dev':       return <ScienceIcon />;
    case 'asf':
    default:          return <LockIcon />;
  }
};

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // Phase B providers fetched from the backend. null = not loaded yet;
  // [] = loaded, Phase B disabled; array = Phase B providers to render.
  const [phaseBProviders, setPhaseBProviders] = useState(null);
  const [legacyFirebaseEnabled, setLegacyFirebaseEnabled] = useState(true);
  const [providersLoading, setProvidersLoading] = useState(true);
  // Trigger for the "redirecting…" spinner when a Phase B button is clicked.
  const [redirecting, setRedirecting] = useState(false);
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
  const legacySocialProviders = config.auth.socialProviders || [];

  // Load Phase B providers on mount. Endpoint is unauthenticated.
  // Failure is benign — just means Phase B isn't deployed, and
  // LoginPage falls back to the legacy rendering path.
  useEffect(() => {
    let cancelled = false;
    fetchAuthProviders()
      .then((resp) => {
        if (cancelled) return;
        if (resp && Array.isArray(resp.providers)) {
          setPhaseBProviders(resp.providers);
          setLegacyFirebaseEnabled(!!resp.legacyFirebaseEnabled);
        } else {
          setPhaseBProviders([]);
        }
      })
      .finally(() => { if (!cancelled) setProvidersLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (user) {
      navigate('/');
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

  // Phase B provider click → redirects the whole window via sessionAuth.
  // No need to swap authService; the callback cookie sets identity and
  // the next page load picks it up automatically.
  const handlePhaseBProvider = async (providerType) => {
    setRedirecting(true);
    try {
      await sessionAuth.loginWithProvider(providerType);
      // loginWithProvider navigates the window away; the promise
      // never resolves. If it somehow does (e.g. network error),
      // we unset redirecting so the buttons re-enable.
    } finally {
      setRedirecting(false);
    }
  };

  // --- Legacy render paths (unchanged from pre-B-2) ---------------------

  const renderMockLogin = () => (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
        Local development mode - authentication disabled
      </Typography>
      <Button
        variant="contained"
        onClick={handleMockLogin}
        disabled={loading}
        fullWidth
        size="large"
        sx={{
          bgcolor: '#18181b',
          '&:hover': { bgcolor: '#27272a' },
          py: 1.5
        }}
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Enter App'}
      </Button>
    </>
  );

  const renderFirebaseLogin = () => (
    <>
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
          sx={{
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused fieldset': { borderColor: '#18181b' },
            },
            '& .MuiInputLabel-root.Mui-focused': { color: '#18181b' },
          }}
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
          sx={{
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused fieldset': { borderColor: '#18181b' },
            },
            '& .MuiInputLabel-root.Mui-focused': { color: '#18181b' },
          }}
        />
        <Button
          type="submit"
          fullWidth
          variant="contained"
          sx={{ 
            mt: 3, 
            mb: 2,
            bgcolor: '#18181b',
            '&:hover': { bgcolor: '#27272a' },
            py: 1.5
          }}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In'}
        </Button>
      </Box>

      {legacySocialProviders.length > 0 && (
        <>
          <Divider sx={{ my: 2 }}>
            <Typography variant="caption" color="text.secondary">or continue with</Typography>
          </Divider>
          <Stack spacing={2}>
            {legacySocialProviders.map((providerId) => {
              const details = legacySocialProviderDetails[providerId];
              if (!details) return null;
              return (
                <Button
                  key={providerId}
                  fullWidth
                  variant="outlined"
                  startIcon={details.icon}
                  onClick={() => handleProviderLogin(providerId)}
                  disabled={loading}
                  sx={{ 
                    justifyContent: 'center',
                    borderColor: '#e4e4e7',
                    color: '#18181b',
                    '&:hover': { 
                      borderColor: '#a1a1aa',
                      bgcolor: '#fafafa'
                    }
                  }}
                >
                  {details.name}
                </Button>
              );
            })}
          </Stack>
        </>
      )}
    </>
  );

  // --- Phase B render ---------------------------------------------------

  const renderPhaseBProviders = () => (
    <Stack spacing={2} sx={{ mt: 1 }}>
      {phaseBProviders.map((p) => (
        <Button
          key={p.type}
          fullWidth
          variant="contained"
          startIcon={providerIconFor(p.icon)}
          onClick={() => handlePhaseBProvider(p.type)}
          disabled={redirecting}
          size="large"
          sx={{
            justifyContent: 'center',
            bgcolor: '#18181b',
            '&:hover': { bgcolor: '#27272a' },
            py: 1.5,
          }}
        >
          {redirecting ? <CircularProgress size={20} color="inherit" /> : `Sign in with ${p.displayName}`}
        </Button>
      ))}
    </Stack>
  );

  // --- Top-level layout chooser ----------------------------------------

  let body;
  if (providersLoading) {
    body = (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  } else if (phaseBProviders && phaseBProviders.length > 0) {
    // Phase B is on. Render provider buttons. If the operator chose to
    // keep Firebase enabled for rollover (legacyFirebaseEnabled), we
    // *also* render the Firebase UI below.
    body = (
      <>
        {renderPhaseBProviders()}
        {legacyFirebaseEnabled && authProviderType !== 'mock' && authProviderType !== 'session' && (
          <>
            <Divider sx={{ my: 3 }}>
              <Typography variant="caption" color="text.secondary">or use legacy sign-in</Typography>
            </Divider>
            {renderFirebaseLogin()}
          </>
        )}
      </>
    );
  } else if (authProviderType === 'mock') {
    body = renderMockLogin();
  } else {
    body = renderFirebaseLogin();
  }

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      bgcolor: '#f8f9fa', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center' 
    }}>
      <Container component="main" maxWidth="xs">
        <Paper
          elevation={0}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            border: '1px solid #e4e4e7',
            borderRadius: 2,
          }}
        >
          {/* Logo */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1.5, 
            mb: 4 
          }}>
            <AnvilIcon size={36} color="#18181b" />
            <Typography 
              variant="h5" 
              sx={{ 
                fontWeight: 600, 
                letterSpacing: '-0.5px',
                color: '#18181b'
              }}
            >
              Gofannon
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          {body}
        </Paper>
        
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 3 }}>
          AI Agent Development Platform
        </Typography>
      </Container>
    </Box>
  );
};

export default LoginPage;
