import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import authService from '../services/authService';
import observabilityService from '../services/observabilityService';
import { AuthContext } from './AuthContextValue';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // If the auth service supports onAuthStateChanged (like Firebase), use it.
    if (typeof authService.onAuthStateChanged === 'function') {
      const unsubscribe = authService.onAuthStateChanged((user) => {
        setUser(user);
        setLoading(false);
      });
      return () => unsubscribe(); // Cleanup subscription on unmount
    } else {
      // Fallback for mock or simpler auth services
      const currentUser = authService.getCurrentUser();
      setUser(currentUser);
      setLoading(false);
    }       
  }, []);

  const handleLogin = async (loginFn, ...args) => {
    setLoading(true);
    setError(null);
    try {
      const loggedInUser = await loginFn(...args);
      setUser(loggedInUser);
      observabilityService.log({ 
        eventType: 'user-action', 
        message: 'User logged in successfully.', 
        metadata: { email: loggedInUser?.email } 
      });
      return loggedInUser;
    } catch (e) {
      console.error("Login failed:", e);
      setError(e.message || 'Login failed. Please check your credentials.');
      
      // Attempt to extract email from args safely
      const loginArgs = args[0] || {};
      const emailAttempt = loginArgs.email || (typeof loginArgs === 'string' ? loginArgs : 'unknown');

      observabilityService.log({ 
        eventType: 'user-action', 
        message: 'User login failed.', 
        level: 'WARN', 
        metadata: { email: emailAttempt, error: e.message } 
      });
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const loginWithEmail = (email, password) => {
    return handleLogin(authService.login, { email, password });
  };
  
  const loginWithProvider = (providerId) => {
    return handleLogin(authService.loginWithProvider, providerId);
  };
  
  const loginAsMockUser = () => {
    return handleLogin(authService.login);
  };

  const logout = async () => {
    setLoading(true);
    try {
        await authService.logout();
        setUser(null);
    } catch (e) {
        console.error("Logout failed:", e);
        setError("Logout failed. Please try again.");
    } finally {
        setLoading(false);
    }
  };

  const value = { 
    user, 
    loading, 
    error,
    logout,
    loginWithEmail,
    loginWithProvider,
    loginAsMockUser,
    // Phase B: refresh workspace memberships from the provider. When
    // the active authService doesn't support this (Firebase / mock),
    // the function throws — callers should only render the trigger
    // (e.g. user-menu item) when in session mode.
    refreshWorkspaces: async () => {
      if (typeof authService.refreshWorkspaces !== 'function') {
        throw new Error('Workspace refresh is only available with session auth.');
      }
      const diff = await authService.refreshWorkspaces();
      // Update the user object so UI elements bound to
      // user.workspaces re-render with the new list.
      setUser(authService.getCurrentUser());
      return diff;
    },
    // Whether the current auth mode supports Phase B session features
    // like workspace refresh, workspace switcher, etc. Passed through
    // so components (ProfileMenu) can conditionally render those UI
    // bits without poking at module internals.
    isSessionAuth: typeof authService.refreshWorkspaces === 'function',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

AuthProvider.propTypes = {
    children: PropTypes.node.isRequired,
};