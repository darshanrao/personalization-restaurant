import os
import io
from typing import Optional
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import base64

load_dotenv()

class VoiceService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # Default voice from quickstart
        self.client = None
        
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                print(f"Successfully initialized ElevenLabs with voice: {self.voice_id}")
            except Exception as e:
                print(f"Failed to initialize ElevenLabs: {e}")
                self.client = None
        else:
            print("ElevenLabs API key not found")

    async def text_to_speech(self, text: str) -> Optional[str]:
        """Convert text to speech and return base64 encoded audio"""
        if not self.client:
            return None
        
        try:
            # Generate speech using the correct API method from the quickstart guide
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            # Convert to base64 for JSON response
            audio_bytes = b"".join(audio)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return audio_base64
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None

    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert speech to text using ElevenLabs STT API"""
        if not self.client:
            print("ElevenLabs client not initialized")
            return None
        
        try:
            # Use ElevenLabs Speech-to-Text API with correct parameters
            response = self.client.speech_to_text.convert(
                file=audio_data,
                model_id="scribe_v1"  # ElevenLabs STT model
            )
            
            # Extract transcript from response
            if hasattr(response, 'text'):
                return response.text
            elif isinstance(response, dict) and 'text' in response:
                return response['text']
            else:
                print(f"Unexpected STT response format: {response}")
                return None
                
        except Exception as e:
            print(f"ElevenLabs STT error: {e}")
            return None

voice_service = VoiceService()
