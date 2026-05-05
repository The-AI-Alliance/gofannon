// webapp/packages/webui/src/components/ProfileMenu.jsx
import React, { useState } from 'react';
import {
  Box,
  Chip,
  Divider,
  IconButton,
  ListItemIcon,
  ListSubheader,
  Menu,
  MenuItem,
  Snackbar,
  Alert,
  Typography,
} from '@mui/material';
import AccountCircle from '@mui/icons-material/AccountCircle';
import RefreshIcon from '@mui/icons-material/Refresh';
import ShieldIcon from '@mui/icons-material/Shield';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContextValue';

const isAdminPanelEnabled = () => {
  const envValue = import.meta.env.VITE_ADMIN_PANEL_ENABLED ?? 'false';
  const raw = envValue.toString();
  return raw.toLowerCase() === 'true';
};

const ProfileMenu = () => {
  const { user, logout, isSessionAuth, refreshWorkspaces } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [snack, setSnack] = useState(null);
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

  // Phase B: refresh workspace memberships from the provider. The diff
  // determines the toast text; empty diff shows "No changes".
  const handleRefreshWorkspaces = async () => {
    setRefreshing(true);
    try {
      const diff = await refreshWorkspaces();
      const parts = [];
      if (diff.added?.length) parts.push(`Added: ${diff.added.join(', ')}`);
      if (diff.removed?.length) parts.push(`Removed: ${diff.removed.join(', ')}`);
      if (diff.roleChanges?.length) parts.push(`Role changes: ${diff.roleChanges.join(', ')}`);
      if (diff.siteAdminChanged) parts.push('Site admin status changed');
      setSnack({
        severity: parts.length ? 'success' : 'info',
        message: parts.length ? parts.join('. ') : 'No workspace changes.',
      });
    } catch (e) {
      setSnack({ severity: 'error', message: e.message || 'Refresh failed.' });
    } finally {
      setRefreshing(false);
      handleClose();
    }
  };

  // Workspace-section rendering. Only relevant when the backend is in
  // session-auth mode and the user has workspaces loaded on their
  // session. For legacy Firebase users this section is skipped.
  const workspaces = (isSessionAuth && user?.workspaces) || [];
  const isSiteAdmin = !!user?.isSiteAdmin;

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
        PaperProps={{ sx: { minWidth: 260 } }}
      >
        {/* User identity header. Rendered for session mode only, because
            Firebase-mode user objects don't always have displayName. */}
        {isSessionAuth && user && (
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {user.displayName || user.uid}
            </Typography>
            {user.email && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {user.email}
              </Typography>
            )}
            {isSiteAdmin && (
              <Chip
                icon={<ShieldIcon sx={{ fontSize: 14 }} />}
                label="Site admin"
                size="small"
                color="warning"
                sx={{ mt: 0.5, height: 20, fontSize: '0.68rem' }}
              />
            )}
          </Box>
        )}
        {isSessionAuth && user && <Divider />}

        {/* Workspaces list. Read-only preview; the B-3 switcher is what
            actually changes the active workspace. Max 5 shown inline
            with a "+N more" row if there are more than 5 — keeps the
            menu compact. */}
        {workspaces.length > 0 && [
          <ListSubheader key="ws-header" sx={{ lineHeight: '28px', fontSize: '0.7rem' }}>
            WORKSPACES
          </ListSubheader>,
          ...workspaces.slice(0, 5).map((w) => (
            <MenuItem key={w.workspaceId} disabled sx={{ py: 0.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Typography
                  variant="body2"
                  sx={{ flexGrow: 1, fontSize: '0.85rem', color: 'text.primary' }}
                >
                  {w.displayName || w.workspaceId}
                </Typography>
                {w.role === 'admin' && (
                  <Chip label="admin" size="small" sx={{ height: 18, fontSize: '0.65rem' }} />
                )}
              </Box>
            </MenuItem>
          )),
          workspaces.length > 5 && (
            <MenuItem key="ws-more" disabled sx={{ py: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                +{workspaces.length - 5} more
              </Typography>
            </MenuItem>
          ),
          <Divider key="ws-divider" />,
        ]}

        {/* Refresh button only makes sense in session mode. Firebase
            users don't have provider-derived workspaces. */}
        {isSessionAuth && (
          <MenuItem onClick={handleRefreshWorkspaces} disabled={refreshing}>
            <ListItemIcon>
              <RefreshIcon fontSize="small" />
            </ListItemIcon>
            {refreshing ? 'Refreshing…' : 'Refresh workspaces'}
          </MenuItem>
        )}
        {isSessionAuth && <Divider />}

        <MenuItem onClick={() => handleNavigate('/profile/apikeys')}>API Keys</MenuItem>
        {isAdminPanelEnabled() && (
          <MenuItem onClick={() => handleNavigate('/admin')}>Admin Panel</MenuItem>
        )}
        <Divider />
        <MenuItem onClick={handleLogout}>Logout</MenuItem>
      </Menu>

      <Snackbar
        open={Boolean(snack)}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snack && <Alert severity={snack.severity} onClose={() => setSnack(null)}>{snack.message}</Alert>}
      </Snackbar>
    </div>
  );
};

export default ProfileMenu;