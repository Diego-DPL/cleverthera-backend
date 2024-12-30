# archivo: main.py (o app.py)
import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Falta la clave de la API de OpenAI en .env")

app = FastAPI()

# Ajusta los orígenes CORS a tu frontend en React
origins = [
    "http://localhost:3000",
    "https://www.cleverthera.com",
    "https://cleverthera.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/session")
def create_ephemeral_session():
    """
    Genera una ephemeral key llamando a la API Realtime de OpenAI.
    Devuelve la respuesta JSON al frontend.
    """
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",  # Tu API key principal (server-side)
        "Content-Type": "application/json",
    }

    # Ajusta el modelo al que quieras conectarte (por ej: gpt-4o-realtime-preview-2024-12-17)
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17"
        # "voice": "verse", # Ejemplo si quisieras TTS, etc.
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200 and resp.status_code != 201:
        return {"error": f"OpenAI Realtime error: {resp.text}"}

    return resp.json()  # el JSON contiene { client_secret: { value: ..., expires_at: ...}, ...}