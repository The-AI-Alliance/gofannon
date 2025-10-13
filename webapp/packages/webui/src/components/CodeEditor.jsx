import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Button, TextField } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';

const CodeEditor = ({ code, onCodeChange, isReadOnly = false }) => {
  const [isEditing, setIsEditing] = useState(!isReadOnly);

  const handleToggleEdit = () => {
    setIsEditing(prev => !prev);
  };

  const effectiveReadOnly = isReadOnly && !isEditing;

  return (
    <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">Python Code</Typography>
        {isReadOnly && (
          <Button size="small" startIcon={isEditing ? <SaveIcon /> : <EditIcon />} onClick={handleToggleEdit}>
            {isEditing ? 'Lock' : 'Edit'}
          </Button>
        )}
      </Box>
      <TextField
        fullWidth
        multiline
        minRows={15}
        maxRows={25}
        value={code}
        onChange={(e) => onCodeChange(e.target.value)}
        InputProps={{
          readOnly: effectiveReadOnly,
          style: {
            fontFamily: 'monospace',
            fontSize: '0.9rem',
            backgroundColor: effectiveReadOnly ? '#1e1e1e' : 'inherit',
            color: effectiveReadOnly ? '#04f500ff' : 'inherit',
          }
        }}
        sx={{ '& .MuiInputBase-root': { p: 1 } }}
      />
    </Box>
  );
};

CodeEditor.propTypes = {
  code: PropTypes.string.isRequired,
  onCodeChange: PropTypes.func.isRequired,
  isReadOnly: PropTypes.bool,
};

export default CodeEditor;