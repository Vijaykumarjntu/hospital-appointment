# import torch
# from TTS.api import TTS
# import pyttsx3
import io
import wave
import numpy as np
import soundfile as sf
from typing import Optional
import tempfile 
import os
import base64
import concurrent.futures

class FreeTextToSpeech:
    def __init__(self):
        self.voice_map = {
            'en': 0,
            'hi': 1,
            'ta': 1,
        }

    def synthesize(self, text: str, language: str = "en", speaker: Optional[str] = None) -> bytes:
        def _run_tts():
            import pyttsx3
            engine = pyttsx3.init()  # local, not self.engine
            voices = engine.getProperty('voices')
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)

            voice_idx = self.voice_map.get(language, 0)
            if voice_idx < len(voices):
                engine.setProperty('voice', voices[voice_idx].id)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                output_path = tmp.name

            engine.save_to_file(text, output_path)
            engine.runAndWait()
            engine.stop()

            with open(output_path, 'rb') as f:
                audio_bytes = f.read()
            try:
                os.unlink(output_path)
            except:
                pass

            print(f"✅ TTS completed, generated {len(audio_bytes)} bytes")
            return audio_bytes

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(_run_tts).result(timeout=30)
        except Exception as e:
            print(f"TTS Error: {e}")
            import traceback
            traceback.print_exc()
            return b""

    def synthesize_to_base64(self, text: str, language: str = "en") -> str:
        audio_bytes = self.synthesize(text, language)
        return base64.b64encode(audio_bytes).decode("utf-8")

    def list_speakers(self):
        return self.speakers