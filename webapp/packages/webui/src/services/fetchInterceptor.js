// webapp/packages/webui/src/services/fetchInterceptor.js
//
// Wraps ``window.fetch`` once at module load so that any request to the
// Gofannon API base URL automatically includes credentials (the
// ``gofannon_sid`` cookie, once Phase B is on).
//
// Why this shim instead of editing each service's fetch call:
//   - 19+ call sites across agentService, dataStoreService, apiClient,
//     chatService, mcpService. Editing each is error-prone and future
//     service files would need the same boilerplate.
//   - No side effects for non-API fetches (e.g. importing third-party
//     scripts). We narrow by URL prefix.
//   - No side effects when ``credentials`` is already set by the caller
//     (e.g. authService uses ``credentials: 'include'`` explicitly and
//     that's preserved).
//
// The wrapper installs itself on first import. Imported from App.jsx so
// it runs before any service makes its first call.

import appConfig from '../config';

function installFetchInterceptor() {
  if (typeof window === 'undefined' || !window.fetch) return;
  if (window.__gofannonFetchInstalled) return;
  window.__gofannonFetchInstalled = true;

  const originalFetch = window.fetch.bind(window);
  const apiBase = (appConfig?.api?.baseUrl || '').replace(/\/$/, '');
  // Empty base means same-origin API; we still want to add credentials
  // so the cookie is sent.
  const apiMatches = (url) => {
    if (typeof url !== 'string') {
      // Request object: inspect url property. Preserve credentials if
      // already set on the Request.
      url = url.url;
    }
    if (!url) return false;
    if (apiBase) return url.startsWith(apiBase);
    // No configured baseUrl: only touch relative URLs that look like
    // API calls. Everything that starts with "/" is plausibly ours.
    return url.startsWith('/') && !url.startsWith('//');
  };

  window.fetch = async (input, init = {}) => {
    if (apiMatches(input) && init.credentials === undefined) {
      init = { ...init, credentials: 'include' };
    }
    return originalFetch(input, init);
  };
}

installFetchInterceptor();

export default installFetchInterceptor;
