import CampaignIcon from '@mui/icons-material/Campaign';

export const card = {
  id: 'echo',
  title: 'Echo Chamber',
  description: 'A simple page that echoes back what you type.',
  buttonText: 'Go',
  icon: <CampaignIcon />,
  iconColor: 'primary.main',
  defaultOrder: 99,
  onAction: ({ navigate }) => navigate('/echo'),
};