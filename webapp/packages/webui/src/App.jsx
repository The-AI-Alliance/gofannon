import React, { useContext, useEffect, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import config from './config';
import { AuthContext } from './contexts/AuthContext';
import { useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import observabilityService from './services/observabilityService';
import Layout from './components/Layout';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { loadRoutesConfig } from './config/routesConfig';

const RouteChangeTracker = () => {
  const location = useLocation();
  const { user } = useContext(AuthContext);
  console.log("App.jsx")
  useEffect(() => {
    observabilityService.log({
      eventType: 'navigation',
      message: `User navigated to ${location.pathname}`,
      metadata: {
        path: location.pathname,
        userId: user?.uid,
      },
    });
  }, [location, user]);

  return null;
};

function PrivateRoute({ children }) {
  const { user, loading } = useContext(AuthContext);
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  return user ? children : <Navigate to="/login" />;
}

const buildRouteElement = (route) => {
  let element = route.element;

  if (route.layout !== false) {
    element = <Layout>{element}</Layout>;
  }

  if (route.private !== false) {
    element = <PrivateRoute>{element}</PrivateRoute>;
  }

  return element;
};

const renderRoute = (route, keyPrefix, index) => {
  const key = route.path ? `${keyPrefix}-${route.path}` : `${keyPrefix}-${index}`;
  const element = buildRouteElement(route);

  if (route.index) {
    return <Route key={key} index element={element} />;
  }

  return (
    <Route key={key} path={route.path} element={element}>
      {route.children?.map((child, childIndex) => renderRoute(child, `${key}-child`, childIndex))}
    </Route>
  );
};

function App() {
  useEffect(() => {
    document.title = config?.app?.name || 'Gofannon: Web UI';
  }, []);

  const routes = useMemo(() => loadRoutesConfig(), []);
  return (
    <ErrorBoundary>
    <Router>
      <RouteChangeTracker />
      <Routes>
        {routes.map((route, index) => renderRoute(route, 'route', index))}
      </Routes>

    </Router>
    </ErrorBoundary>
  );
}

export default App;
