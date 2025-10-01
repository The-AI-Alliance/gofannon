const localConfig = require('./environments/local');
const firebaseConfig = require('./environments/firebase');
const amplifyConfig = require('./environments/amplify');
const kubernetesConfig = require('./environments/kubernetes');

const env = process.env.VITE_APP_ENV || process.env.APP_ENV || 'local';

let config;

switch (env) {
  case 'firebase':
    config = firebaseConfig;
    break;
  case 'amplify':
    config = amplifyConfig;
    break;
  case 'kubernetes':
    config = kubernetesConfig;
    break;
  default:
    config = localConfig;
}

module.exports = config;

export default config;