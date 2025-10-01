import appConfig from '../config';

// --- MOCK Implementation (for local development) ---
const mockAuth = {
  login: async (credentials) => {
    console.log('Mock login with:', credentials);
    const mockUser = { uid: 'mock-user-123', email: credentials?.email || 'dev@gofannon.com' };
    localStorage.setItem('user', JSON.stringify(mockUser));
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network delay
    return mockUser;
  },
  loginWithProvider: async (providerId) => {
    console.log(`Mock login with provider: ${providerId}`);
    const mockUser = { uid: `mock-${providerId}-user`, email: `${providerId}-dev@gofannon.com` };
    localStorage.setItem('user', JSON.stringify(mockUser));
    await new Promise(resolve => setTimeout(resolve, 500));
    return mockUser;
  },
  logout: async () => {
    console.log('Mock logout');
    localStorage.removeItem('user');
  },
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    try {
        return userStr ? JSON.parse(userStr) : null;
    } catch (e) {
        console.error("Failed to parse user from localStorage", e);
        localStorage.removeItem('user');
        return null;
    }
  },
};

// --- Firebase Implementation (Placeholder) ---
const firebaseAuth = {
  // You would import firebase and implement these methods
  login: async ({ email, password }) => {
    // await signInWithEmailAndPassword(auth, email, password); ...
    throw new Error('Firebase Auth not implemented');
  },
  logout: async () => {
    // await signOut(auth); ...
    throw new Error('Firebase Auth not implemented');
  },
  getCurrentUser: () => {
    // return auth.currentUser;
    throw new Error('Firebase Auth not implemented');
  },
};

// --- Amplify/Cognito Implementation (Placeholder) ---
const cognitoAuth = {
  // You would import Amplify and implement these methods
  login: async ({ username, password }) => {
    // await Auth.signIn(username, password); ...
    throw new Error('Cognito Auth not implemented');
  },
  logout: async () => {
    // await Auth.signOut();
    throw new Error('Cognito Auth not implemented');
  },
  getCurrentUser: () => {
    // return Auth.currentAuthenticatedUser();
    throw new Error('Cognito Auth not implemented');
  },
};

// --- Service Exporter ---
let authService;
switch (appConfig.auth.provider) {
  case 'firebase':
    authService = firebaseAuth;
    break;
  case 'cognito':
    authService = cognitoAuth;
    break;
  case 'mock':
  default:
    authService = mockAuth;
}

export default authService;