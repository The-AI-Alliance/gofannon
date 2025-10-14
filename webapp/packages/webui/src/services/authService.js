import appConfig from '../config';
import { initializeApp } from 'firebase/app';
import {
    getAuth,
    signInWithEmailAndPassword,
    signInWithPopup,
    GoogleAuthProvider,
    onAuthStateChanged,
    signOut,

} from 'firebase/auth';

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


const firebaseAuth = {
  _app: null,
  _auth: null,

  _initialize() {
    if (!this._app) {
      this._app = initializeApp(appConfig.auth.firebase);
      this._auth = getAuth(this._app);
    }
    return this._auth;
  },

  async login({ email, password }) {
    const auth = firebaseAuth._initialize();
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
   },

  async loginWithProvider(providerId) {
    const auth = firebaseAuth._initialize();
    let provider;
    if (providerId === 'google') {
      provider = new GoogleAuthProvider();
    } else {
      throw new Error(`Provider ${providerId} not supported.`);
    }
    const result = await signInWithPopup(auth, provider);
    return result.user;
  },

  async logout() {
    const auth = firebaseAuth._initialize();
    await signOut(auth);
  },

  getCurrentUser() {
    const auth = firebaseAuth._initialize();
    return auth.currentUser;
  },
  
  // New method to handle auth state changes
  onAuthStateChanged(callback) {
    const auth = firebaseAuth._initialize();
    return onAuthStateChanged(auth, (user) => {
      if (user) {
        // User is signed in. We can extract the necessary info.
        callback({
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          getIdToken: () => user.getIdToken(),
        });
      } else {
        // User is signed out.
        callback(null);
      }
    });    
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