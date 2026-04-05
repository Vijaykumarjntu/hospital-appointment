# import whisper
# import numpy as np
# import io
# import wave
from faster_whisper import WhisperModel
from typing import Optional
import tempfile
import os

class FreeSpeechToText:
    """Open-source Speech-to-Text using Whisper (runs locally, no API)"""
    
    # Model sizes: tiny, base, small, medium, large
    # tiny = fastest, least accurate
    # large = slowest, most accurate
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model
        model_size: "tiny", "base", "small", "medium", "large"
        """
        print(f"Loading Whisper {model_size} model...")
        # self.model = whisper.load_model(model_size)
          # Use CPU with int8 for best performance on Windows
        self.model = WhisperModel(
            model_size, 
            device="cpu", 
            compute_type="int8",  # int8 is faster on CPU
            cpu_threads=4,         # Use 4 CPU threads
            num_workers=2          # Number of parallel workers
        )
        print("✅ Whisper model loaded")
        
        # Language mapping for Whisper
        self.language_codes = {
            "en": "english",
            "hi": "hindi", 
            "ta": "tamil",
            "te": "telugu",
            "kn": "kannada",
            "ml": "malayalam",
            "mr": "marathi",
            "bn": "bengali",
            "gu": "gujarati",
            "pa": "punjabi",
            "ur": "urdu"
        }
    
    def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> dict:
        """
        Transcribe audio bytes to text
        Returns: {"text": "...", "language": "en", "confidence": 0.95}
        """
        print("transcribe working")
        try:
            # Save bytes to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            # # Transcribe with Whisper
            # result = self.model.transcribe(
            #     tmp_path,
            #     language=language if language else None,
            #     task="transcribe",
            #     fp16=False  # Use FP32 for CPU
            # )

             # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                tmp_path,
                language=language if language else None,
                task="transcribe",
                beam_size=5,           # Better accuracy
                best_of=5,              # Number of candidates
                temperature=0.0,        # Lower = more deterministic
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6
            )

            # Collect all text
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)
            
            text = " ".join(text_parts)

            
            # Clean up
            os.unlink(tmp_path)
            
            # Convert language code (whisper returns full names)
            # detected_lang = result.get("language", "en")
            # Map back to short codes
            # lang_code = "en"
            # for code, name in self.language_codes.items():
            #     if name == detected_lang:
            #         lang_code = code
            #         break
            
            # return {
            #     "text": result.get("text", "").strip(),
            #     "language": lang_code,
            #     "confidence": result.get("confidence", 0.8),  # Whisper doesn't give confidence per word
            #     "segments": result.get("segments", [])
            # }

            return {
                "text": text.strip(),
                "language": info.language,
                "confidence": info.language_probability,
                "segments": list(segments)  # Convert to list if needed
            }
            
        except Exception as e:
            print(f"Whisper STT Error: {e}")
            return {
                "text": "",
                "language": language or "en",
                "confidence": 0,
                "error": str(e)
            }
    
    def transcribe_file(self, audio_path: str, language: Optional[str] = None) -> dict:
        """Transcribe audio from file path"""
        try:
            # result = self.model.transcribe(
            #     audio_path,
            #     language=language if language else None,
            #     task="transcribe",
            #     fp16=False
            # )

            segments, info = self.model.transcribe(
                audio_path,
                language=language if language else None,
                task="transcribe",
                beam_size=5
            )
            
            text = " ".join([segment.text for segment in segments])
            
            # detected_lang = result.get("language", "en")
            # lang_code = "en"
            # for code, name in self.language_codes.items():
            #     if name == detected_lang:
            #         lang_code = code
            #         break
            
            # return {
            #     "text": result.get("text", "").strip(),
            #     "language": lang_code,
            #     "confidence": result.get("confidence", 0.8),
            #     "segments": result.get("segments", [])
            # }
            return {
                "text": text.strip(),
                "language": info.language,
                "confidence": info.language_probability
            }
            
        except Exception as e:
            print(f"Whisper STT Error: {e}")
            return {"text": "", "language": "en", "confidence": 0, "error": str(e)}