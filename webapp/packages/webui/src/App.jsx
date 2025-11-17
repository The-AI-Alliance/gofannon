import React, { useContext, useEffect, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import config from './config';
import { AuthContext } from './contexts/AuthContext';
import { useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import observabilityService from './services/observabilityService';
import Layout from './components/Layout';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';


import loadRoutesConfig from './config/routes/loadRoutesConfig';

const RouteChangeTracker = () => {
  const location = useLocation();
  const { user } = useContext(AuthContext);

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

const wrapWithProviders = (element, providers = []) =>
  (providers || []).reduceRight((child, Provider) => <Provider>{child}</Provider>, element);

const buildRouteElement = (route) => {
  const baseElement =
    route.element ?? (route.children?.length ? <Outlet /> : <React.Fragment />);
  const wrappedContent = wrapWithProviders(baseElement, route.providers);
  const useLayout = route.useLayout ?? true;
  const withLayout = useLayout ? <Layout>{wrappedContent}</Layout> : wrappedContent;
  const requiresAuth = route.requiresAuth ?? true;

  return requiresAuth ? <PrivateRoute>{withLayout}</PrivateRoute> : withLayout;
};

const renderRoute = (route) => {
  const element = buildRouteElement(route);
  const children = route.children?.map((child) => renderRoute(child));
  const key = route.id || route.path || route.index;

  if (route.index) {
    return <Route key={key} index element={element} />;
  }

  return (
    <Route key={key} path={route.path} element={element}>
      {children}
    </Route>
  );
};

function App() {
  const routesConfig = useMemo(() => loadRoutesConfig(), []);
  useEffect(() => {
    document.title = config?.app?.name || 'Gofannon: Web UI';
  }, []);
  return (
    <ErrorBoundary>
      <Router>
        <RouteChangeTracker />
        <Routes>{routesConfig.routes.map((route) => renderRoute(route))}</Routes>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
