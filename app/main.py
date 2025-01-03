import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# IMPORTAMOS NUESTRO NUEVO TRANSCRIBER
from .transcription.transcriber import Transcriber

load_dotenv()

app = FastAPI()

# Configurar CORS
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

    message_queue = asyncio.Queue()
    transcriber = Transcriber(message_queue)

    try:
        # Iniciamos nuestro Transcriber
        await transcriber.start()

        # Tareas asíncronas para:
        # 1) Recibir datos del WebSocket
        receive_task = asyncio.create_task(receive_audio(websocket, transcriber))
        # 2) Enviar transcripciones al cliente
        send_task = asyncio.create_task(send_transcriptions(websocket, message_queue))

        await asyncio.gather(receive_task, send_task)

    except WebSocketDisconnect:
        print("WebSocket desconectado.")
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

            # En lugar de transcribir chunk a chunk,
            # simplemente se lo pasamos a FFmpeg:
            transcriber.write_chunk(audio_chunk)

        except WebSocketDisconnect:
            print("WebSocket desconectado en receive_audio().")
            break
        except Exception as e:
            print(f"Error al recibir audio: {e}")
            break

async def send_transcriptions(websocket: WebSocket, message_queue: asyncio.Queue):
    while True:
        try:
            # Esperamos un mensaje de la cola (saldrá del _transcription_loop)
            message = await message_queue.get()
            await websocket.send_json(message)
            print(f"Transcripción enviada: {message}")
        except WebSocketDisconnect:
            print("WebSocket desconectado en send_transcriptions().")
            break
        except Exception as e:
            print(f"Error al enviar transcripción: {e}")
            break