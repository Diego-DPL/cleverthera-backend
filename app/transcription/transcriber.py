import asyncio
import subprocess
import time
import whisper

from pydub import AudioSegment
import io

class Transcriber:
    def __init__(self, message_queue: asyncio.Queue):
        self.message_queue = message_queue
        self.is_active = True

        # Proceso de FFmpeg
        self.ffmpeg_process = None

        # Buffer donde almacenamos los bytes PCM “crudos” que salen de FFmpeg
        self.pcm_buffer = bytearray()

        # Cargamos el modelo Whisper (puedes cambiar a "small", "medium", etc.)
        self.model = whisper.load_model("base")

    async def start(self):
        """
        Inicia el pipeline de FFmpeg y lanza la tarea de lectura de stdout,
        además de la tarea de transcripción periódica.
        """
        print("Transcriber iniciado. Arrancando FFmpeg...")

        # Arrancamos el proceso FFmpeg
        # Ajusta la ruta de 'ffmpeg' si fuera necesario en tu entorno.
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",  # menos spam en logs
            "-f", "webm",          # formato de entrada
            "-i", "pipe:0",        # leemos de stdin
            "-ac", "1",            # 1 canal
            "-ar", "16000",        # 16 kHz
            "-f", "s16le",         # salida en PCM 16 bits LE
            "pipe:1"               # escribimos a stdout
        ]
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Lanza tareas asíncronas:
        # 1) Lectura de stdout de FFmpeg en bucle
        asyncio.create_task(self._read_ffmpeg_stdout())
        # 2) Transcripción periódica
        asyncio.create_task(self._transcription_loop())

    async def _read_ffmpeg_stdout(self):
        """
        Lee continuamente de stdout de FFmpeg y acumula
        los bytes PCM en self.pcm_buffer.
        """
        if not self.ffmpeg_process or not self.ffmpeg_process.stdout:
            print("FFmpeg no está inicializado correctamente.")
            return

        while self.is_active:
            try:
                # Leemos 1024 bytes cada vez (ajusta el tamaño si lo deseas)
                chunk = await asyncio.to_thread(self.ffmpeg_process.stdout.read, 1024)
                if not chunk:
                    # Si chunk es vacío, FFmpeg pudo haber terminado
                    break

                # Acumulamos en el buffer
                self.pcm_buffer.extend(chunk)

            except Exception as e:
                print(f"Error leyendo stdout de FFmpeg: {e}")
                break

        print("Finalizando bucle de lectura de stdout de FFmpeg.")

    async def _transcription_loop(self, interval=3):
        """
        Cada 'interval' segundos, toma todo lo que haya en pcm_buffer,
        lo transcribe con Whisper y envía la transcripción por la cola.
        """
        while self.is_active:
            try:
                await asyncio.sleep(interval)

                # Tomamos una copia de lo que hay en el buffer y lo limpiamos
                pcm_data = self._pop_pcm_buffer()
                if not pcm_data:
                    continue  # no hay nada nuevo

                # Convertimos esos bytes PCM a un WAV en memoria usando pydub (opcional).
                audio_segment = AudioSegment(
                    pcm_data,
                    sample_width=2,   # 16 bits = 2 bytes
                    frame_rate=16000,
                    channels=1
                )
                wav_bytes = audio_segment.export(format="wav").read()

                # Llamamos a Whisper
                result = self.model.transcribe(io.BytesIO(wav_bytes), fp16=False)
                transcription = result.get("text", "").strip()

                if transcription:
                    message = {
                        "speaker": "Usuario",
                        "text": transcription,
                        "timestamp": time.time(),
                    }
                    await self.message_queue.put(message)
                    print(f"Transcripción: {transcription}")

            except asyncio.CancelledError:
                # Se cancela cuando se cierra el WebSocket
                break
            except Exception as e:
                print(f"Error en _transcription_loop: {e}")
                break

        print("Finalizando bucle de transcripción.")

    def write_chunk(self, data: bytes):
        """
        Escribe el chunk WebM/Opus recibido al stdin de FFmpeg.
        """
        if self.ffmpeg_process and self.ffmpeg_process.stdin:
            try:
                self.ffmpeg_process.stdin.write(data)
                self.ffmpeg_process.stdin.flush()
            except Exception as e:
                print(f"Error escribiendo chunk a FFmpeg: {e}")

    def _pop_pcm_buffer(self) -> bytes:
        """
        Toma todo lo que hay en self.pcm_buffer y lo retorna,
        dejando self.pcm_buffer vacío.
        """
        data = bytes(self.pcm_buffer)
        self.pcm_buffer.clear()
        return data

    async def close(self):
        """
        Detiene la transcripción y el proceso FFmpeg.
        """
        self.is_active = False
        if self.ffmpeg_process:
            try:
                # Cerramos stdin para que FFmpeg “sepa” que no vendrán más datos
                self.ffmpeg_process.stdin.close()
            except Exception as e:
                print(f"Error cerrando stdin de FFmpeg: {e}")

            await asyncio.sleep(0.5)  # pequeña espera
            self.ffmpeg_process.terminate()

            try:
                self.ffmpeg_process.wait(timeout=1)
            except Exception:
                pass

            self.ffmpeg_process = None

        print("Transcriber cerrado y FFmpeg detenido.")