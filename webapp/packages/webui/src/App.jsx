import React, { useContext, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import config from './config';
import { AuthContext } from './contexts/AuthContext';
import { AgentCreationFlowProvider } from './pages/AgentCreationFlow/AgentCreationFlowContext';
import { DemoCreationFlowProvider } from './pages/DemoCreationFlow/DemoCreationFlowContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ViewAgent from './pages/ViewAgent';
import SavedAgentsPage from './pages/SavedAgentsPage';
import DeployedApisPage from './pages/DeployedApisPage';
import DemoAppsPage from './pages/DemoAppsPage';
import ViewDemoAppPage from './pages/ViewDemoAppPage';
import ToolsScreen from './pages/AgentCreationFlow/ToolsScreen'; 
import DescriptionScreen from './pages/AgentCreationFlow/DescriptionScreen';
import SchemasScreen from './pages/AgentCreationFlow/SchemasScreen';
import SandboxScreen from './pages/AgentCreationFlow/SandboxScreen';
import DeployScreen from './pages/AgentCreationFlow/DeployScreen';
import SaveAgentScreen from './pages/AgentCreationFlow/SaveAgentScreen';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

import SelectApisScreen from './pages/DemoCreationFlow/SelectApisScreen';
import SelectModelScreen from './pages/DemoCreationFlow/SelectModelScreen';
import CanvasScreen from './pages/DemoCreationFlow/CanvasScreen';
import SaveDemoScreen from './pages/DemoCreationFlow/SaveDemoScreen';

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

function App() {
  useEffect(() => {
    document.title = config?.app?.name || 'Gofannon: Web UI';
  }, []);  
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout>
                <HomePage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/agents"
          element={
            <PrivateRoute>
              <Layout>
                <SavedAgentsPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/deployed-apis"
          element={
            <PrivateRoute>
              <Layout>
                <DeployedApisPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/demo-apps"
          element={
            <PrivateRoute>
              <Layout>
                <DemoAppsPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/demos/:demoId"
          element={<ViewDemoAppPage />} // This page is public and renders the app, no layout
        />
        <Route
          path="/chat"
          element={
            <PrivateRoute>
              <Layout>
                <ChatPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/agent/:agentId"
          element={
            <PrivateRoute>
              <Layout>
                {/* Provider is needed for navigation to sandbox/deploy */}
                <AgentCreationFlowProvider>
                  <ViewAgent />
                </AgentCreationFlowProvider>
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/agent/:agentId/deploy"
          element={
            <PrivateRoute>
              <Layout>
                <AgentCreationFlowProvider>
                  <DeployScreen />
                </AgentCreationFlowProvider>
              </Layout>
            </PrivateRoute>
          }
        />
        <Route 
          path="/create-agent/*" 
          element={
            <PrivateRoute>
              <Layout>
                <AgentCreationFlowProvider>
                  <Routes>
                    <Route index element={<Navigate to="tools" replace />} /> {/* Default to tools screen */}
                    <Route path="tools" element={<ToolsScreen />} />
                    <Route path="description" element={<DescriptionScreen />} />
                    <Route path="schemas" element={<SchemasScreen />} />
                    <Route path="code" element={<ViewAgent isCreating={true} />} />
                    <Route path="sandbox" element={<SandboxScreen />} />
                    <Route path="deploy" element={<DeployScreen />} />
                    <Route path="save" element={<SaveAgentScreen />} />
                  </Routes>
                </AgentCreationFlowProvider>
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/create-demo/*"
          element={
            <PrivateRoute>
              <Layout>
                <DemoCreationFlowProvider>
                  <Routes>
                    <Route index element={<Navigate to="select-apis" replace />} />
                    <Route path="select-apis" element={<SelectApisScreen />} />
                    <Route path="select-model" element={<SelectModelScreen />} />
                    <Route path="canvas" element={<CanvasScreen />} />
                    <Route path="save" element={<SaveDemoScreen />} />
                  </Routes>
                </DemoCreationFlowProvider>
              </Layout>
            </PrivateRoute>
          }
        />        
      </Routes>
    </Router>
  );
}

export default App;
