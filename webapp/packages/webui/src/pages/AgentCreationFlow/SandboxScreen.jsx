import React from 'react';
import { Navigate } from 'react-router-dom';

const SandboxScreen = () => {
  // As per requirements: "For now simply navigate to the Chat endpoint"
  // The 'Run in Sandbox' button from CodeEditorScreen directly navigates here.
  // This component will then redirect to the ChatPage.
  return <Navigate to="/chat" replace />;
};

export default SandboxScreen;