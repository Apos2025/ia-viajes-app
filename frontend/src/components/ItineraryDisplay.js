// frontend/src/components/ItineraryDisplay.js
import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

function ItineraryDisplay({ text }) {
  return (
    <Box sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ p: 3, whiteSpace: 'pre-wrap', backgroundColor: '#f5f5f5' }}>
        <Typography variant="h5" gutterBottom>
          Tu Plan de Viaje Sugerido
        </Typography>
        <Typography variant="body1">
          {text}
        </Typography>
      </Paper>
    </Box>
  );
}

export default ItineraryDisplay;