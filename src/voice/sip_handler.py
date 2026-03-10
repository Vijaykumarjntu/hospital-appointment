import socket
import threading
import wave
import pyaudio
from typing import Optional, Callable
import json

class SimpleSIPHandler:
    """
    Simplified SIP handler for local testing
    For production, use Asterisk/FreeSWITCH
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5060):
        self.host = host
        self.port = port
        self.running = False
        self.callback = None
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
    def start(self, callback: Optional[Callable] = None):
        """Start SIP server"""
        self.callback = callback
        self.running = True
        
        # For demo, we'll simulate calls via WebSocket/HTTP
        # In production, integrate with Asterisk Manager Interface (AMI)
        print(f"SIP Handler started on {self.host}:{self.port}")
        print("📞 Ready to receive calls")
        
        # Start audio processing thread
        self.audio_thread = threading.Thread(target=self._process_audio)
        self.audio_thread.start()
    
    def _process_audio(self):
        """Process incoming audio (simplified for demo)"""
        p = pyaudio.PyAudio()
        
        # Open microphone stream (for testing)
        stream = p.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("🎤 Microphone open - speak into your mic to simulate call")
        
        frames = []
        recording = False
        
        while self.running:
            try:
                data = stream.read(self.chunk)
                
                # Simple voice activity detection (VAD)
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                if volume > 500:  # Threshold for voice
                    if not recording:
                        print("🔴 Recording started...")
                        recording = True
                        frames = []
                    frames.append(data)
                else:
                    if recording and len(frames) > 0:
                        # Check if silence long enough to end utterance
                        silence_duration = 0
                        # This is simplified - in production use proper VAD
                        if len(frames) > 50:  # About 1 second of audio
                            print("✅ Utterance complete")
                            self._process_utterance(frames)
                            frames = []
                            recording = False
                            
            except Exception as e:
                print(f"Audio error: {e}")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    def _process_utterance(self, frames):
        """Process a complete utterance"""
        # Save to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.audio_format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # Call the callback with audio file
            if self.callback:
                with open(f.name, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    self.callback(audio_bytes)
            
            os.unlink(f.name)
    
    def stop(self):
        """Stop SIP server"""
        self.running = False
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join()
        print("SIP Handler stopped")

# For Asterisk integration (production), use:
"""
import asyncio
from asterisk.ami import AMIClient

class AsteriskHandler:
    def __init__(self, host='localhost', port=5038, username='admin', secret='password'):
        self.client = AMIClient(host=host, port=port)
        self.client.login(username=username, secret=secret)
        
    def originate_call(self, extension, context='default', priority=1):
        action = self.client.originate(
            channel=f'SIP/{extension}',
            context=context,
            extention=extension,
            priority=priority,
            caller_id='VoiceAgent'
        )
        return action
"""