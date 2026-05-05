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


// --- Phase B: server-side session auth ----------------------------------
//
// When the backend exposes /auth/providers (Phase B enabled), the frontend
// uses this implementation instead of talking directly to Firebase.
//
// Identity lives in an HttpOnly ``gofannon_sid`` cookie set by the backend
// on OAuth callback. The frontend can't read the cookie (that's the point);
// it observes the session by GETting /auth/me, which returns the user info
// or 401.
//
// ``getIdToken`` exists to match Firebase's contract — existing service code
// calls ``user.getIdToken()`` to build Authorization headers. In session
// mode there's no bearer token (the cookie authenticates automatically),
// so ``getIdToken`` resolves to null. The service helpers in agentService /
// apiClient already gracefully skip the Authorization header when the
// token is falsy. Separately, those fetchers need ``credentials: 'include'``
// to ensure the cookie is sent on same-origin and properly-CORSed
// cross-origin requests; we don't change them here (ships with B-1), but
// the backend CORS config already allows credentials.

const sessionAuth = {
  // Cache of the most recent /auth/me response. Mirrors Firebase's
  // behavior of giving callers something synchronous via getCurrentUser().
  _currentUser: null,
  _listeners: new Set(),

  _emit() {
    for (const cb of this._listeners) {
      try { cb(this._currentUser); } catch (e) { console.error(e); }
    }
  },

  _buildUser(me) {
    // me shape: {uid, displayName, email, providerType, workspaces, isSiteAdmin}
    // Returned object mimics the Firebase user shape so existing code
    // that reads user.uid / user.email / user.displayName /
    // user.getIdToken() keeps working.
    return {
      uid: me.uid,
      email: me.email,
      displayName: me.displayName,
      providerType: me.providerType,
      workspaces: me.workspaces || [],
      isSiteAdmin: !!me.isSiteAdmin,
      // No bearer token in session mode — the cookie handles it.
      // Resolving to null makes the existing getIdToken-or-skip logic
      // in agentService / apiClient / dataStoreService cleanly fall
      // through to "no Authorization header."
      getIdToken: async () => null,
    };
  },

  async _fetchMe() {
    // GET /auth/me with credentials so the cookie is sent.
    const base = appConfig.api.baseUrl;
    try {
      const resp = await fetch(`${base}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (resp.status === 401) {
        this._currentUser = null;
        return null;
      }
      if (!resp.ok) {
        console.warn('[sessionAuth] /auth/me returned', resp.status);
        this._currentUser = null;
        return null;
      }
      const me = await resp.json();
      this._currentUser = this._buildUser(me);
      return this._currentUser;
    } catch (e) {
      console.error('[sessionAuth] /auth/me failed:', e);
      this._currentUser = null;
      return null;
    }
  },

  async login() {
    // Email/password login is not supported in session mode; callers
    // should never hit this path because LoginPage renders provider
    // buttons instead of the email form. Throwing makes misuse obvious.
    throw new Error('Email/password login is not supported with session auth. Use a provider.');
  },

  async loginWithProvider(providerType) {
    // Redirect the whole window to the provider flow. The callback
    // sets the session cookie and bounces back to ``return_to``.
    const base = appConfig.api.baseUrl;
    // Preserve where the user was trying to go pre-login.
    const returnTo = typeof window !== 'undefined'
      ? (window.location.pathname + window.location.search)
      : '/';
    const url = `${base}/auth/login/${encodeURIComponent(providerType)}?return_to=${encodeURIComponent(returnTo)}`;
    window.location.href = url;
    // Never resolves — the browser has left the page.
    return new Promise(() => {});
  },

  async logout() {
    const base = appConfig.api.baseUrl;
    try {
      await fetch(`${base}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      console.warn('[sessionAuth] logout POST failed:', e);
    }
    this._currentUser = null;
    this._emit();
    // Best-effort: also wipe any Firebase state if it was previously used.
    try {
      const fb = getAuth();
      if (fb?.currentUser) await signOut(fb);
    } catch { /* firebase not initialized; fine */ }
  },

  getCurrentUser() {
    return this._currentUser;
  },

  onAuthStateChanged(callback) {
    this._listeners.add(callback);
    // Unlike Firebase's onAuthStateChanged, we don't have a cached
    // user available synchronously on first mount — we have to ask
    // the backend whether the session cookie is valid via /auth/me.
    //
    // Firing callback(null) here unconditionally caused a real bug:
    // AuthContext saw user=null,loading=false on first paint, so
    // PrivateRoute bounced to /login. By the time /auth/me resolved
    // and we emitted the real user, LoginPage was already mounted
    // and its 'if (user) navigate(/)' effect sent them to home —
    // which is why refreshing /agent/<id> always landed on /.
    //
    // Only fire synchronously if we already have a resolved user
    // (covers later listener subscriptions after the first fetch).
    // Otherwise, kick off _fetchMe and let _emit() send the real
    // value when it lands. AuthContext keeps loading=true until then.
    if (this._currentUser !== null) {
      callback(this._currentUser);
    }
    this._fetchMe().then(() => this._emit());
    return () => { this._listeners.delete(callback); };
  },

  // Phase B-specific helper: re-query the provider for updated
  // workspace memberships and returns the diff. The AuthContext
  // wires this up for the user-menu "Refresh workspaces" button.
  async refreshWorkspaces() {
    const base = appConfig.api.baseUrl;
    const resp = await fetch(`${base}/auth/refresh-workspaces`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (!resp.ok) {
      throw new Error(`Refresh failed: ${resp.status}`);
    }
    const diff = await resp.json();
    // Update cached user with the new workspace list.
    await this._fetchMe();
    this._emit();
    return diff;
  },
};


// --- Provider-mode discovery ---------------------------------------------
//
// On startup the frontend asks /auth/providers whether Phase B is on.
// Returns the raw response or null on any error. Consumed by
// LoginPage (to render buttons) and by the authService exporter below
// (to pick sessionAuth when Phase B is active).

export async function fetchAuthProviders() {
  const base = appConfig.api.baseUrl;
  try {
    const resp = await fetch(`${base}/auth/providers`, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (!resp.ok) return null;
    return await resp.json(); // {providers: [...], legacyFirebaseEnabled: bool}
  } catch (e) {
    console.warn('[authService] /auth/providers unreachable:', e);
    return null;
  }
}


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
  login: async () => {
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
//
// Mode selection:
//
// 1. Session auth if the operator has explicitly opted in via
//    ``appConfig.auth.provider === 'session'``. (Set in config when
//    rolling out Phase B so we don't need a network round-trip at
//    module-load time to pick a mode.)
// 2. Firebase if ``appConfig.auth.provider === 'firebase'``.
// 3. Cognito if ``appConfig.auth.provider === 'cognito'``.
// 4. Mock otherwise (local dev).
//
// LoginPage separately calls ``fetchAuthProviders()`` at render time so
// it can show the right buttons regardless of which mode the service
// selected — i.e. during the migration window where both Firebase and
// Phase B are available, the service stays on Firebase but LoginPage
// still surfaces the provider buttons.

let authService;
switch (appConfig.auth.provider) {
  case 'session':
    authService = sessionAuth;
    break;
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

// Named export: the session implementation, so LoginPage and ProfileMenu
// can use provider-specific helpers (loginWithProvider with a backend
// type, refreshWorkspaces) without importing the raw module internals.
export { sessionAuth };