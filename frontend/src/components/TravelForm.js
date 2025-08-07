// frontend/src/components/TravelForm.js
import React, { useState } from 'react';
import { TextField, Button, Box, CircularProgress, Alert } from '@mui/material';
import ItineraryDisplay from './ItineraryDisplay'; // Importamos el nuevo componente

function TravelForm() {
  const [destination, setDestination] = useState('');
  const [dates, setDates] = useState('');
  const [budget, setBudget] = useState('');

  const [loading, setLoading] = useState(false);
  const [itinerary, setItinerary] = useState(null); // Antes era pdfUrl, ahora es itinerary
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setItinerary(null);
    setError(null);

    try {
      const apiUrl = `${process.env.REACT_APP_API_URL}/api/generate-trip`;
      const response = await fetch(apiUrl, {
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
      if (data.itinerary) setItinerary(data.itinerary);
      else if (data.error) setError(data.error);
    } catch (err) {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
        {/* ... Los campos TextField siguen igual que antes ... */}
        <TextField label="Destino" value={destination} onChange={(e) => setDestination(e.target.value)} fullWidth required margin="normal" />
        <TextField label="Fechas" value={dates} onChange={(e) => setDates(e.target.value)} fullWidth required margin="normal" />
        <TextField label="Presupuesto (opcional)" type="number" value={budget} onChange={(e) => setBudget(e.target.value)} fullWidth margin="normal" />
        <Box sx={{ mt: 2, position: 'relative' }}>
          <Button type="submit" variant="contained" size="large" fullWidth disabled={loading}>
            Generar Itinerario
          </Button>
          {loading && <CircularProgress size={24} sx={{ position: 'absolute', top: '50%', left: '50%', marginTop: '-12px', marginLeft: '-12px' }} />}
        </Box>
      </Box>

      <Box sx={{ mt: 4 }}>
        {error && <Alert severity="error">{error}</Alert>}
        {/* Si hay un itinerario, lo mostramos con el nuevo componente */}
        {itinerary && <ItineraryDisplay text={itinerary} />}
      </Box>
    </Box>
  );
}

export default TravelForm;