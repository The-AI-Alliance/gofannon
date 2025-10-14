export default firebaseConfig = {
  env: 'firebase',
  api: {
    baseUrl: 'https://us-central1-your-project-id.cloudfunctions.net/api',
  },
  auth: {
    provider: 'firebase',
    firebase: {
      apiKey: process.env.VITE_FIREBASE_API_KEY,
      authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: process.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: process.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: process.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: process.env.VITE_FIREBASE_APP_ID,
    },
    // Configurable social logins
    enabledSocialProviders: ['google'],
  },
  storage: {
    provider: 'gcs', // Google Cloud Storage
    gcs: {
      bucket: 'your-project-id.appspot.com',
    },
  },
  // theme: {
  //   palette: {
  //     primary: { main: '#FFA000' }, // Firebase-like orange
  //     // secondary: { main: '#039BE5' }, // Firebase-like blue
  //   },
  // },
};