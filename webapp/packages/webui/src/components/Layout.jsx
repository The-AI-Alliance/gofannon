import React from 'react';
import PropTypes from 'prop-types';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  CssBaseline,
} from '@mui/material';

/**
 * A responsive layout component that provides a consistent structure
 * with a top navigation bar and a main content area.
 * @param {object} props - The component props.
 * @param {React.ReactNode} props.children - The child elements to be rendered within the main content area.
 * @returns {React.ReactElement} The rendered Layout component.
 */
const Layout = ({ children }) => {
  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Gofannon WebApp
          </Typography>
          {/* Add Navigation Links or User Menu here later */}
        </Toolbar>
      </AppBar>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
        }}
      >
        <Toolbar /> {/* Spacer for the AppBar */}
        <Container maxWidth="lg">
          {children}
        </Container>
      </Box>
    </Box>
  );
};

Layout.propTypes = {
  /**
   * The content of the page.
   */
  children: PropTypes.node.isRequired,
};

export default Layout;