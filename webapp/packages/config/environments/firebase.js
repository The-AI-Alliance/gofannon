export default firebaseConfig = {
  env: 'firebase',
  api: {
    baseUrl: 'https://us-central1-your-project-id.cloudfunctions.net/api',
  },
  auth: {
    provider: 'firebase',
    firebase: {
      apiKey: 'YOUR_API_KEY',
      authDomain: 'YOUR_PROJECT_ID.firebaseapp.com',
      // ... other firebase config
    },
    // Configurable social logins
    enabledSocialProviders: ['google', 'facebook'],
  },
  storage: {
    provider: 'gcs', // Google Cloud Storage
    gcs: {
      bucket: 'your-project-id.appspot.com',
    },
  },
  theme: {
    // Theme can be overridden here if needed
  },
};