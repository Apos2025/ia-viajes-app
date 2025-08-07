import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI()
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


class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None


@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    budget_info_prompt = ""
    if request.budget and request.budget > 0:
        budget_info_prompt = f"El presupuesto aproximado es de {request.budget} euros. Ajusta las recomendaciones a este presupuesto."

    prompt = f"""
    Actúa como un experto en viajes. Crea un itinerario de 3 días para un viaje a {request.destination} 
    durante las fechas {request.dates}. {budget_info_prompt}

    Usa un tono amigable y útil. Estructura el plan día por día con sugerencias de actividades, usando saltos de línea para separar los párrafos.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un planificador de viajes experto."},
                {"role": "user", "content": prompt}
            ]
        )
        itinerary_text = completion.choices[0].message.content
    except openai.APIError as e:
        print(f"Error en la API de OpenAI: {e}")
        return {"error": "Hubo un problema al contactar con la IA."}

    # Simplemente devolvemos el texto del itinerario en un JSON
    return {"itinerary": itinerary_text}
