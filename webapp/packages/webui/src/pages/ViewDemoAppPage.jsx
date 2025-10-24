// webapp/packages/webui/src/pages/ViewDemoAppPage.jsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { CircularProgress, Box, Alert } from '@mui/material';
import demoService from '../services/demoService';
import config from '../config';

const ViewDemoAppPage = () => {
  const { demoId } = useParams();
  const [srcDoc, setSrcDoc] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAndBuildApp = async () => {
      setLoading(true);
      setError(null);
      try {
        const appData = await demoService.getDemo(demoId);
        const { html, css, js } = appData.generatedCode;
        const apiBaseUrl = config.api.baseUrl;

        const content = `
          <html>
            <head>
              <style>${css}</style>
            </head>
            <body>
              ${html}
              <script>
                const API_BASE_URL = "${apiBaseUrl}";
              </script>
              <script type="module">
                ${js}
              </script>
            </body>
          </html>
        `;
        setSrcDoc(content);
      } catch (err) {
        setError(err.message || 'Failed to load demo application.');
      } finally {
        setLoading(false);
      }
    };

    fetchAndBuildApp();
  }, [demoId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <iframe
      srcDoc={srcDoc}
      title="Demo App"
      sandbox="allow-scripts allow-forms allow-same-origin"
      style={{ width: '100%', height: '100vh', border: 'none' }}
    />
  );
};

export default ViewDemoAppPage;