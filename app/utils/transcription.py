import asyncio
import websockets
import json
import base64
import time
from pydub import AudioSegment
import io

REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

class Transcriber:
    def __init__(self, message_queue: asyncio.Queue, openai_api_key: str):
        self.message_queue = message_queue
        self.openai_api_key = openai_api_key
        self.is_active = True
        self.audio_queue = asyncio.Queue()
        self.websocket = None

    async def start(self):
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            async with websockets.connect(REALTIME_API_URL, extra_headers=headers) as websocket:
                self.websocket = websocket
                await self._initialize_session()
                await asyncio.gather(
                    self._send_audio(),
                    self._receive_events()
                )
        except Exception as e:
            print(f"Error al conectar con la API Realtime: {e}")
            self.is_active = False

    async def _initialize_session(self):
        session_update_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": "Transcribe el audio del usuario en texto.",
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tool_choice": "auto",
                "temperature": 0.8,  # Ajustado según los requisitos de la API
                "max_response_output_tokens": "inf"
            }
        }
        await self.websocket.send(json.dumps(session_update_event))

    async def _send_audio(self):
        while self.is_active:
            audio_chunk = await self.audio_queue.get()
            if audio_chunk is None:
                break

            audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')

            audio_event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            try:
                await self.websocket.send(json.dumps(audio_event))
            except Exception as e:
                print(f"Error al enviar audio: {e}")
                break

    async def _receive_events(self):
        try:
            async for message in self.websocket:
                event = json.loads(message)
                await self._handle_event(event)
        except websockets.ConnectionClosed:
            print("Conexión cerrada.")
            self.is_active = False
        except Exception as e:
            print(f"Error al recibir eventos: {e}")
            self.is_active = False

    async def _handle_event(self, event):
        event_type = event.get("type")
        if event_type == "conversation.item.created":
            item = event.get("item", {})
            if item.get("type") == "message" and item.get("role") == "user":
                content = item.get("content", [])
                for part in content:
                    if part.get("type") == "input_audio":
                        transcript = part.get("transcript", "")
                        if transcript:
                            message = {
                                "speaker": "Usuario",
                                "text": transcript,
                                "timestamp": time.time()
                            }
                            await self.message_queue.put(message)
        elif event_type == "error":
            error = event.get("error", {})
            print(f"Error: {error.get('message')}")

    async def transcribe_audio_chunk(self, audio_chunk: bytes):
        if self.is_active:
            pcm_audio = await self._convert_audio_to_pcm(audio_chunk)
            if pcm_audio:
                await self.audio_queue.put(pcm_audio)
            else:
                print("Error al convertir el audio al formato PCM requerido.")

    async def _convert_audio_to_pcm(self, audio_chunk: bytes):
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_chunk), format="webm")
            pcm_audio = audio.set_frame_rate(24000).set_sample_width(2).set_channels(1).raw_data
            return pcm_audio
        except Exception as e:
            print(f"Error al convertir el audio: {e}")
            return None

    async def close(self):
        self.is_active = False
        await self.audio_queue.put(None)
