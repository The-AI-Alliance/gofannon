import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const BillingInfoTab = () => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Billing
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography color="text.secondary">
          Billing is not enabled in the open source version.
        </Typography>
      </Paper>
    </Box>
  );
};

export default BillingInfoTab;
