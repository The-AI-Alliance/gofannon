
import localConfig from './environments/local.js';
// import firebaseConfig from './environments/firebase.js';
// import amplifyConfig from './environments/amplify.js';
// import kubernetesConfig from './environments/kubernetes.js';


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

config.name = "Gofannon WebApp"
export default config;