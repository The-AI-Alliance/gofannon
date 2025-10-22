import React from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Paper, Button } from '@mui/material';
import observabilityService from '../services/observabilityService';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to your observability service
    observabilityService.logError(error, {
      componentStack: errorInfo.componentStack,
      location: window.location.href,
    });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <Box sx={{ p: 4, m: 'auto', maxWidth: 600 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h5" color="error" gutterBottom>
              Something went wrong.
            </Typography>
            <Typography variant="body1" color="text.secondary">
              An unexpected error occurred. We have been notified and are looking into it.
            </Typography>
            <Button
              variant="contained"
              sx={{ mt: 3 }}
              onClick={() => window.location.reload()}
            >
              Reload Page
            </Button>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
};

export default ErrorBoundary;