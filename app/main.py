# main.py
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

# Ajusta los orígenes CORS para tu frontend en React
origins = [
    "http://localhost:3000",
    "https://www.cleverthera.com",
    "https://cleverthera.com",
    # Agrega más si lo requieres
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
    Genera una ephemeral key para usar con la Realtime API de OpenAI.
    """
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",  # Tu API key principal, solo en backend
        "Content-Type": "application/json",
    }

    # Ajusta el modelo y configuración que quieras por defecto
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "modalities": ["audio", "text"],
        "instructions": "Eres un asistente que transcribe audio.",
        "input_audio_format": "pcm16",  # asumiendo que queremos transcribir en PCM16
        "input_audio_transcription": {
            "model": "whisper-1"
        },
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.8,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
            "create_response": False
        },
        "temperature": 0.0,
        "max_response_output_tokens": "inf",
    }

    resp = requests.post(url, headers=headers, json=payload)
    if not resp.ok:
        return {"error": f"OpenAI Realtime error: {resp.text}"}

    return resp.json()  # Retorna el JSON (contiene client_secret y la config de la session)