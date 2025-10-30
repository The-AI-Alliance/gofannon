import React from 'react';
import PropTypes from 'prop-types';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Paper,
} from '@mui/material';

const SpecViewerModal = ({ open, onClose, specName, specContent }) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Viewing Spec: {specName}</DialogTitle>
      <DialogContent>
        <Paper variant="outlined" sx={{ p: 2, mt: 1, backgroundColor: '#2e2e2e', maxHeight: '60vh', overflowY: 'auto' }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: '#e0e0e0' }}>
            {specContent}
          </pre>
        </Paper>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

SpecViewerModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  specName: PropTypes.string,
  specContent: PropTypes.string,
};

SpecViewerModal.defaultProps = {
    specName: '',
    specContent: '',
};

export default SpecViewerModal;