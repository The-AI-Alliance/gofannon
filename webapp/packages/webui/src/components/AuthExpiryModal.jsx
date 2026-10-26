// webapp/packages/webui/src/components/AuthExpiryModal.jsx
//
// listens for the `auth:session-expired` custom event dispatched
// by services/fetchInterceptor.js when the API returns HTTP 401 with the
// X-Auth-Reason: session_expired header. Renders a modal prompting the user
// to sign in again, capturing the path they were on so we can return them
// there after re-login.
//
// Genuinely-anonymous 401s (X-Auth-Reason: not_authenticated) do NOT trigger
// this modal -- those are handled by the existing route guards.

import React, { useEffect, useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from '@mui/material';

export default function AuthExpiryModal() {
  const [open, setOpen] = useState(false);
  const [returnTo, setReturnTo] = useState('/');

  useEffect(() => {
    const handler = (event) => {
      const detail = (event && event.detail) || {};
      setReturnTo(detail.returnTo || '/');
      setOpen(true);
    };
    window.addEventListener('auth:session-expired', handler);
    return () => window.removeEventListener('auth:session-expired', handler);
  }, []);

  const handleSignIn = () => {
    const encoded = encodeURIComponent(returnTo);
    window.location.href = `/login?returnTo=${encoded}`;
  };

  return (
    <Dialog open={open}>
      <DialogTitle>Session expired</DialogTitle>
      <DialogContent>
        <Typography>
          Your session has expired. Please sign in again to continue.
          You will return to the page you were on after signing in.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleSignIn} variant="contained" color="primary">
          Sign in
        </Button>
      </DialogActions>
    </Dialog>
  );
}
