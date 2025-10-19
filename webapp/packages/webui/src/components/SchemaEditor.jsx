import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';

const SchemaEditor = ({ title, schema, setSchema }) => {
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldType, setNewFieldType] = useState('string');

  const handleAddField = () => {
    if (newFieldName.trim() && !schema[newFieldName.trim()]) {
      const updatedSchema = {
        ...schema,
        [newFieldName.trim()]: newFieldType,
      };
      setSchema(updatedSchema);
      setNewFieldName('');
      setNewFieldType('string');
    }
  };

  const handleDeleteField = (fieldName) => {
    const { [fieldName]: _, ...remainingSchema } = schema;
    setSchema(remainingSchema);
  };

  return (
    <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 2, bgcolor: 'background.default', height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 1 }}>{title}</Typography>
      
      <List dense sx={{ minHeight: '100px' /* Give it some space */ }}>
        {Object.keys(schema).length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{p:1}}>No fields defined.</Typography>
        ) : Object.entries(schema).map(([name, type]) => (
          <ListItem
            key={name}
            secondaryAction={
              <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteField(name)}>
                <DeleteIcon />
              </IconButton>
            }
            sx={{ pl: 0 }}
          >
            <ListItemText primary={name} secondary={type} />
          </ListItem>
        ))}
      </List>

      <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
        <TextField
          label="Field Name"
          variant="outlined"
          size="small"
          value={newFieldName}
          onChange={(e) => setNewFieldName(e.target.value)}
          sx={{ flexGrow: 1 }}
        />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Type</InputLabel>
          <Select
            value={newFieldType}
            label="Type"
            onChange={(e) => setNewFieldType(e.target.value)}
          >
            <MenuItem value="string">string</MenuItem>
            <MenuItem value="integer">integer</MenuItem>
            <MenuItem value="float">float</MenuItem>
            <MenuItem value="boolean">boolean</MenuItem>
            <MenuItem value="list">list</MenuItem>
          </Select>
        </FormControl>
        <Button
          onClick={handleAddField}
          startIcon={<AddCircleOutlineIcon />}
          disabled={!newFieldName.trim()}
          variant="outlined"
          size="small"
        >
          Add
        </Button>
      </Stack>
    </Box>
  );
};

SchemaEditor.propTypes = {
  title: PropTypes.string.isRequired,
  schema: PropTypes.object.isRequired,
  setSchema: PropTypes.func.isRequired,
};

export default SchemaEditor;