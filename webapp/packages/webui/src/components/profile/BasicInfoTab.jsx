import React from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Paper, Stack, Divider } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

const InfoRow = ({ label, value }) => (
  <Stack direction="row" justifyContent="space-between" alignItems="center" py={1}>
    <Typography variant="subtitle2" color="text.secondary">
      {label}
    </Typography>
    <Typography variant="body1" sx={{ ml: 2 }}>
      {value || 'Not provided'}
    </Typography>
  </Stack>
);

InfoRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),
};

const BasicInfoTab = () => {
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Basic Information
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        {user ? (
          <Stack spacing={0}>
            <InfoRow label="Display Name" value={user.displayName} />
            <Divider />
            <InfoRow label="Email" value={user.email} />
            <Divider />
            <InfoRow label="User ID" value={user.uid} />
          </Stack>
        ) : (
          <Typography color="text.secondary">
            No user information available.
          </Typography>
        )}
      </Paper>
    </Box>
  );
};

export default BasicInfoTab;
