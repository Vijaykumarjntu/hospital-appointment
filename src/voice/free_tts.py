# import torch
# from TTS.api import TTS
import pyttsx3
import io
import wave
import numpy as np
import soundfile as sf
from typing import Optional
import tempfile 
import os
import base64

class FreeTextToSpeech:
    """Open-source Text-to-Speech using Coqui TTS (runs locally, no API)"""
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        # """
        # Initialize Coqui TTS model
        # Common models:
        # - English: "tts_models/en/ljspeech/tacotron2-DDC"
        # - Multi-language: "tts_models/multilingual/multi-dataset/your_tts"
        # - Hindi: "tts_models/hi/fastspeech2/hifigan"
        # - Tamil: "tts_models/ta/fastspeech2/hifigan"
        # """
        # print(f"Loading TTS model: {model_name}...")
        
        # # Check if GPU is available
        # self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # print(f"Using device: {self.device}")
        
        
        """Initialize pyttsx3 engine"""
        print("Initializing pyttsx3 TTS...")
        self.engine = pyttsx3.init()
        
        # Get available voices
        self.voices = self.engine.getProperty('voices')
        
        # Set properties
        self.engine.setProperty('rate', 150)    # Speed of speech
        self.engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)


        # self.tts = TTS(model_name, progress_bar=False).to(self.device)
        # print("✅ TTS model loaded")
        
        # # Available speakers (for multi-speaker models)
        # self.speakers = self.tts.speakers if hasattr(self.tts, 'speakers') else None

          # Language to voice mapping (simplified)
        self.voice_map = {
            'en': 0,  # Default English voice
            'hi': 1,  # Hindi voice (if available)
            'ta': 1,  # Tamil voice (if available)
        }
        
        print(f"✅ TTS initialized with {len(self.voices)} voices")
    
    def synthesize(self, text: str, language: str = "en", speaker: Optional[str] = None) -> bytes:
        """
        Convert text to speech audio bytes
        Returns: WAV audio bytes
        """
        try:
             # Select voice based on language
            voice_idx = self.voice_map.get(language, 0)
            if voice_idx < len(self.voices):
                self.engine.setProperty('voice', self.voices[voice_idx].id)
            
            # Create temp file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                output_path = tmp.name
            
             # Save speech to file
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            # # Generate speech
            # if language == "en":
            #     self.tts.tts_to_file(text=text, file_path=output_path)
            # else:
            #     # For multilingual models
            #     if hasattr(self.tts, 'languages') and language in self.tts.languages:
            #         self.tts.tts_to_file(
            #             text=text, 
            #             file_path=output_path,
            #             language=language,
            #             speaker=speaker if speaker else self.speakers[0] if self.speakers else None
            #         )
            #     else:
            #         # Fallback to English
            #         print(f"Language {language} not supported, falling back to English")
            #         self.tts.tts_to_file(text=text, file_path=output_path)
            
            # Read the generated audio
            with open(output_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Clean up
            os.unlink(output_path)
            
            return audio_bytes
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return b""
    
    def synthesize_to_base64(self, text: str, language: str = "en") -> str:
        """Convert text to speech and return as base64 string"""
        audio_bytes = self.synthesize(text, language)
        return base64.b64encode(audio_bytes).decode("utf-8")
    
    # def list_languages(self):
    #     """List supported languages (for multilingual models)"""
    #     if hasattr(self.tts, 'languages'):
    #         return self.tts.languages
    #     return ["en"]
    
    def list_speakers(self):
        """List available speakers (for multi-speaker models)"""
        return self.speakers