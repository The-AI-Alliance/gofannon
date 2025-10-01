import React, { createContext, useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import authService from '../services/authService';

export const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    const currentUser = authService.getCurrentUser();
    setUser(currentUser);
    setLoading(false);
  }, []);

  const handleLogin = async (loginFn, ...args) => {
    setLoading(true);
    setError(null);
    try {
      const loggedInUser = await loginFn(...args);
      setUser(loggedInUser);
      return loggedInUser;
    } catch (e) {
      console.error("Login failed:", e);
      setError(e.message || 'Login failed. Please check your credentials.');
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
    loginAsMockUser 
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

AuthProvider.propTypes = {
    children: PropTypes.node.isRequired,
};