// frontend/src/components/TravelForm.js
import React, { useState } from 'react';
import { TextField, Button, Box, CircularProgress, Alert, Link } from '@mui/material';

function TravelForm() {
  const [destination, setDestination] = useState('');
  const [dates, setDates] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setPdfUrl(null);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/generate-trip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination,
          dates,
          budget: budget ? parseFloat(budget) : null
        }),
      });
      if (!response.ok) throw new Error('La respuesta del servidor no fue OK');
      const data = await response.json();
      if (data.download_url) setPdfUrl(data.download_url);
      else if (data.error) setError(data.error);
    } catch (err) {
      setError('No se pudo conectar con el servidor. ¿Está funcionando?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
        <TextField
          label="Destino"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          fullWidth
          required
          margin="normal"
        />
        <TextField
          label="Fechas"
          value={dates}
          onChange={(e) => setDates(e.target.value)}
          fullWidth
          required
          margin="normal"
        />
        <TextField
          label="Presupuesto (opcional)"
          type="number"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          fullWidth
          margin="normal"
        />
        <Box sx={{ mt: 2, position: 'relative' }}>
          <Button
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            disabled={loading}
          >
            Generar Itinerario
          </Button>
          {loading && (
            <CircularProgress
              size={24}
              sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                marginTop: '-12px',
                marginLeft: '-12px',
              }}
            />
          )}
        </Box>
      </Box>

      {/* Muestra el resultado o el estado de carga */}
      <Box sx={{ mt: 4 }}>
        {error && <Alert severity="error">{error}</Alert>}
        {pdfUrl && (
          <Alert severity="success">
            <h3>¡Tu itinerario está listo!</h3>
            <Link href={pdfUrl} target="_blank" rel="noopener noreferrer" underline="hover">
              Haz clic aquí para descargar tu PDF
            </Link>
          </Alert>
        )}
      </Box>
    </Box>
  );
}

export default TravelForm;