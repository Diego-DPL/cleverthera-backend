import os
import wave
import whisper

class Transcriber:
    def __init__(self):
        self.audio_file = "recording.wav"
        self.model = whisper.load_model("base")
        self.wav_file = None

    def start_recording(self):
        """Inicia la grabación del archivo de audio."""
        self.wav_file = wave.open(self.audio_file, 'wb')
        self.wav_file.setnchannels(1)  # Mono audio
        self.wav_file.setsampwidth(2)  # 16-bit audio
        self.wav_file.setframerate(16000)  # 16 kHz

    def write_chunk(self, chunk):
        """Escribe un fragmento de audio al archivo."""
        if self.wav_file:
            self.wav_file.writeframes(chunk)

    def stop_and_transcribe(self):
        """Finaliza la grabación, transcribe el archivo y lo elimina."""
        if self.wav_file:
            self.wav_file.close()

        # Realiza la transcripción
        result = self.model.transcribe(self.audio_file, language="es")
        transcription = result.get("text", "")

        # Elimina el archivo después de la transcripción
        os.remove(self.audio_file)

        return transcription
