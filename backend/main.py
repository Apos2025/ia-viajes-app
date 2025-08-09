import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# OpenAI SDK (nuevo)
from openai import OpenAI
from openai import APIStatusError, AuthenticationError, RateLimitError

# Amadeus
from amadeus import Client, ResponseError

load_dotenv()

# --- App ---
app = FastAPI()

# --- CORS ---
origins = [
    "http://localhost:3000",
    "https://ia-viajes-app.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # En Render debes poner la env var en el servicio
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")
client_openai = OpenAI(api_key=OPENAI_API_KEY)

# --- Amadeus ---
AMADEUS_CLIENT_ID = os.getenv(
    "AMADEUS_API_KEY") or os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv(
    "AMADEUS_API_SECRET") or os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = None
try:
    if AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET:
        amadeus = Client(
            client_id=AMADEUS_CLIENT_ID,
            client_secret=AMADEUS_CLIENT_SECRET
        )
    else:
        print(
            "Amadeus: faltan credenciales; la búsqueda real de hoteles estará desactivada.")
except Exception as e:
    print(f"Error al inicializar Amadeus: {e}")
    amadeus = None


# --- Modelos ---
class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None


# --- Helper Hoteles ---
def get_hotel_ids_by_location(latitude: float, longitude: float):
    if not amadeus:
        return []
    try:
        resp = amadeus.reference_data.locations.hotels.by_geocode.get(
            latitude=latitude, longitude=longitude, radius=20, radiusUnit='KM',
            ratings='3,4,5', hotelSource='ALL'
        )
        data = getattr(resp, "data", None) or []
        hotel_ids = [item.get("hotelId") for item in data if isinstance(
            item, dict) and item.get("hotelId")]
        hotel_ids = hotel_ids[:5]
        print(f"IDs de hoteles: {hotel_ids}")
        return hotel_ids
    except ResponseError as e:
        print(f"Amadeus ResponseError (by_geocode): {e}")
        return []
    except Exception as e:
        print(f"Amadeus error inesperado (by_geocode): {e}")
        return []


def search_real_hotels(destination_name: str) -> str:
    if not amadeus:
        return "El servicio de búsqueda de hoteles no está disponible."
    try:
        print(f"Amadeus: buscando ciudad para '{destination_name}'")
        city_search = amadeus.reference_data.locations.get(
            keyword=destination_name, subType='CITY')
        city_data = getattr(city_search, "data", None) or []
        if not city_data:
            return "No se encontró el destino."

        location = city_data[0]
        geo = location.get("geoCode") or {}
        latitude = geo.get("latitude")
        longitude = geo.get("longitude")
        if latitude is None or longitude is None:
            return "No se encontraron coordenadas para el destino."

        print(f"Coordenadas: lat {latitude}, lon {longitude}")
        hotel_ids = get_hotel_ids_by_location(latitude, longitude)
        if not hotel_ids:
            return "No se encontraron hoteles para este destino."

        offers_resp = amadeus.shopping.hotel_offers_by_hotel.get(
            hotelIds=hotel_ids)
        offers_data = getattr(offers_resp, "data", None) or []
        if not offers_data:
            return "No se encontraron ofertas de hotel para este destino."

        formatted = []
        for offer in offers_data[:3]:
            hotel = offer.get("hotel", {}) if isinstance(offer, dict) else {}
            price_info = (offer.get("offers", [{}])[0] or {}).get(
                "price", {}) if isinstance(offer, dict) else {}
            price = price_info.get("total", "N/D")
            currency = price_info.get("currency", "")
            name = hotel.get("name", "Nombre no disponible")
            formatted.append(
                f"- Nombre: {name}, Precio aprox: {price} {currency}.")
        return "\n".join(formatted) if formatted else "No se encontraron ofertas de hotel para este destino."

    except ResponseError as e:
        print(f"Amadeus ResponseError (search): {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."
    except Exception as e:
        print(f"Amadeus error inesperado (search): {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."


# --- Endpoint ---
@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    print(f"generate_trip: {request}")
    real_hotel_data = search_real_hotels(request.destination)

    budget_info_prompt = (
        f"El presupuesto aproximado para el viaje es de {request.budget} euros. Ten muy en cuenta este presupuesto."
        if (request.budget and request.budget > 0) else
        "No se ha especificado presupuesto; ofrece una mezcla de opciones."
    )

    prompt = f"""
Eres un agente de viajes experto y muy práctico.
Crea un itinerario de 3 días para {request.destination} durante {request.dates}.
{budget_info_prompt}

Datos REALES de hoteles (elige 1 y justifica):
{real_hotel_data}

Formato:
- Día 1 (mañana/tarde/noche)
- Día 2 (mañana/tarde/noche)
- Día 3 (mañana/tarde/noche)
Usa **negritas** para lugares clave. Evita inventar precios exactos; da rangos razonables.
"""

    try:
        completion = client_openai.chat.completions.create(
            model="gpt-4o-mini",   # puedes usar "gpt-4o" si tu cuenta lo permite
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        itinerary_text = completion.choices[0].message.content
        return {"itinerary": itinerary_text}

    except AuthenticationError as e:
        # Clave inválida o ausente
        print(f"OpenAI AuthenticationError: {e}")
        raise HTTPException(
            status_code=401, detail="Error de autenticación con OpenAI.")

    except RateLimitError as e:
        print(f"OpenAI RateLimitError: {e}")
        raise HTTPException(
            status_code=429, detail="Límite de uso de OpenAI alcanzado.")

    except APIStatusError as e:
        # Errores HTTP de la API (p.ej., 400/404/500 específicos)
        print(f"OpenAI APIStatusError: {e}")
        raise HTTPException(status_code=502, detail=f"Error de OpenAI: {e}")

    except Exception as e:
        # Cualquier otro error → no dejar que se convierta en 500 silencioso
        print(f"OpenAI error inesperado: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502, detail=f"Error de OpenAI: {type(e).__name__}")
