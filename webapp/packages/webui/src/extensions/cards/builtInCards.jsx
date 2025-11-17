import ChatIcon from '@mui/icons-material/Chat';
import CodeIcon from '@mui/icons-material/Code';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ApiIcon from '@mui/icons-material/Api';
import WebIcon from '@mui/icons-material/Web';

export const builtInCards = [
  {
    id: 'chat',
    title: 'Start Chatting',
    description: 'Chat with AI models powered by LiteLLM',
    buttonText: 'Open Chat',
    icon: <ChatIcon />, 
    iconColor: 'primary.main',
    buttonColor: 'primary',
    defaultOrder: 1,
    onAction: ({ navigate }) => navigate('/chat'),
  },
  {
    id: 'create-agent',
    title: 'Create New Agent',
    description: 'Define tools and behavior for a new AI agent',
    buttonText: 'Start Agent Creation',
    icon: <CodeIcon />, 
    iconColor: 'secondary.main',
    buttonColor: 'secondary',
    defaultOrder: 2,
    onAction: ({ navigate }) => navigate('/create-agent'),
  },
  {
    id: 'saved-agents',
    title: 'View Saved Agents',
    description: 'Browse and manage your previously created agents',
    buttonText: 'Browse Agents',
    icon: <SmartToyIcon />, 
    iconColor: 'success.main',
    buttonColor: 'success',
    defaultOrder: 3,
    onAction: ({ navigate }) => navigate('/agents'),
  },
  {
    id: 'deployed-apis',
    title: 'View Deployed APIs',
    description: 'Browse all agents deployed as REST endpoints.',
    buttonText: 'Browse APIs',
    icon: <ApiIcon />, 
    iconColor: 'info.main',
    buttonColor: 'info',
    defaultOrder: 4,
    onAction: ({ navigate }) => navigate('/deployed-apis'),
  },
  {
    id: 'create-demo',
    title: 'Create Demo App',
    description: 'Build a web UI that uses your deployed agents.',
    buttonText: 'Create Demo',
    icon: <WebIcon />, 
    iconColor: 'warning.main',
    buttonColor: 'warning',
    defaultOrder: 5,
    onAction: ({ navigate }) => navigate('/create-demo'),
  },
  {
    id: 'demo-apps',
    title: 'View Demo Apps',
    description: 'View and manage your saved demo applications.',
    buttonText: 'View Demos',
    icon: <WebIcon />, 
    iconColor: 'secondary.light',
    buttonColor: 'secondary',
    defaultOrder: 6,
    onAction: ({ navigate }) => navigate('/demo-apps'),
  },
];

export const registerBuiltInCards = (registerCard) => builtInCards.forEach((card) => registerCard(card));

export default registerBuiltInCards;