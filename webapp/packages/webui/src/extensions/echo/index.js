// webapp/packages/webui/src/extensions/echo/index.js
import EchoCard from './EchoCard';
import EchoPage from './EchoPage';

export const cards = [
    {
        name: 'EchoCard',
        component: EchoCard,
    }
];

export const pages = [
    {
        path: '/echo',
        name: 'EchoPage',
        component: EchoPage,
        layout: true,
    }
];
