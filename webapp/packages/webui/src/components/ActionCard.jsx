import React from 'react';
import PropTypes from 'prop-types';
import { Paper, Box, Typography, Button } from '@mui/material';

const ActionCard = ({ icon, title, description, buttonText, buttonColor, iconColor, onClick }) => {
  return (
    <Paper
      onClick={onClick}
      sx={{
        width: 300,        // fixed width
        height: 150,
        p: 2,
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 2,
        height: '100%',
        cursor: 'pointer',
        
        transition: 'box-shadow 0.3s, background-color 0.3s',
        '&:hover': {
          backgroundColor: 'action.hover',
          boxShadow: 3,
        },
      }}
    >
      <Box sx={{ color: iconColor, flexShrink: 0 }}>
        {React.cloneElement(icon, { sx: { fontSize: 48 } })}
      </Box>

      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', textAlign: 'right', overflow: 'hidden', height: '100%' }}>
        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <Typography variant="h6" noWrap title={title}>
            {title}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            title={description}
            sx={{
                whiteSpace: 'normal',       // allow wrapping
                overflow: 'hidden',         // keep inside fixed box
                textOverflow: 'ellipsis',   // optional: show ellipsis
                display: 'block',           // normal block layout
                maxHeight: '3em',           // limit height (≈ 2 lines depending on font)
                lineHeight: 1.5,            // consistent spacing
            }}
          >
            {description}
          </Typography>
        </Box>
        <Button
          variant="contained"
          color={buttonColor}
          size="small"
          sx={{ mt: 1, flexShrink: 0 }}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
        >
          {buttonText}
        </Button>
      </Box>
    </Paper>
  );
};

ActionCard.propTypes = {
  icon: PropTypes.element.isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  buttonText: PropTypes.string.isRequired,
  buttonColor: PropTypes.string,
  iconColor: PropTypes.string,
  onClick: PropTypes.func.isRequired,
};

ActionCard.defaultProps = {
    buttonColor: 'primary',
    iconColor: 'inherit',
};

export default ActionCard;