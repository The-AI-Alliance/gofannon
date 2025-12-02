import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import userService from '../services/userService';

const isAdminPanelEnabled = () => {
  const envValue = import.meta.env.VITE_ADMIN_PANEL_ENABLED
    ?? (typeof process !== 'undefined' ? process.env.ADMIN_PANEL_ENABLED : undefined)
    ?? 'false';
  const raw = envValue.toString();
  return raw.toLowerCase() === 'true';
};

const formatDateInput = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toISOString().slice(0, 10);
};

const parseDateInput = (value) => {
  if (!value) return 0;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }
  return parsed;
};

const AdminPanel = () => {
  const adminEnabled = useMemo(() => isAdminPanelEnabled(), []);
  const [adminPassword, setAdminPassword] = useState('');
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [edits, setEdits] = useState({});
  const [savingUserId, setSavingUserId] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (users.length === 0) return;
    const nextEdits = {};
    users.forEach((user) => {
      const usageInfo = user.usageInfo || {};
      nextEdits[user._id] = {
        monthlyAllowance: usageInfo.monthlyAllowance?.toString() ?? '',
        spendRemaining: usageInfo.spendRemaining?.toString() ?? '',
        allowanceResetDate: formatDateInput(usageInfo.allowanceResetDate),
      };
    });
    setEdits(nextEdits);
  }, [users]);

  const handleLoadUsers = async () => {
    if (!adminPassword) {
      setError('Admin password is required.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccessMessage('');
    try {
      const data = await userService.getAllUsers(adminPassword);
      setUsers(data);
      setIsAuthenticated(true);
      setSuccessMessage('Users loaded successfully.');
    } catch (err) {
      setIsAuthenticated(false);
      setError(err.message || 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (userId, field, value) => {
    setEdits((prev) => ({
      ...prev,
      [userId]: {
        ...prev[userId],
        [field]: value,
      },
    }));
  };

  const handleSaveUser = async (userId) => {
    const edit = edits[userId] || {};
    const updates = {};

    if (edit.monthlyAllowance !== undefined) {
      const parsed = parseFloat(edit.monthlyAllowance);
      if (!Number.isNaN(parsed)) {
        updates.monthlyAllowance = parsed;
      }
    }

    if (edit.spendRemaining !== undefined) {
      const parsed = parseFloat(edit.spendRemaining);
      if (!Number.isNaN(parsed)) {
        updates.spendRemaining = parsed;
      }
    }

    if (edit.allowanceResetDate !== undefined) {
      updates.allowanceResetDate = parseDateInput(edit.allowanceResetDate);
    }

    setSavingUserId(userId);
    setError('');
    setSuccessMessage('');
    try {
      const updatedUser = await userService.updateUser(userId, updates, adminPassword);
      setUsers((prev) => prev.map((user) => (user._id === userId ? updatedUser : user)));
      setSuccessMessage('User updated successfully.');
    } catch (err) {
      setError(err.message || 'Failed to update user.');
    } finally {
      setSavingUserId('');
    }
  };

  if (!adminEnabled) {
    return (
      <Box>
        <Alert severity="warning" sx={{ mb: 2 }}>
          The admin panel is disabled. Set the <code>VITE_ADMIN_PANEL_ENABLED</code> environment variable to enable it.
        </Alert>
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" gutterBottom>
          Admin Panel
        </Typography>
        <Typography variant="body1">
          Enter the admin password to manage user allowances and spend limits.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {successMessage && <Alert severity="success">{successMessage}</Alert>}

      <Card>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
            <TextField
              label="Admin Password"
              type="password"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              fullWidth
              required
            />
            <Button variant="contained" onClick={handleLoadUsers} disabled={loading}>
              {loading ? <CircularProgress size={24} /> : 'Load Users'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {isAuthenticated && (
        <Grid container spacing={2}>
          {users.map((user) => {
            const edit = edits[user._id] || {};
            return (
              <Grid item xs={12} md={6} key={user._id}>
                <Card variant="outlined">
                  <CardContent>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="h6">{user.basicInfo?.displayName || 'Unnamed User'}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {user.basicInfo?.email || 'No email'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          User ID: {user._id}
                        </Typography>
                      </Box>

                      <TextField
                        label="Monthly Allowance"
                        type="number"
                        value={edit.monthlyAllowance ?? ''}
                        onChange={(e) => handleChange(user._id, 'monthlyAllowance', e.target.value)}
                        fullWidth
                      />

                      <TextField
                        label="Spend Remaining"
                        type="number"
                        value={edit.spendRemaining ?? ''}
                        onChange={(e) => handleChange(user._id, 'spendRemaining', e.target.value)}
                        fullWidth
                      />

                      <TextField
                        label="Refill Date"
                        type="date"
                        value={edit.allowanceResetDate ?? ''}
                        onChange={(e) => handleChange(user._id, 'allowanceResetDate', e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                        helperText="Date used to reset the allowance"
                      />

                      <Box display="flex" justifyContent="flex-end">
                        <Button
                          variant="contained"
                          onClick={() => handleSaveUser(user._id)}
                          disabled={savingUserId === user._id}
                        >
                          {savingUserId === user._id ? <CircularProgress size={20} /> : 'Save Changes'}
                        </Button>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Stack>
  );
};

export default AdminPanel;
