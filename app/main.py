import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from .utils.transcription import Transcriber
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

app = FastAPI()

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("Llamando a la API Realtime")
    await websocket.accept()
    print("Cliente conectado")
    message_queue = asyncio.Queue()
    print("Lista de mensajes")

    transcriber = Transcriber(message_queue)
    print("Transcriber creado")

    try:
        send_task = asyncio.create_task(send_messages(websocket, message_queue))
        print("Task creada")

        while True:
            # Recibir datos de audio del cliente
            data = await websocket.receive_bytes()
            transcriber.transcribe_audio_chunk(data)
            print("Audio procesado y enviado al transcriptor")
    except WebSocketDisconnect:
        print("Cliente desconectado")
        transcriber.close()
        send_task.cancel()
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
        transcriber.close()
        send_task.cancel()

async def send_messages(websocket: WebSocket, message_queue: asyncio.Queue):
    try:
        while True:
            message = await message_queue.get()
            print(f"Enviando mensaje al cliente: {message}")
            await websocket.send_json(message)
    except Exception as e:
        print(f"Error al enviar mensajes: {e}")
