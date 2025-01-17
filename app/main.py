import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .transcription.transcriber import Transcriber

load_dotenv()

app = FastAPI()

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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("La clave de la API de OpenAI no está configurada en las variables de entorno (.env).")

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Cliente conectado al endpoint /ws/audio")

    transcriber = Transcriber()

    try:
        # Inicia grabación de audio
        transcriber.start_recording()

        while True:
            audio_chunk = await websocket.receive_bytes()
            transcriber.write_chunk(audio_chunk)

    except WebSocketDisconnect:
        print("WebSocket desconectado.")
        # Transcribir el archivo completo al finalizar
        transcription = transcriber.stop_and_transcribe()
        await websocket.send_json({"transcription": transcription})
        await websocket.close()

    except Exception as e:
        print(f"Error en websocket_endpoint: {e}")
        await websocket.close()
        transcriber.stop_recording()
