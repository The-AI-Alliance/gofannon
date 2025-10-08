import React, { useContext, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import config from './config';
import { AuthContext } from './contexts/AuthContext';
import { AgentCreationFlowProvider } from './pages/AgentCreationFlow/AgentCreationFlowContext'; // Import AgentCreationFlowProvider
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ToolsScreen from './pages/AgentCreationFlow/ToolsScreen'; // Import agent flow screens
import DescriptionScreen from './pages/AgentCreationFlow/DescriptionScreen';
import SchemasScreen from './pages/AgentCreationFlow/SchemasScreen';
import CodeEditorScreen from './pages/AgentCreationFlow/CodeEditorScreen';
import SandboxScreen from './pages/AgentCreationFlow/SandboxScreen';
import DeployScreen from './pages/AgentCreationFlow/DeployScreen';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

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
          path="/chat"
          element={
            <PrivateRoute>
              <Layout>
                <ChatPage />
              </Layout>
            </PrivateRoute>
          }
        />
        {/* Agent Creation Flow Routes */}
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
                    <Route path="code" element={<CodeEditorScreen />} />
                    <Route path="sandbox" element={<SandboxScreen />} />
                    <Route path="deploy" element={<DeployScreen />} />
                  </Routes>
                </AgentCreationFlowProvider>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
