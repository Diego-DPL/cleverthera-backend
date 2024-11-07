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
        threading.Thread(target=self._start_streaming, daemon=True).start()

    def _start_streaming(self):
        while self.is_active:
            self._streaming_recognize()
            # Agregar un breve retraso para evitar bucles rápidos en caso de error
            time.sleep(1)

    def _streaming_recognize(self):
        client = speech.SpeechClient(credentials=self.credentials)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code='es-ES',
            audio_channel_count=2,
            enable_separate_recognition_per_channel=True,
            enable_speaker_diarization=False,
            enable_automatic_punctuation=True,
            model='default',
            use_enhanced=True
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=False,
            single_utterance=False,
        )

        # Crear una nueva cola para esta sesión
        self.requests_queue = queue.Queue()

        def request_generator():
            # Enviar el streaming_config en la primera solicitud
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            try:
                while self.is_active:
                    audio_content = self.requests_queue.get()
                    if audio_content is None:
                        break
                    print("Enviando fragmento de audio a la API de Speech-to-Text")
                    yield speech.StreamingRecognizeRequest(audio_content=audio_content)
            except Exception as e:
                print(f"Error en request_generator: {e}")

        try:
            requests = request_generator()
            # No pasar streaming_config como argumento
            responses = client.streaming_recognize(requests)

            # Iniciar el temporizador
            start_time = time.time()

            for response in responses:
                # Verificar si han transcurrido 200 segundos
                if time.time() - start_time > 200:
                    print("Tiempo límite alcanzado, reiniciando el streaming.")
                    # Detener el generador y salir del bucle
                    self.requests_queue.put(None)
                    break

                for result in response.results:
                    if result.is_final:
                        alternative = result.alternatives[0]
                        channel_tag = result.channel_tag  # Obtener el canal

                        # Obtener el tiempo de finalización del resultado
                        result_end_time = result.result_end_time
                        # Convertir a segundos
                        timestamp = result_end_time.total_seconds()

                        # Asignar el nombre del hablante según el canal
                        speaker_name = speaker_mapping.get(channel_tag, f"Hablante Canal {channel_tag}")
                        transcript = alternative.transcript.strip()

                        message = {
                            "speaker": speaker_name,
                            "text": transcript,
                            "timestamp": timestamp
                        }
                        # Añadir el mensaje a la cola asíncrona
                        asyncio.run_coroutine_threadsafe(
                            self.message_queue.put(message), self.loop
                        )
        except Exception as e:
            print(f"Error en _streaming_recognize: {e}")
            traceback.print_exc()
            # Salir del método para que _start_streaming() lo reinicie
            return

    def transcribe_audio_chunk(self, audio_chunk: bytes):
        print(f"Received audio chunk of size {len(audio_chunk)} bytes")
        if self.is_active:
            try:
                self.requests_queue.put(audio_chunk)
            except Exception as e:
                print(f"Error al agregar fragmento de audio a la cola: {e}")

    def close(self):
        self.is_active = False
        # Poner None en la cola para finalizar el generador
        self.requests_queue.put(None)
