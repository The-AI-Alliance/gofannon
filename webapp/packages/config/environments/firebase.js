const firebaseConfig = {
  env: 'firebase',
  api: {
    baseUrl: `https://us-central1-${import.meta.env.VITE_FIREBASE_PROJECT_ID}.cloudfunctions.net/api`,
  },
  auth: {
    provider: 'firebase',
    firebase: {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    },
    // Configurable social logins
    enabledSocialProviders: ['google'],
  },
  storage: {
    provider: 'gcs', // Google Cloud Storage
    gcs: {
      bucket: `${import.meta.env.VITE_FIREBASE_STORAGE_BUCKET}`,
    },
  },
  theme: {
    palette: {
      primary: { main: '#FFA000' }, // Firebase-like orange
      secondary: { main: '#039BE5' }, // Firebase-like blue
    },
  },
};
export default firebaseConfig;
