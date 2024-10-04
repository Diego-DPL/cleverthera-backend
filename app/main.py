from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from utils.transcription import Transcriber
import asyncio
import os
import json
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

# Cargar las credenciales de Google Cloud desde una variable de entorno
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if credentials_json:
    # Convertir el string JSON a un objeto de credenciales
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
else:
    raise ValueError("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS")

# Cargar las credenciales de Google Cloud desde un archivo .env
#from dotenv import load_dotenv
#load_dotenv()
#import os
#print("GOOGLE_APPLICATION_CREDENTIALS:", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
#eliminar credentials=credentials de la función websocket_endpoint


app = FastAPI()

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket, credentials=credentials):
    await websocket.accept()
    message_queue = asyncio.Queue()
    transcriber = Transcriber(message_queue)
    try:
        send_task = asyncio.create_task(send_messages(websocket, message_queue))
        while True:
            data = await websocket.receive_bytes()
            transcriber.transcribe_audio_chunk(data)
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
