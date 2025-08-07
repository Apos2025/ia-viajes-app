# backend/main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # IMPORTAMOS CORS
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
from fpdf import FPDF
import time

load_dotenv()

client = openai.OpenAI()
app = FastAPI()

# --- CONFIGURACIÓN DE CORS ---
# Orígenes permitidos (en nuestro caso, la app de React)
origins = [
    "http://localhost:3000",
    "https://ia-viajes-app.vercel.app",  # <-- Así debe quedar
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permitimos todos los métodos (GET, POST, etc)
    allow_headers=["*"],  # Permitimos todas las cabeceras
)
# --- FIN DE LA CONFIGURACIÓN DE CORS ---


if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# El resto del código que ya teníamos...


def create_pdf_itinerary(itinerary_text: str, destination: str) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(
        200, 10, txt=f"Tu Itinerario de Viaje para {destination.title()}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.write(5, itinerary_text)
    timestamp = int(time.time())
    file_path = f"static/itinerary_{timestamp}.pdf"
    pdf.output(file_path)
    return file_path


class TripRequest(BaseModel):
    destination: str
    dates: str
    budget: float | None = None


@app.post("/api/generate-trip")
def generate_trip(request: TripRequest):
    budget_info_prompt = ""
    if request.budget and request.budget > 0:
        budget_info_prompt = f"El presupuesto aproximado es de {request.budget} euros. Ajusta las recomendaciones a este presupuesto."
    prompt = f"Crea un itinerario de 3 días para un viaje a {request.destination} en las fechas {request.dates}. {budget_info_prompt}..."

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        itinerary = completion.choices[0].message.content
    except openai.APIError as e:
        return {"error": "Hubo un problema al contactar con la IA."}

    pdf_path = create_pdf_itinerary(itinerary, request.destination)
    base_url = "http://127.0.0.1:8000/"
    download_url = f"{base_url}{pdf_path}"
    return {"download_url": download_url}
