// Updated local.js config with new theme
const localConfig = {
  env: 'local',
  app: {
    name: 'Gofannon',
  },
  api: {
    baseUrl: '', // same-origin; nginx proxies /auth/* etc. to api:8000
  },
  auth: {
    provider: 'session',
  },
  storage: {
    provider: 's3',
    s3: {
      bucket: 'local-bucket',
      region: 'us-east-1',
      endpoint: 'http://localhost:9000',
    },
  },
  theme: {
    palette: {
      mode: 'light',
      primary: { 
        main: '#18181b',
        light: '#3f3f46',
        dark: '#09090b',
        contrastText: '#ffffff',
      },
      secondary: { 
        main: '#71717a',
        light: '#a1a1aa',
        dark: '#52525b',
      },
      success: {
        main: '#16a34a',
        light: '#22c55e',
        dark: '#15803d',
      },
      error: {
        main: '#dc2626',
        light: '#ef4444',
        dark: '#b91c1c',
      },
      background: {
        default: '#f8f9fa',
        paper: '#ffffff',
      },
      text: {
        primary: '#18181b',
        secondary: '#71717a',
      },
      divider: '#e4e4e7',
    },
    typography: {
      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      h1: { fontWeight: 600 },
      h2: { fontWeight: 600 },
      h3: { fontWeight: 600 },
      h4: { fontWeight: 600 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 500 },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            boxShadow: 'none',
            '&:hover': {
              boxShadow: 'none',
            },
          },
          contained: {
            '&:hover': {
              boxShadow: 'none',
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            boxShadow: 'none',
            border: '1px solid #e4e4e7',
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            boxShadow: 'none',
            borderBottom: '1px solid #27272a',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            fontWeight: 500,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
            color: '#71717a',
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          },
        },
      },
    },
  },
};

export default localConfig;
