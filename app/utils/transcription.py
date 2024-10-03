import asyncio
from google.cloud import speech_v1p1beta1 as speech
import threading
import queue
import traceback

# Mapeo de canales a hablantes
speaker_mapping = {
    1: "Psicólogo",  # Canal izquierdo
    2: "Paciente"    # Canal derecho
}

class Transcriber:
    def __init__(self, message_queue: asyncio.Queue):
        self.client = speech.SpeechClient()
        self.requests_queue = queue.Queue()
        self.message_queue = message_queue
        self.is_active = True
        self.loop = asyncio.get_event_loop()
        threading.Thread(target=self._start_streaming, daemon=True).start()

    def _start_streaming(self):
        self._streaming_recognize()

    def _streaming_recognize(self):
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

        # Generador de solicitudes síncrono
        def request_generator():
            while self.is_active:
                audio_content = self.requests_queue.get()
                if audio_content is None:
                    break
                print("Enviando fragmento de audio a la API de Speech-to-Text")
                yield speech.StreamingRecognizeRequest(audio_content=audio_content)

        # Procesar las respuestas
        try:
            requests = request_generator()
            responses = self.client.streaming_recognize(streaming_config, requests)

            for response in responses:
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

    def transcribe_audio_chunk(self, audio_chunk: bytes):
        print(f"Received audio chunk of size {len(audio_chunk)} bytes")
        self.requests_queue.put(audio_chunk)

    def close(self):
        self.is_active = False
        self.requests_queue.put(None)
