import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  LinearProgress,
} from '@mui/material';
import userService from '../../services/userService';

const UsageBar = ({ date, cost, maxCost }) => {
  const height = maxCost > 0 ? (cost / maxCost) * 160 : 0;
  return (
    <Box sx={{ flex: 1, minWidth: 48 }}>
      <Box
        sx={{
          height,
          bgcolor: 'primary.main',
          borderRadius: 1,
          transition: 'height 0.3s ease',
        }}
      />
      <Typography variant="caption" display="block" sx={{ mt: 1 }}>
        {date}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        ${cost.toFixed(2)}
      </Typography>
    </Box>
  );
};

const UsageInfoTab = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        const data = await userService.getProfile();
        setProfile(data);
      } catch (err) {
        setError(err.message || 'Failed to load usage information');
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const usageSummary = useMemo(() => {
    if (!profile?.usageInfo) return { chartData: [], maxCost: 0 };

    const grouped = profile.usageInfo.usage.reduce((acc, entry) => {
      const date = new Date(entry.timestamp).toISOString().split('T')[0];
      const cost = Number(entry.responseCost || 0);
      acc[date] = (acc[date] || 0) + cost;
      return acc;
    }, {});

    const chartData = Object.entries(grouped)
      .map(([date, cost]) => ({ date, cost }))
      .sort((a, b) => a.date.localeCompare(b.date));

    const maxCost = chartData.reduce((max, item) => Math.max(max, item.cost), 0);

    return { chartData, maxCost };
  }, [profile]);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Usage
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        {loading && <LinearProgress />}
        {!loading && error && (
          <Typography color="error" gutterBottom>
            {error}
          </Typography>
        )}
        {!loading && !error && profile && (
          <Stack spacing={2}>
            <Stack direction="row" spacing={2}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Monthly Allowance
                </Typography>
                <Typography variant="h6">
                  ${profile.usageInfo.monthlyAllowance.toFixed(2)}
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Spend Remaining
                </Typography>
                <Typography variant="h6">
                  ${profile.usageInfo.spendRemaining.toFixed(2)}
                </Typography>
              </Box>
            </Stack>

            <Divider />

            <Typography variant="subtitle1">Usage by Date</Typography>
            {usageSummary.chartData.length === 0 ? (
              <Typography color="text.secondary">
                No usage recorded yet.
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
                {usageSummary.chartData.map((item) => (
                  <UsageBar
                    key={item.date}
                    date={item.date}
                    cost={item.cost}
                    maxCost={usageSummary.maxCost}
                  />
                ))}
              </Box>
            )}
          </Stack>
        )}
      </Paper>
    </Box>
  );
};

export default UsageInfoTab;
