import asyncio
import time
import whisper
import io

from pydub import AudioSegment

class Transcriber:
    def __init__(self, message_queue: asyncio.Queue):
        self.message_queue = message_queue
        self.is_active = True
        self.audio_queue = asyncio.Queue()
        self.model = whisper.load_model("base")  # Carga del modelo Whisper

    async def start(self):
        try:
            print("Transcriber iniciado.")
            await self._process_audio()  # Procesar audio en tiempo real
        except Exception as e:
            print(f"Error en Transcriber: {e}")
            self.is_active = False

    async def _process_audio(self):
        while self.is_active:
            audio_chunk = await self.audio_queue.get()
            if audio_chunk is None:
                break

            try:
                # Procesar el chunk con Whisper
                print("Procesando chunk con Whisper...")
                result = self.model.transcribe(audio_chunk, fp16=False)
                transcription = result.get("text", "").strip()

                if transcription:
                    message = {
                        "speaker": "Usuario",
                        "text": transcription,
                        "timestamp": time.time(),
                    }
                    await self.message_queue.put(message)
                    print(f"Transcripción procesada: {transcription}")

            except Exception as e:
                print(f"Error al procesar audio con Whisper: {e}")

    async def transcribe_audio_chunk(self, audio_chunk: bytes):
        if self.is_active:
            # Guarda el chunk en un archivo para depuración
            with open(f"chunk-{time.time()}.webm", "wb") as f:
                f.write(audio_chunk)
            print("Chunk guardado para depuración.")

            pcm_audio = await self._convert_audio_to_pcm(audio_chunk)
            if pcm_audio:
                await self.audio_queue.put(pcm_audio)

    async def _convert_audio_to_pcm(self, audio_chunk: bytes):
        try:
            print("Convirtiendo audio de WebM a PCM...")
            audio = AudioSegment.from_file(io.BytesIO(audio_chunk), format="webm")
            pcm_audio = (
                audio.set_frame_rate(16000)
                    .set_sample_width(2)  # 16 bits
                    .set_channels(1)
                    .raw_data
            )
            print("Conversión completada.")
            return pcm_audio
        except Exception as e:
            print(f"Error al convertir el chunk webm a PCM16: {e}")
            return None

    async def close(self):
        print("Cerrando transcriptor...")
        self.is_active = False
        await self.audio_queue.put(None)