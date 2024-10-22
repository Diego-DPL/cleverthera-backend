import os
import json
from google.oauth2 import service_account
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .utils.transcription import Transcriber
from google.cloud import speech_v1p1beta1 as speech

load_dotenv()

# Cargar las credenciales directamente desde la variable de entorno
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
print(f"Contenido de GOOGLE_APPLICATION_CREDENTIALS: {credentials_json}")

if credentials_json:
    try:
        print("Cargando credenciales de Google desde la variable de entorno")
        # Parsear el JSON de las credenciales
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        print("Credenciales cargadas correctamente")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error en el formato JSON de las credenciales: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error al cargar las credenciales de Google: {str(e)}")
else:
    print("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS o está vacía")
    raise ValueError("No se encontró la variable de entorno GOOGLE_APPLICATION_CREDENTIALS o está vacía")

# Prueba la conexión con Google Speech API
def prueba_conexion_google_speech():
    try:
        client = speech.SpeechClient(credentials=credentials)
        print("Conexión a Google Speech API exitosa.")
    except Exception as e:
        print(f"Error al conectar con Google Speech API: {e}")

prueba_conexion_google_speech()

app = FastAPI()

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    print("Llamando a la API")
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
            data = await websocket.receive_bytes()
            transcriber.transcribe_audio_chunk(data)
            print("Enviando datos al cliente")
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
