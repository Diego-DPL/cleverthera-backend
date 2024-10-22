import os
import json
from google.oauth2 import service_account
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .utils.transcription import Transcriber

load_dotenv()

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# En producción, cargar las credenciales desde la variable de entorno JSON
if os.getenv("ENV") == "production":  # Configura esta variable de entorno en Heroku
    if credentials_path:
        # Heroku almacena el JSON completo de las credenciales en una variable de entorno
        try:
            credentials_info = json.loads(credentials_path)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
        except json.JSONDecodeError:
            raise ValueError("Las credenciales de Google no están en un formato JSON válido.")
    else:
        raise ValueError("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS en Heroku")
else:
    # En local, cargar desde un archivo
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
    else:
        raise ValueError("No se encontró el archivo de credenciales local o la variable de entorno")

app = FastAPI()

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("llamando a la API")
    await websocket.accept()
    message_queue = asyncio.Queue()
    transcriber = Transcriber(message_queue)
    try:
        send_task = asyncio.create_task(send_messages(websocket, message_queue))
        while True:
            data = await websocket.receive_bytes()
            transcriber.transcribe_audio_chunk(data)
            print("enviando datos al cliente")
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
            await websocket.send_json(message)
    except Exception as e:
        print(f"Error al enviar mensajes: {e}")
