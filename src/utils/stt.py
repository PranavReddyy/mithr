import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import audio packages with better error handling
AUDIO_AVAILABLE = True
MISSING_PACKAGES = []

try:
    import torch
    logger.info("✅ PyTorch imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("torch")
    logger.warning(f"❌ PyTorch not available: {e}")

try:
    import numpy as np
    logger.info("✅ NumPy imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("numpy")
    logger.warning(f"❌ NumPy not available: {e}")

try:
    import sounddevice as sd
    logger.info("✅ SoundDevice imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("sounddevice")
    logger.warning(f"❌ SoundDevice not available: {e}")

try:
    import whisper
    logger.info("✅ Whisper imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("whisper")
    logger.warning(f"❌ Whisper not available: {e}")

try:
    from scipy.io.wavfile import write as wav_write
    logger.info("✅ SciPy imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("scipy")
    logger.warning(f"❌ SciPy not available: {e}")

try:
    import pyaudio
    logger.info("✅ PyAudio imported successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    MISSING_PACKAGES.append("pyaudio")
    logger.warning(f"❌ PyAudio not available: {e}")

# Additional imports
import tempfile
import wave
import time

if not AUDIO_AVAILABLE:
    logger.warning(f"🎤 Audio features disabled. Missing packages: {MISSING_PACKAGES}")
    logger.info("💬 Falling back to text-only input mode")


class UniversitySpeechToText:
    """Speech-to-Text system optimized for university assistant interactions."""
    
    def __init__(self, whisper_model_size="base", enable_voice_input=False):
        """
        Initialize STT system.
        
        Args:
            whisper_model_size (str): Whisper model size - "tiny", "base", "small", "medium", "large"
            enable_voice_input (bool): Enable actual voice recording (set to False for text input fallback)
        """
        self.enable_voice_input = enable_voice_input and AUDIO_AVAILABLE
        self.whisper_model = None
        self.vad_model = None
        self.vad_utils = None
        
        if self.enable_voice_input:
            try:
                logger.info(f"🤖 Loading Whisper model: {whisper_model_size}")
                self.whisper_model = whisper.load_model(whisper_model_size)
                
                logger.info("🎯 Loading Voice Activity Detection model")
                self.vad_model, self.vad_utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False
                )
                logger.info("🎉 STT system initialized successfully with audio support")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize STT models: {e}")
                logger.info("💬 Falling back to text input mode")
                self.enable_voice_input = False
        else:
            if not AUDIO_AVAILABLE:
                logger.info("💬 STT system initialized in text-only mode (missing audio dependencies)")
            else:
                logger.info("💬 STT system initialized in text-only mode (voice input disabled)")

    def transcribe_audio(self, audio_bytes):
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio bytes
            
        Returns:
            str: Transcribed text
        """
        if not self.whisper_model:
            return ""
            
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                with wave.open(temp_file.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
                    wf.setframerate(16000)
                    wf.writeframes(audio_bytes)
                
                result = self.whisper_model.transcribe(
                    temp_file.name, 
                    language='en', 
                    fp16=False, 
                    verbose=False
                )
                os.unlink(temp_file.name)
                return result["text"].strip()
                
        except Exception as e:
            logger.error(f"❌ Audio transcription failed: {e}")
            return ""

    def voice_input(self, prompt_text, filename='university_input.wav', max_record_seconds=15, silence_duration=2.0):
        """
        Get voice input from user with VAD-based silence detection.
        
        Args:
            prompt_text (str): Text to display to user
            filename (str): File to save recorded audio
            max_record_seconds (int): Maximum recording duration
            silence_duration (float): Silence duration to stop recording
            
        Returns:
            str: Transcribed text or user input
        """
        if not self.enable_voice_input:
            # Fallback to text input with university-friendly prompt
            print(f"\n🎤 {prompt_text}")
            if not AUDIO_AVAILABLE:
                print("💬 Audio not available - using text input mode")
                print(f"   Missing packages: {MISSING_PACKAGES}")
            print("💬 Type your response (or 'quit' to exit): ", end="")
            user_input = input().strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                return "goodbye"
            return user_input
        
        # Voice recording with VAD
        SAMPLE_RATE = 16000
        FRAME_SAMPLES = 512
        SILERO_THRESHOLD = 0.5

        frames_per_second = SAMPLE_RATE / FRAME_SAMPLES
        silence_frames = int(silence_duration * frames_per_second)

        print(f"\n🎤 {prompt_text}")
        print("🔴 Recording... Speak into the microphone (or press Ctrl+C for text input)")

        audio_buffer = []
        silent_frames_count = 0
        start_time = time.time()
        is_recording = True
        speech_detected = False

        def callback(indata, frames, time_info, status):
            nonlocal silent_frames_count, is_recording, speech_detected

            chunk = indata[:FRAME_SAMPLES, 0].copy()
            if len(chunk) < FRAME_SAMPLES:
                return

            chunk_int16 = (chunk * 32767).astype(np.int16)
            audio_buffer.append(chunk_int16.copy())

            input_tensor = torch.from_numpy(chunk_int16).unsqueeze(0)

            with torch.no_grad():
                speech_prob = self.vad_model(input_tensor, SAMPLE_RATE).item()

            if speech_prob >= SILERO_THRESHOLD:
                speech_detected = True
                silent_frames_count = 0
            else:
                if speech_detected:  # Only count silence after speech is detected
                    silent_frames_count += 1
                    if silent_frames_count >= silence_frames:
                        is_recording = False

            if (time.time() - start_time) >= max_record_seconds:
                is_recording = False

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=FRAME_SAMPLES,
                callback=callback
            ):
                while is_recording and (time.time() - start_time < max_record_seconds):
                    time.sleep(0.01)
                    
        except KeyboardInterrupt:
            print("\n⌨️  Switching to text input...")
            user_input = input("💬 Type your response: ").strip()
            return user_input if user_input else ""

        print("🔴 Recording stopped")

        if audio_buffer and speech_detected:
            full_audio = np.concatenate(audio_buffer)
            transcribed_text = self.transcribe_audio(full_audio.tobytes())
            
            if transcribed_text:
                print(f"📝 You said: {transcribed_text}")
                wav_write(filename, SAMPLE_RATE, full_audio)
                return transcribed_text
            else:
                print("❌ Could not transcribe audio. Please try again.")
                return ""
        else:
            print("❌ No speech detected")
            return ""

    def quick_voice_input(self, prompt_text):
        """Quick voice input for simple yes/no or short responses."""
        return self.voice_input(prompt_text, max_record_seconds=5, silence_duration=1.0)


# Global STT instance for easy access
stt_system = UniversitySpeechToText(enable_voice_input=AUDIO_AVAILABLE)  # Enable if audio is available

def get_user_input(prompt_text):
    """Simple function to get user input (voice or text)."""
    return stt_system.voice_input(prompt_text)