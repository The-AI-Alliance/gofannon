
import localConfig from './environments/local.js';

// Browser-safe env resolution. This module is loaded by Vite into the
// browser bundle, where ``process`` is not defined — referencing
// ``process.env.APP_ENV`` throws ``ReferenceError: process is not defined``
// and prevents React from mounting. ``import.meta.env.VITE_APP_ENV`` is
// the Vite-native way to read env at build time; the ``typeof`` guard
// lets the same module run in Node contexts (SSR, tests) without
// depending on Vite.
const env = import.meta.env.VITE_APP_ENV
  || (typeof process !== 'undefined' ? process.env.APP_ENV : undefined)
  || 'local';
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