import os
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from openai import OpenAI
from amadeus import Client, ResponseError

load_dotenv()

BUILD_TAG = "v2-cityCode-days-2025-08-10"
print(f"[BOOT] backend starting… {BUILD_TAG}")

app = FastAPI()

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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")
client_openai = OpenAI(api_key=OPENAI_API_KEY)

AMADEUS_CLIENT_ID = os.getenv(
    "AMADEUS_API_KEY") or os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv(
    "AMADEUS_API_SECRET") or os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = None
try:
    if AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET:
        amadeus = Client(client_id=AMADEUS_CLIENT_ID,
                         client_secret=AMADEUS_CLIENT_SECRET)
        print("[BOOT] Amadeus client OK")
    else:
        print("[BOOT] Amadeus desactivado (faltan credenciales)")
except Exception as e:
    print(f"[BOOT] Error al inicializar Amadeus: {e}")
    amadeus = None


class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None


def extract_dates(text: str):
    iso = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if len(iso) >= 2:
        return iso[0], iso[1]
    dmy = re.findall(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', text)

    def to_iso(d):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None
    if len(dmy) >= 2:
        c1, c2 = to_iso(dmy[0]), to_iso(dmy[1])
        if c1 and c2:
            return c1, c2
    return None, None


def extract_days(text: str) -> int | None:
    s = text.lower().strip()
    m = re.search(r'\b(\d{1,2})\s*(d[ií]a[s]?|d|days?)\b', s)
    if m:
        try:
            n = int(m.group(1))
            return n if 1 <= n <= 30 else None
        except:
            pass
    if re.search(r'd[ií]a', s) or 'days' in s:
        m2 = re.search(r'\b(\d{1,2})\b', s)
        if m2:
            try:
                n = int(m2.group(1))
                return n if 1 <= n <= 30 else None
            except:
                pass
    return None


def search_real_hotels(destination_name: str, dates_text: str) -> str:
    if not amadeus:
        return "El servicio de búsqueda de hoteles no está disponible."
    try:
        print(f"[AMADEUS] ciudad: '{destination_name}'")
        city_search = amadeus.reference_data.locations.get(
            keyword=destination_name, subType='CITY')
        city_data = getattr(city_search, "data", None) or []
        if not city_data:
            return "No se encontró el destino."
        location = city_data[0]
        iata = location.get('iataCode')
        if not iata:
            return "No se encontró código IATA para el destino."
        check_in, check_out = extract_dates(dates_text)
        kwargs = {"cityCode": iata, "adults": 2, "bestRateOnly": True}
        if check_in and check_out:
            kwargs["checkInDate"] = check_in
            kwargs["checkOutDate"] = check_out
        hotel_offers_response = amadeus.shopping.hotel_offers.get(**kwargs)
        offers = getattr(hotel_offers_response, "data", None) or []
        if not offers:
            return "No se encontraron ofertas de hotel para este destino."
        formatted = []
        for offer in offers[:3]:
            if not isinstance(offer, dict):
                continue
            hotel = offer.get('hotel', {}) or {}
            price_info = (offer.get('offers', [{}])[
                          0] or {}).get('price', {}) or {}
            price = price_info.get('total', 'N/A')
            currency = price_info.get('currency', '')
            name = hotel.get('name', 'Nombre no disponible')
            formatted.append(
                f"- Nombre: {name}, Precio aprox: {price} {currency}.")
        return "\n".join(formatted) if formatted else "No se encontraron ofertas de hotel para este destino."
    except ResponseError as e:
        print(f"[AMADEUS] ResponseError: {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."
    except Exception as e:
        print(f"[AMADEUS] Error inesperado: {e}")
        return "Hubo un problema al buscar hoteles en Amadeus."


@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    print(f"[REQ] {request}")
    real_hotel_data = search_real_hotels(request.destination, request.dates)

    check_in, check_out = extract_dates(request.dates)
    days = None
    if check_in and check_out:
        try:
            d1 = datetime.fromisoformat(check_in)
            d2 = datetime.fromisoformat(check_out)
            diff = (d2 - d1).days
            if diff >= 1:
                days = diff
        except Exception:
            pass
    if days is None:
        days = extract_days(request.dates) or 3
    days = max(1, min(days, 30))

    budget_info = (
        f"El presupuesto aproximado es {request.budget} euros. Ajusta recomendaciones a este presupuesto."
        if (request.budget and request.budget > 0) else
        "No hay presupuesto especificado; ofrece una mezcla de opciones."
    )

    prompt = f"""
Eres un agente de viajes experto y práctico.
Crea un itinerario de {days} días para {request.destination} durante {request.dates}.
{budget_info}

Datos REALES de hoteles (elige 1 y justifica):
{real_hotel_data}

Instrucciones:
- Estructura {days} días completos (Día 1 ... Día {days}), con mañana/tarde/noche.
- Usa **negritas** para lugares clave.
- Evita precios exactos; da rangos razonables y consejos prácticos.
Si el rango de fechas no es claro, asume {days} días igualmente.
"""
    try:
        completion = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        itinerary_text = completion.choices[0].message.content
        return {"itinerary": itinerary_text, "days_inferred": days, "build": BUILD_TAG}
    except Exception as e:
        print(f"[OPENAI] {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502, detail=f"Error al contactar con la IA: {type(e).__name__}")


@app.get("/health")
def health():
    return {"ok": True, "build": BUILD_TAG}


@app.get("/version")
def version():
    return {"build": BUILD_TAG}
