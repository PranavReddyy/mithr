from elevenlabs.client import ElevenLabs
from elevenlabs import play
import io
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize ElevenLabs client
elabs_key = os.getenv("ELEVENLABS_API_KEY")
if elabs_key is None:
    logger.warning("ELEVENLABS_API_KEY not found. TTS will use text output only.")
    client = None
else:
    client = ElevenLabs(api_key=elabs_key)

# University assistant voice configuration
UNIVERSITY_VOICE_CONFIG = {
    "voice_id": "JBFqnCBsd6RMkjVDRZzb",  # Professional, clear voice for university setting
    "model_id": "eleven_multilingual_v2",
    "output_format": "mp3_44100_128",
    "voice_settings": {
        "stability": 0.75,  # More stable for educational content
        "similarity_boost": 0.85,
        "style": 0.2,  # Slightly more expressive for engagement
        "use_speaker_boost": True
    }
}


def botspeak(text, save_file=None, play_audio=False):
    """
    Convert text to speech for university assistant.
    
    Args:
        text (str): Text to convert to speech
        save_file (str, optional): Path to save audio file
        play_audio (bool): Whether to play audio immediately
    
    Returns:
        str: The input text (for fallback/logging)
    """
    logger.info(f"University Assistant: {text}")
    
    # If no API key or client, just print text
    if not client:
        print(f"🎓 University Assistant: {text}")
        return text
    
    try:
        # Generate speech using ElevenLabs
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=UNIVERSITY_VOICE_CONFIG["voice_id"],
            model_id=UNIVERSITY_VOICE_CONFIG["model_id"],
            output_format=UNIVERSITY_VOICE_CONFIG["output_format"],
            voice_settings=UNIVERSITY_VOICE_CONFIG["voice_settings"]
        )
        
        # Collect audio data
        audio_data = b''
        for chunk in audio_stream:
            audio_data += chunk
        
        # Save audio file if requested
        if save_file:
            with open(save_file, 'wb') as f:
                f.write(audio_data)
            logger.info(f"Audio saved to {save_file}")
        
        # Play audio if requested
        if play_audio:
            play(io.BytesIO(audio_data))
        
        return text
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        print(f"🎓 University Assistant: {text}")  # Fallback to text
        return text


def speak_with_emotion(text, emotion="neutral", save_file=None):
    """
    Speak with different emotional tones for university context.
    
    Args:
        text (str): Text to speak
        emotion (str): Emotion type - "neutral", "encouraging", "informative", "friendly"
        save_file (str, optional): Path to save audio
    """
    emotion_settings = {
        "neutral": {"stability": 0.75, "similarity_boost": 0.85, "style": 0.2},
        "encouraging": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.4},
        "informative": {"stability": 0.85, "similarity_boost": 0.9, "style": 0.1},
        "friendly": {"stability": 0.65, "similarity_boost": 0.8, "style": 0.35}
    }
    
    if not client:
        print(f"🎓 University Assistant ({emotion}): {text}")
        return text
    
    try:
        settings = emotion_settings.get(emotion, emotion_settings["neutral"])
        
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=UNIVERSITY_VOICE_CONFIG["voice_id"],
            model_id=UNIVERSITY_VOICE_CONFIG["model_id"],
            output_format=UNIVERSITY_VOICE_CONFIG["output_format"],
            voice_settings=settings
        )
        
        audio_data = b''
        for chunk in audio_stream:
            audio_data += chunk
        
        if save_file:
            with open(save_file, 'wb') as f:
                f.write(audio_data)
        
        play(io.BytesIO(audio_data))
        return text
        
    except Exception as e:
        logger.error(f"Emotional TTS Error: {e}")
        print(f"🎓 University Assistant ({emotion}): {text}")
        return text