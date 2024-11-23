import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from .utils.transcription import Transcriber

load_dotenv()

app = FastAPI()

# Cargar la clave de la API de OpenAI desde las variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("La clave de la API de OpenAI no está configurada en las variables de entorno.")

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("Llamando a la API de OpenAI Realtime")
    await websocket.accept()
    print("Cliente conectado")
    
    message_queue = asyncio.Queue()
    transcriber = Transcriber(message_queue, OPENAI_API_KEY)
    print("Transcriber creado")

    try:
        # Iniciar la conexión con la API de Realtime
        transcriber_task = asyncio.create_task(transcriber.start())
        print("Transcriber iniciado")
        
        # Tareas de envío y recepción de audio
        receive_task = asyncio.create_task(receive_audio(websocket, transcriber))
        send_task = asyncio.create_task(send_transcriptions(websocket, message_queue))

        await asyncio.gather(transcriber_task, receive_task, send_task)
    except WebSocketDisconnect:
        print("Cliente desconectado")
        await transcriber.close()
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
        await transcriber.close()

async def receive_audio(websocket: WebSocket, transcriber: Transcriber):
    while True:
        try:
            audio_chunk = await websocket.receive_bytes()
            await transcriber.transcribe_audio_chunk(audio_chunk)
        except WebSocketDisconnect:
            print("WebSocket desconectado")
            break
        except Exception as e:
            print(f"Error al recibir audio del cliente: {e}")
            break

async def send_transcriptions(websocket: WebSocket, message_queue: asyncio.Queue):
    try:
        while True:
            message = await message_queue.get()
            print(f"Enviando transcripción al cliente: {message}")
            await websocket.send_json(message)
    except WebSocketDisconnect:
        print("WebSocket desconectado al enviar mensajes")
