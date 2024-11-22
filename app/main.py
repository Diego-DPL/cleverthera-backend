import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .utils.transcription import Transcriber

load_dotenv()

# Cargar la clave de API de OpenAI desde la variable de entorno
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("No se encontró la variable de entorno OPENAI_API_KEY o está vacía")

app = FastAPI()

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("Llamando a la API de OpenAI")
    await websocket.accept()
    message_queue = asyncio.Queue()
    print("Lista de mensajes")
    transcriber = Transcriber(message_queue, openai_api_key)
    print("Transcriber creado")

    try:
        send_task = asyncio.create_task(send_messages(websocket, message_queue))
        print("Task creada")

        while True:
            data = await websocket.receive_bytes()
            await transcriber.transcribe_audio_chunk(data)
            print("Enviando datos al cliente")
    except WebSocketDisconnect:
        print("Cliente desconectado")
        await transcriber.close()
        send_task.cancel()
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
        await transcriber.close()
        send_task.cancel()

async def send_messages(websocket: WebSocket, message_queue: asyncio.Queue):
    try:
        while True:
            message = await message_queue.get()
            print(f"Enviando mensaje al cliente: {message}")
            await websocket.send_json(message)
    except Exception as e:
        print(f"Error al enviar mensajes: {e}")
