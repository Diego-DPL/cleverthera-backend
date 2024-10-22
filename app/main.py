from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import json
from google.oauth2 import service_account
import os
import json
from google.oauth2 import service_account
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .utils.transcription import Transcriber

load_dotenv()

# Cargar las credenciales de Google Cloud desde una variable de entorno
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

#DESCOMENTAR PARA LOCAL
# Cargar las credenciales de Google Cloud desde una variable de entorno LOCAL
# if credentials_path and os.path.exists(credentials_path):
#     # Cargar las credenciales desde el archivo JSON
#     credentials = service_account.Credentials.from_service_account_file(credentials_path)
# else:
#     raise ValueError("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS o el archivo no existe")

#PRODUCCION
# Cargar las credenciales de Google Cloud desde una variable de entorno en HEROKU
if credentials_path:
    # Convertir el string JSON a un objeto de credenciales
    credentials_info = json.loads(credentials_path)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
else:
    raise ValueError("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS o el archivo no existe")

app = FastAPI()

# Habilitar CORS para permitir solicitudes desde el frontend en Vercel
origins = [
    "https://www.cleverthera.com",  # tu dominio
    "https://cleverthera.com",  # tu dominio
    #"http://localhost",  # Para pruebas locales si es necesario
    #"http://localhost:3000",  # Si estás probando localmente en un puerto específico
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("llamada a la API")
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
