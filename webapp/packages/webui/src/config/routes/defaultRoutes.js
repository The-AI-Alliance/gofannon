import React from 'react';
import { Navigate } from 'react-router-dom';
import LoginPage from '../../pages/LoginPage';
import HomePage from '../../pages/HomePage';
import ChatPage from '../../pages/ChatPage';
import ViewAgent from '../../pages/ViewAgent';
import SavedAgentsPage from '../../pages/SavedAgentsPage';
import DeployedApisPage from '../../pages/DeployedApisPage';
import DemoAppsPage from '../../pages/DemoAppsPage';
import ViewDemoAppPage from '../../pages/ViewDemoAppPage';
import ToolsScreen from '../../pages/AgentCreationFlow/ToolsScreen';
import DescriptionScreen from '../../pages/AgentCreationFlow/DescriptionScreen';
import SchemasScreen from '../../pages/AgentCreationFlow/SchemasScreen';
import SandboxScreen from '../../pages/AgentCreationFlow/SandboxScreen';
import DeployScreen from '../../pages/AgentCreationFlow/DeployScreen';
import SaveAgentScreen from '../../pages/AgentCreationFlow/SaveAgentScreen';
import SelectApisScreen from '../../pages/DemoCreationFlow/SelectApisScreen';
import SelectModelScreen from '../../pages/DemoCreationFlow/SelectModelScreen';
import CanvasScreen from '../../pages/DemoCreationFlow/CanvasScreen';
import SaveDemoScreen from '../../pages/DemoCreationFlow/SaveDemoScreen';
import { AgentCreationFlowProvider } from '../../pages/AgentCreationFlow/AgentCreationFlowContext';
import { DemoCreationFlowProvider } from '../../pages/DemoCreationFlow/DemoCreationFlowContext';

const defaultRoutesConfig = {
  routes: [
    {
      id: 'login',
      path: '/login',
      element: <LoginPage />,
      requiresAuth: false,
      useLayout: false,
    },
    {
      id: 'home',
      path: '/',
      element: <HomePage />,
      useLayout: true,
    },
    {
      id: 'saved-agents',
      path: '/agents',
      element: <SavedAgentsPage />,
      useLayout: true,
    },
    {
      id: 'deployed-apis',
      path: '/deployed-apis',
      element: <DeployedApisPage />,
      useLayout: true,
    },
    {
      id: 'demo-apps',
      path: '/demo-apps',
      element: <DemoAppsPage />,
      useLayout: true,
    },
    {
      id: 'view-demo',
      path: '/demos/:demoId',
      element: <ViewDemoAppPage />,
      useLayout: false,
    },
    {
      id: 'chat',
      path: '/chat',
      element: <ChatPage />,
      useLayout: true,
    },
    {
      id: 'view-agent',
      path: '/agent/:agentId',
      element: <ViewAgent />,
      useLayout: true,
      providers: [AgentCreationFlowProvider],
    },
    {
      id: 'deploy-agent',
      path: '/agent/:agentId/deploy',
      element: <DeployScreen />,
      useLayout: true,
      providers: [AgentCreationFlowProvider],
    },
    {
      id: 'create-agent-flow',
      path: '/create-agent/*',
      element: null,
      useLayout: true,
      providers: [AgentCreationFlowProvider],
      children: [
        { id: 'create-agent-default', index: true, element: <Navigate to="tools" replace /> },
        { id: 'create-agent-tools', path: 'tools', element: <ToolsScreen /> },
        { id: 'create-agent-description', path: 'description', element: <DescriptionScreen /> },
        { id: 'create-agent-schemas', path: 'schemas', element: <SchemasScreen /> },
        { id: 'create-agent-code', path: 'code', element: <ViewAgent isCreating={true} /> },
        { id: 'create-agent-sandbox', path: 'sandbox', element: <SandboxScreen /> },
        { id: 'create-agent-deploy', path: 'deploy', element: <DeployScreen /> },
        { id: 'create-agent-save', path: 'save', element: <SaveAgentScreen /> },
      ],
    },
    {
      id: 'create-demo-flow',
      path: '/create-demo/*',
      element: null,
      useLayout: true,
      providers: [DemoCreationFlowProvider],
      children: [
        { id: 'create-demo-default', index: true, element: <Navigate to="select-apis" replace /> },
        { id: 'create-demo-select-apis', path: 'select-apis', element: <SelectApisScreen /> },
        { id: 'create-demo-select-model', path: 'select-model', element: <SelectModelScreen /> },
        { id: 'create-demo-canvas', path: 'canvas', element: <CanvasScreen /> },
        { id: 'create-demo-save', path: 'save', element: <SaveDemoScreen /> },
      ],
    },
  ],
};

export default defaultRoutesConfig;
