# transcription.py
import asyncio
from google.cloud import speech_v1p1beta1 as speech
import threading
import queue
import traceback
import google.api_core.exceptions
import time

# Mapeo de canales a hablantes
speaker_mapping = {
    1: "Psicólogo",  # Canal izquierdo
    2: "Paciente"    # Canal derecho
}

class Transcriber:
    def __init__(self, message_queue: asyncio.Queue, credentials):
        self.credentials = credentials
        self.message_queue = message_queue
        self.is_active = True
        self.loop = asyncio.get_event_loop()
        self.audio_queue = queue.Queue()
        threading.Thread(target=self._start_streaming, daemon=True).start()

    def _start_streaming(self):
        while self.is_active:
            try:
                self._streaming_recognize()
            except Exception as e:
                print(f"Error en _streaming_recognize: {e}")
                traceback.print_exc()
                # Esperar antes de reiniciar el stream
                time.sleep(1)

    def _streaming_recognize(self):
        client = speech.SpeechClient(credentials=self.credentials)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code='es-ES',
            audio_channel_count=2,
            enable_separate_recognition_per_channel=True
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )

        def generator():
            start_time = time.time()
            while self.is_active:
                if time.time() - start_time > 200:
                    # Reiniciar el stream antes de los 300 segundos
                    break
                data = self.audio_queue.get()
                if data is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=data)

        requests = generator()
        responses = client.streaming_recognize(streaming_config=streaming_config, requests=requests)

        # Procesar las respuestas en un hilo separado
        threading.Thread(target=self._process_responses, args=(responses,), daemon=True).start()

    def _process_responses(self, responses):
        try:
            for response in responses:
                for result in response.results:
                    if result.is_final:
                        # Procesar resultado final
                        for alternative in result.alternatives:
                            transcript = alternative.transcript.strip()
                            channel_tag = result.channel_tag
                            speaker = speaker_mapping.get(channel_tag, f"Canal {channel_tag}")
                            message = f"{speaker}: {transcript}"
                            # Enviar el mensaje a la cola asíncrona
                            asyncio.run_coroutine_threadsafe(self.message_queue.put(message), self.loop)
        except Exception as e:
            print(f"Error al procesar respuestas: {e}")
            traceback.print_exc()

    def add_audio_data(self, audio_chunk):
        self.audio_queue.put(audio_chunk)

    def close(self):
        self.is_active = False
        # Poner None en la cola para finalizar el generador
        self.audio_queue.put(None)
