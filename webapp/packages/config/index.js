
import localConfig from './environments/local.js';
import firebaseConfig from './environments/firebase.js';
// import amplifyConfig from './environments/amplify.js';
// import kubernetesConfig from './environments/kubernetes.js';

const env = import.meta.env.VITE_APP_ENV || process.env.APP_ENV || 'local';
console.log(`Using configuration for environment: ${env}`);

let config;

switch (env) {
  case 'firebase':
    console.log("Loading Firebase configuration: ", firebaseConfig);
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

config.name = "Gofannon WebApp"
export default config;