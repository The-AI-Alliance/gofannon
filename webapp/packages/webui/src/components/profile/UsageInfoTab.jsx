import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const UsageInfoTab = () => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Usage
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography color="text.secondary">
          Usage insights are coming soon. We&apos;re working on adding detailed metrics for your account.
        </Typography>
      </Paper>
    </Box>
  );
};

export default UsageInfoTab;
