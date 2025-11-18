import React from 'react';
import EchoPage from './echo/EchoPage';

export const route = {
    path: '/echo',
    element: <EchoPage />,
    // Inherits PrivateRoute + Layout by default
  }