import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
from amadeus import Client, ResponseError

load_dotenv()

# --- Configuración de Clientes y la App ---
client_openai = openai.OpenAI()
app = FastAPI()

try:
    amadeus = Client(
        client_id=os.getenv("AMADEUS_API_KEY"),
        client_secret=os.getenv("AMADEUS_API_SECRET")
    )
except Exception as e:
    print(f"Error al inicializar el cliente de Amadeus: {e}")
    amadeus = None

# --- Configuración de CORS ---
origins = [
    "http://localhost:3000",
    "https://ia-viajes-app.vercel.app",
]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# --- Función de Búsqueda de Hoteles con Amadeus (Versión Corregida) ---
def get_hotel_ids_by_location(latitude, longitude):
    try:
        hotels_by_geo_response = amadeus.reference_data.locations.hotels.by_geocode.get(
            latitude=latitude, longitude=longitude, radius=20, radiusUnit='KM', ratings='3,4,5', hotelSource='ALL'
        )
        if not hotels_by_geo_response.data:
            return []
        hotel_ids = [hotel['hotelId']
            for hotel in hotels_by_geo_response.data[:5]]
        print(f"IDs de hoteles encontrados: {hotel_ids}")
        return hotel_ids
    except ResponseError as e:
        print(f"Error obteniendo IDs de hoteles: {e}")
        return []


def search_real_hotels(destination_name: str):
    if not amadeus:
        return "El servicio de búsqueda de hoteles no está disponible."
    try:
        print(f"Buscando hoteles en Amadeus para: {destination_name}")
        city_search = amadeus.reference_data.locations.get(
            keyword=destination_name, subType='CITY')
        if not city_search.data:
            return "No se encontró el destino."

        location = city_search.data[0]
        latitude = location['geoCode']['latitude']
        longitude = location['geoCode']['longitude']
        print(f"Coordenadas encontradas: Lat {latitude}, Lon {longitude}")

        hotel_ids = get_hotel_ids_by_location(latitude, longitude)
        if not hotel_ids:
            return "No se encontraron hoteles para este destino."

        hotel_offers_response = amadeus.shopping.hotel_offers_by_hotel.get(
            hotelIds=hotel_ids)
        if not hotel_offers_response.data:
            return "No se encontraron ofertas de hotel para este destino."

        formatted_hotels = []
        for offer in hotel_offers_response.data[:3]:
            hotel = offer.get('hotel', {})
            price_info = offer.get('offers', [{}])[0].get('price', {})
            price = price_info.get('total', 'N/A')
            currency = price_info.get('currency', '')
            hotel_info = f"- Nombre: {hotel.get('name', 'Nombre no disponible')}, Precio aprox: {price} {currency}."
            formatted_hotels.append(hotel_info)

        return "\n".join(formatted_hotels)
    except ResponseError as e:
        print(f"Error en la API de Amadeus: {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."

# --- Definición del Modelo de Petición ---


class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None

# --- Endpoint Principal ---


@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    real_hotel_data = search_real_hotels(request.destination)

    budget_info_prompt = f"El presupuesto aproximado para el viaje es de {request.budget} euros. Ten muy en cuenta este presupuesto para todas las recomendaciones." if request.budget and request.budget > 0 else "No se ha especificado un presupuesto, ofrece una mezcla de opciones."

    # --- EL PROMPT MEJORADO Y DETALLADO ---
    prompt = f"""
    **Tu Rol:** Eres un agente de viajes de élite, amigable, extremadamente detallista y servicial. Tu objetivo es crear un itinerario inolvidable.

    **Tarea Principal:** Crea un itinerario detallado de 3 días para un viaje a {request.destination} durante las fechas {request.dates}.

    **Contexto y Datos Reales (¡MUY IMPORTANTE!):**
    He realizado una búsqueda de hoteles disponibles en la zona y he encontrado las siguientes opciones reales. **DEBES** basar tu recomendación de alojamiento en una de estas opciones, justificando tu elección. No inventes hoteles ni precios.
    
    Hoteles Disponibles:
    {real_hotel_data}

    **Instrucciones Específicas:**
    1.  **Estructura:** Organiza el plan día por día (Día 1, Día 2, Día 3). Para cada día,
