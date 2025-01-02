import os
import json
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# main.py
from .transcription.transcriber import Transcriber

load_dotenv()

app = FastAPI()

# Configurar CORS si tu front está en localhost:3000 o en otro dominio.
origins = [
    "http://localhost:3000",
    "https://www.cleverthera.com",
    "https://cleverthera.com"   # Ajusta con el dominio donde esté tu front en producción
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

    message_queue = asyncio.Queue()
    transcriber = Transcriber(message_queue)  # No necesitamos la API Key

    try:
        # Crear tarea que maneja la transcripción con Whisper
        transcriber_task = asyncio.create_task(transcriber.start())

        # Tareas de recepción y envío:
        receive_task = asyncio.create_task(receive_audio(websocket, transcriber))
        send_task = asyncio.create_task(send_transcriptions(websocket, message_queue))

        await asyncio.gather(transcriber_task, receive_task, send_task)

    except WebSocketDisconnect:
        print("WebSocket desconectado: el cliente cerró la conexión.")
        await transcriber.close()

    except Exception as e:
        print(f"Error en websocket_endpoint: {e}")
        await transcriber.close()
        await websocket.close()


async def receive_audio(websocket: WebSocket, transcriber: Transcriber):
    while True:
        try:
            audio_chunk = await websocket.receive_bytes()
            print(f"Chunk recibido: {len(audio_chunk)} bytes")
            await transcriber.transcribe_audio_chunk(audio_chunk)
        except WebSocketDisconnect:
            print("WebSocket desconectado en receive_audio()")
            break
        except Exception as e:
            print(f"Error al recibir audio: {e}")
            break

async def send_transcriptions(websocket: WebSocket, message_queue: asyncio.Queue):
    while True:
        try:
            message = await message_queue.get()
            await websocket.send_json(message)
        except WebSocketDisconnect:
            print("WebSocketDisconnect en send_transcriptions()")
            break
        except Exception as e:
            print(f"Error al enviar transcripción: {e}")
            break