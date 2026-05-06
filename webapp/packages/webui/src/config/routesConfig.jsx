import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import HomePage from '../pages/HomePage';
import ChatPage from '../pages/ChatPage';
import ViewAgent from '../pages/ViewAgent';
import SavedAgentsPage from '../pages/SavedAgentsPage';
import DeployedApisPage from '../pages/DeployedApisPage';
import DemoAppsPage from '../pages/DemoAppsPage';
import ViewDemoAppPage from '../pages/ViewDemoAppPage';
import DataStoresPage from '../pages/DataStoresPage';
import DataStoreBrowser from '../pages/DataStoreBrowser';
import RunsScreen from '../pages/AgentCreationFlow/RunsScreen';
import DeployScreen from '../pages/AgentCreationFlow/DeployScreen';
import SelectApisScreen from '../pages/DemoCreationFlow/SelectApisScreen';
import SelectModelScreen from '../pages/DemoCreationFlow/SelectModelScreen';
import CanvasScreen from '../pages/DemoCreationFlow/CanvasScreen';
import SaveDemoScreen from '../pages/DemoCreationFlow/SaveDemoScreen';
import { AgentCreationFlowProvider } from '../pages/AgentCreationFlow/AgentCreationFlowContext';
import { DemoCreationFlowProvider } from '../pages/DemoCreationFlow/DemoCreationFlowContext';
import ProfilePage from '../pages/ProfilePage';
import AdminPanel from '../pages/AdminPanel';
// import extendRoutes from '../extensions/routes/routeExtensions';

const isAdminPanelEnabled = () => {
  const envValue = import.meta.env.VITE_ADMIN_PANEL_ENABLED ?? 'false';
  const raw = envValue.toString();
  return raw.toLowerCase() === 'true';
};

export const defaultRoutes = [
  {
    path: '/login',
    element: <LoginPage />,
    private: false,
    layout: false,
  },
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/agents',
    element: <SavedAgentsPage />,
  },
  {
    path: '/deployed-apis',
    element: <DeployedApisPage />,
  },
  {
    path: '/demo-apps',
    element: <DemoAppsPage />,
  },
  {
    path: '/data-stores',
    element: <DataStoresPage />,
  },
  {
    path: '/data-stores/:namespace',
    element: <DataStoreBrowser />,
  },
  {
    path: '/profile/:section?',
    element: <ProfilePage />,
  },
  {
    path: '/demos/:demoId',
    element: <ViewDemoAppPage />, // This page renders the app without the shell
    layout: false,
  },
  {
    path: '/chat',
    element: <ChatPage />,
  },
  {
    path: '/agent/:agentId',
    element: (
      <AgentCreationFlowProvider>
        <ViewAgent />
      </AgentCreationFlowProvider>
    ),
  },
  {
    path: '/agent/:agentId/deploy',
    element: (
      <AgentCreationFlowProvider>
        <DeployScreen />
      </AgentCreationFlowProvider>
    ),
  },
  {
    path: '/agent/:agentId/runs/:runId?',
    element: (
      <AgentCreationFlowProvider>
        <RunsScreen />
      </AgentCreationFlowProvider>
    ),
  },
  {
    path: '/create-agent/*',
    element: (
      <AgentCreationFlowProvider>
        <Outlet />
      </AgentCreationFlowProvider>
    ),
    children: [
      { index: true, element: <ViewAgent />, private: false, layout: false },
      { path: 'tools', element: <Navigate to="/create-agent" replace />, private: false, layout: false }, // Legacy redirect
      { path: 'description', element: <Navigate to="/create-agent" replace />, private: false, layout: false }, // Legacy redirect
      { path: 'schemas', element: <Navigate to="/create-agent" replace />, private: false, layout: false }, // Legacy redirect
      { path: 'code', element: <Navigate to="/create-agent" replace />, private: false, layout: false }, // Legacy redirect
      { path: 'sandbox', element: <RunsScreen />, private: false, layout: false },
      { path: 'deploy', element: <DeployScreen />, private: false, layout: false },
    ],
  },
  {
    path: '/create-demo/*',
    element: (
      <DemoCreationFlowProvider>
        <Outlet />
      </DemoCreationFlowProvider>
    ),
    children: [
      { index: true, element: <Navigate to="select-apis" replace />, private: false, layout: false },
      { path: 'select-apis', element: <SelectApisScreen />, private: false, layout: false },
      { path: 'select-model', element: <SelectModelScreen />, private: false, layout: false },
      { path: 'canvas', element: <CanvasScreen />, private: false, layout: false },
      { path: 'save', element: <SaveDemoScreen />, private: false, layout: false },
    ],
  },
];

if (isAdminPanelEnabled()) {
  defaultRoutes.push({
    path: '/admin',
    element: <AdminPanel />,
  });
}

import { routes as extensionRoutes } from '../extensions';

export const loadRoutesConfig = () => {
  return [...defaultRoutes, ...extensionRoutes];
};

export default loadRoutesConfig;