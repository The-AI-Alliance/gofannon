import React, { useState } from 'react';
import { Box, Button, Stack, TextField, Typography } from '@mui/material';
import config from '../../config';

const EchoPage = () => {
  const [value, setValue] = useState('');
  const [echo, setEcho] = useState('');
  const [isSending, setIsSending] = useState(false);

  const sendEcho = async () => {
    setIsSending(true);
    try {
      const response = await fetch(`${config.api.baseUrl}/extensions/echo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value }),
      });
      const payload = await response.json();
      setEcho(payload.echo ?? '');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Echo
      </Typography>
      <Typography color="text.secondary" paragraph>
        Type any message and the API will echo it back.
      </Typography>
      <Stack direction="row" spacing={2} alignItems="center">
        <TextField
          fullWidth
          label="Message"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Button variant="contained" onClick={sendEcho} disabled={isSending}>
          {isSending ? 'Sending…' : 'Send'}
        </Button>
      </Stack>
      {echo && (
        <Typography sx={{ mt: 2 }}>
          Echoed: <strong>{echo}</strong>
        </Typography>
      )}
    </Box>
  );
};

export default EchoPage;
