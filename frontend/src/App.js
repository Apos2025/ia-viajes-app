// frontend/src/App.js
import TravelForm from './components/TravelForm';
import { CssBaseline, Container, Typography, Box } from '@mui/material';

function App() {
  return (
    <>
      <CssBaseline /> {/* Normaliza los estilos en todos los navegadores */}
      <Container maxWidth="md">
        <Box sx={{ my: 4, textAlign: 'center' }}>
          <Typography variant="h3" component="h1" gutterBottom>
            Generador de Viajes con IA ✈️
          </Typography>
          <Typography variant="h6" color="text.secondary">
            Introduce los detalles de tu viaje y crearemos un itinerario para ti.
          </Typography>
        </Box>
        <main>
          <TravelForm />
        </main>
      </Container>
    </>
  );
}

export default App;