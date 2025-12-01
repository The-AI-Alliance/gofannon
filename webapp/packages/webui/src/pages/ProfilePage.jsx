import React from 'react';
import { Box, Typography } from '@mui/material';
import { useParams } from 'react-router-dom';
import BasicInfoTab from '../components/profile/BasicInfoTab';
import UsageInfoTab from '../components/profile/UsageInfoTab';
import BillingInfoTab from '../components/profile/BillingInfoTab';

const sections = {
  basic: { label: 'Basic Info', component: <BasicInfoTab /> },
  usage: { label: 'Usage', component: <UsageInfoTab /> },
  billing: { label: 'Billing', component: <BillingInfoTab /> },
};

const ProfilePage = () => {
  const { section } = useParams();
  const sectionKey = section && sections[section] ? section : 'basic';
  const activeSection = sections[sectionKey];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Profile
      </Typography>
      <Box sx={{ pt: 1 }}>{activeSection.component}</Box>
    </Box>
  );
};

export default ProfilePage;
