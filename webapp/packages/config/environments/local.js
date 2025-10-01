const localConfig = {
  env: 'local',
  api: {
    baseUrl: 'http://localhost:8000',
  },
  auth: {
    provider: 'mock', // 'mock' for local, no real login
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
      primary: { main: '#1976d2' },
      secondary: { main: '#dc004e' },
    },
  },
};

export default localConfig;