import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
from amadeus import Client, ResponseError  # Importamos el cliente de Amadeus

load_dotenv()

# --- Configuración de Clientes y la App ---
client_openai = openai.OpenAI()
app = FastAPI()

# --- NUEVA CONFIGURACIÓN PARA AMADEUS ---
try:
    amadeus = Client(
        client_id=os.getenv("AMADEUS_API_KEY"),
        client_secret=os.getenv("AMADEUS_API_SECRET")
    )
except Exception as e:
    print(f"Error al inicializar el cliente de Amadeus: {e}")
    amadeus = None

# ... la configuración de CORS sigue igual ...
origins = ["http://localhost:3000", "https://ia-viajes-app.vercel.app"]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# --- NUEVA FUNCIÓN DE BÚSQUEDA CON AMADEUS ---
def search_real_hotels(destination_name: str):
    if not amadeus:
        return "El servicio de búsqueda de hoteles no está disponible."

    try:
        print(f"Buscando hoteles en Amadeus para: {destination_name}")
        # 1. Amadeus necesita un código de ciudad IATA (ej: 'MAD' para Madrid). Lo buscamos primero.
        city_search = amadeus.reference_data.locations.get(
            keyword=destination_name,
            subType='CITY'
        )
        if not city_search.data:
            return "No se encontró el destino."

        city_code = city_search.data[0]['iataCode']
        print(f"Código de ciudad encontrado: {city_code}")

        # 2. Ahora buscamos ofertas de hotel en esa ciudad.
        hotel_offers = amadeus.shopping.hotel_offers.get(
            cityCode=city_code,
            radius=20,
            radiusUnit='KM',
            ratings='3,4,5',  # Buscamos hoteles de 3, 4 y 5 estrellas
            view='LIGHT',  # Pedimos una vista ligera para no gastar mucha cuota
            bestRateOnly=True
        )

        if not hotel_offers.data:
            return "No se encontraron ofertas de hotel para este destino."

        # 3. Formateamos la respuesta para la IA
        formatted_hotels = []
        # Tomamos hasta 3 hoteles como máximo
        for offer in hotel_offers.data[:3]:
            hotel = offer['hotel']
            price = offer['offers'][0]['price']['total']
            hotel_info = f"- Nombre: {hotel['name']}, Valoración: {hotel.get('rating', 'N/A')} estrellas, Precio aprox: {price} {offer['offers'][0]['price']['currency']}."
            formatted_hotels.append(hotel_info)

        return "\n".join(formatted_hotels)

    except ResponseError as e:
        print(f"Error en la API de Amadeus: {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."


class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None


# Dentro de la función generate_trip en main.py

@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    real_hotel_data = search_real_hotels(request.destination)

    budget_info_prompt = ""
    if request.budget and request.budget > 0:
        budget_info_prompt = f"El presupuesto aproximado para el viaje es de {request.budget} euros. Ten muy en cuenta este presupuesto para todas las recomendaciones."

    # --- ESTE ES EL NUEVO PROMPT MEJORADO ---
    prompt = f"""
    **Tu Rol:** Eres un agente de viajes de élite, amigable, extremadamente detallista y servicial. Tu objetivo es crear un itinerario inolvidable.

    **Tarea Principal:** Crea un itinerario detallado de 3 días para un viaje a {request.destination} durante las fechas {request.dates}.

    **Contexto y Datos Reales (¡MUY IMPORTANTE!):**
    He realizado una búsqueda de hoteles disponibles en la zona y he encontrado las siguientes opciones reales. **DEBES** basar tu recomendación de alojamiento en una de estas opciones, justificando tu elección. No inventes hoteles ni precios.

    Hoteles Disponibles:
    {real_hotel_data}

    **Instrucciones Específicas:**
    1.  **Estructura:** Organiza el plan día por día (Día 1, Día 2, Día 3). Para cada día, detalla sugerencias para la mañana, tarde y noche.
    2.  **Alojamiento:** En el "Día 1", recomienda explícitamente **uno** de los hoteles de la lista proporcionada. Justifica por qué es una buena opción (ej: "Te recomiendo alojarte en el 'Hotel X' por su buena valoración y precio...").
    3.  **Presupuesto:** {budget_info_prompt if budget_info_prompt else "No se ha especificado un presupuesto, ofrece una mezcla de opciones."}
    4.  **Tono:** Mantén un tono entusiasta y práctico.
    5.  **Formato:** Usa saltos de línea para que sea fácil de leer. Usa negritas para resaltar lugares o actividades clave.
    """

    try:
        # ... el resto de la función sigue igual ...
        completion = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        itinerary_text = completion.choices[0].message.content
    except openai.APIError as e:
        return {"error": "Hubo un problema al contactar con la IA."}

    return {"itinerary": itinerary_text}
