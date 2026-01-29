// webapp/packages/webui/src/components/ProfileMenu.jsx
import React, { useState } from 'react';
import { Divider, IconButton, Menu, MenuItem } from '@mui/material';
import AccountCircle from '@mui/icons-material/AccountCircle';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContextValue';

const isAdminPanelEnabled = () => {
  const envValue = import.meta.env.VITE_ADMIN_PANEL_ENABLED ?? 'false';
  const raw = envValue.toString();
  return raw.toLowerCase() === 'true';
};

const ProfileMenu = () => {
  const { logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    handleClose();
  };

  const handleNavigate = (path) => {
    navigate(path);
    handleClose();
  };

  return (
    <div>
      <IconButton
        size="large"
        aria-label="account of current user"
        aria-controls="menu-appbar"
        aria-haspopup="true"
        onClick={handleMenu}
        color="inherit"
      >
        <AccountCircle />
      </IconButton>
      <Menu
        id="menu-appbar"
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        <MenuItem onClick={() => handleNavigate('/profile/basic')}>Basic Info</MenuItem>
        <MenuItem onClick={() => handleNavigate('/profile/usage')}>Usage</MenuItem>
        <MenuItem onClick={() => handleNavigate('/profile/billing')}>Billing</MenuItem>
        <MenuItem onClick={() => handleNavigate('/profile/apikeys')}>API Keys</MenuItem>
        {isAdminPanelEnabled() && (
          <MenuItem onClick={() => handleNavigate('/admin')}>Admin Panel</MenuItem>
        )}
        <Divider />
        <MenuItem onClick={handleLogout}>Logout</MenuItem>
      </Menu>
    </div>
  );
};

export default ProfileMenu;