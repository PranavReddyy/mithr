import random
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import asyncio
import shutil
from uuid import uuid4
import tempfile
import logging
import json
import base64
import pandas as pd
from pydub import AudioSegment # Add pydub
import io # Add io
import math

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router
a2f_router = APIRouter()

# Request models
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "cgSgspJ2msm6clMCkdW9"

class A2FRequest(BaseModel):
    text: str
    function_id: str = "0961a6da-fb9e-4f2e-8491-247e5fd7bf8d"
    uri: str = "grpc.nvcf.nvidia.com:443"
    config_file: str = "a2f/config/config_claire.yml"

class STTRequest(BaseModel):
    audio_data: str  # Base64 encoded audio

# Try to import ElevenLabs
client = None
elabs_key = os.getenv("ELEVENLABS_API_KEY")
if elabs_key:
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=elabs_key)
        logger.info("✅ ElevenLabs TTS initialized")
    except ImportError:
        logger.warning("❌ ElevenLabs not installed. Install with: pip install elevenlabs")
    except Exception as e:
        logger.error(f"❌ ElevenLabs init failed: {e}")
else:
    logger.warning("❌ ELEVENLABS_API_KEY not found in environment")

# Try to import Whisper for STT
whisper_model = None
try:
    import whisper
    whisper_model = whisper.load_model("base")
    logger.info("✅ Whisper STT initialized")
except ImportError:
    logger.warning("❌ Whisper not installed. Install with: pip install openai-whisper")
except Exception as e:
    logger.error(f"❌ Whisper init failed: {e}")

# A2F availability
A2F_AVAILABLE = True  # Set to True since we have mock implementation
logger.info("✅ A2F components available (mock implementation)")

def cleanup_files(*paths):
    """Clean up temporary files"""
    def cleanup():
        for path in paths:
            try:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                        logger.info(f"Cleaned up file: {path}")
                    else:
                        shutil.rmtree(path)
                        logger.info(f"Cleaned up directory: {path}")
            except Exception as e:
                logger.error(f"Cleanup error for {path}: {e}")
    return cleanup

def generate_realistic_face_animation(text: str, audio_duration: float):
    """Generate realistic face animation keyframes based on text"""
    words = text.split()
    total_frames = int(audio_duration * 30)  # 30 FPS
    
    animation_frames = []
    
    # Define phoneme-to-viseme mapping for realistic mouth movements
    phoneme_map = {
        'a': {'mouth_open': 0.8, 'jaw_open': 0.6, 'lip_pucker': 0.0},
        'e': {'mouth_open': 0.5, 'jaw_open': 0.3, 'lip_pucker': 0.0},
        'i': {'mouth_open': 0.2, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        'o': {'mouth_open': 0.6, 'jaw_open': 0.4, 'lip_pucker': 0.7},
        'u': {'mouth_open': 0.3, 'jaw_open': 0.2, 'lip_pucker': 0.9},
        'm': {'mouth_open': 0.0, 'jaw_open': 0.0, 'lip_pucker': 0.0},
        'p': {'mouth_open': 0.0, 'jaw_open': 0.0, 'lip_pucker': 0.0},
        'b': {'mouth_open': 0.1, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        't': {'mouth_open': 0.2, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        'd': {'mouth_open': 0.3, 'jaw_open': 0.2, 'lip_pucker': 0.0},
        'k': {'mouth_open': 0.4, 'jaw_open': 0.3, 'lip_pucker': 0.0},
        'g': {'mouth_open': 0.4, 'jaw_open': 0.3, 'lip_pucker': 0.0},
        'f': {'mouth_open': 0.1, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        'v': {'mouth_open': 0.1, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        's': {'mouth_open': 0.1, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        'z': {'mouth_open': 0.1, 'jaw_open': 0.1, 'lip_pucker': 0.0},
        'l': {'mouth_open': 0.4, 'jaw_open': 0.2, 'lip_pucker': 0.0},
        'r': {'mouth_open': 0.3, 'jaw_open': 0.2, 'lip_pucker': 0.4},
        'w': {'mouth_open': 0.2, 'jaw_open': 0.1, 'lip_pucker': 0.8},
        'h': {'mouth_open': 0.6, 'jaw_open': 0.4, 'lip_pucker': 0.0},
        'silence': {'mouth_open': 0.0, 'jaw_open': 0.0, 'lip_pucker': 0.0}
    }
    
    word_durations = [len(word) * 0.1 for word in words]
    total_word_time = sum(word_durations)
    
    if total_word_time > 0:
        scale_factor = audio_duration / total_word_time
        word_durations = [d * scale_factor for d in word_durations]
    
    current_time = 0
    word_start_times = []
    for d in word_durations:
        word_start_times.append(current_time)
        current_time += d

    for frame in range(total_frames):
        time_in_seconds = frame / 30.0
        
        word_index = -1
        for i, start_time in enumerate(word_start_times):
            if time_in_seconds >= start_time:
                word_index = i

        if word_index != -1:
            word = words[word_index]
            first_char = word[0].lower() if word else 'silence'
            phoneme = phoneme_map.get(first_char, phoneme_map['silence'])
            
            time_into_word = time_in_seconds - word_start_times[word_index]
            word_duration = word_durations[word_index]
            progress = time_into_word / max(word_duration, 0.01)
            easing = 0.5 * (1 - math.cos(math.pi * min(progress, 1.0) * 2)) # Ease in and out
        else:
            word = ""
            first_char = "silence"
            phoneme = phoneme_map['silence']
            easing = 0

        noise_factor = 0.02
        
        frame_data = {
            "frame": frame,
            "time": time_in_seconds,
            "face_controls": {
                "mouth_open": max(0, min(1, phoneme['mouth_open'] * easing + random.uniform(-noise_factor, noise_factor))),
                "jaw_open": max(0, min(1, phoneme['jaw_open'] * easing + random.uniform(-noise_factor, noise_factor))),
                "lip_pucker": max(0, min(1, phoneme['lip_pucker'] * easing + random.uniform(-noise_factor, noise_factor))),
                "mouthSmile": random.uniform(0, 0.15) * easing,
                "eyeBlink": 1.0 if frame % 100 < 4 else 0.0,  # Blink every ~3 seconds
                "browUp": random.uniform(0, 0.4) * easing,
                "headNod": 0.03 * math.sin(time_in_seconds * 1.5),
                "headTurn": 0.02 * math.sin(time_in_seconds * 1.2)
            },
            "word": word,
            "phoneme": first_char
        }
        
        animation_frames.append(frame_data)
        
    return animation_frames

@a2f_router.get("/status")
async def a2f_status():
    """Get A2F system status"""
    status = {
        "tts_available": client is not None,
        "stt_available": whisper_model is not None,
        "a2f_available": A2F_AVAILABLE,
        "elevenlabs_configured": elabs_key is not None,
        "elevenlabs_key_present": bool(elabs_key)
    }
    logger.info(f"A2F Status: {status}")
    return status

@a2f_router.post("/tts-only")
async def text_to_speech_only(
    request: TTSRequest,
    background_tasks: BackgroundTasks
):
    """Generate TTS audio"""
    logger.info(f"🎤 TTS request for: '{request.text[:50]}...'")
    
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="TTS not available - ElevenLabs not configured. Check ELEVENLABS_API_KEY."
        )
    
    try:
        logger.info(f"Generating TTS with voice_id: {request.voice_id}")
        
        # Generate audio with no timeout
        audio_stream = client.text_to_speech.stream(
            text=request.text,
            voice_id=request.voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Save to temporary file
        temp_file = f"tts_output_{uuid4().hex[:8]}.mp3"
        logger.info(f"Saving TTS to: {temp_file}")
        
        with open(temp_file, 'wb') as f:
            chunk_count = 0
            for chunk in audio_stream:
                f.write(chunk)
                chunk_count += 1
        
        logger.info(f"✅ TTS generated: {temp_file} ({chunk_count} chunks)")
        
        # Verify file exists and has content
        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            raise Exception("Generated audio file is empty or missing")
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_files(temp_file))
        
        return FileResponse(
            temp_file,
            media_type='audio/mpeg',
            filename="university_assistant_voice.mp3"
        )
        
    except Exception as e:
        logger.error(f"❌ TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

whisper_model = None
try:
    from faster_whisper import WhisperModel
    # Using "base" model with int8 quantization for fast CPU performance.
    # For GPU, you might use device="cuda" and compute_type="float16".
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("✅ faster-whisper STT initialized")
except ImportError:
    logger.warning("❌ faster-whisper not installed. Install with: pip install faster-whisper")
except Exception as e:
    logger.error(f"❌ faster-whisper init failed: {e}")

# A2F availability
A2F_AVAILABLE = True  

@a2f_router.post("/stt")
async def speech_to_text(request: STTRequest):
    """Convert speech to text using Whisper"""
    logger.info("🎧 STT request received")
    
    if not whisper_model:
        raise HTTPException(
            status_code=503, 
            detail="STT not available - Whisper not configured. Install with: pip install faster-whisper"
        )
    
    try:
        import base64
        import numpy as np
        import io
        from pydub import AudioSegment
        import tempfile
        
        logger.info("Decoding audio data...")
        
        # Decode base64 audio from the frontend
        audio_bytes = base64.b64decode(request.audio_data)
        logger.info(f"Decoded {len(audio_bytes)} bytes of audio data")
        
        # Use pydub to convert the incoming audio (likely webm/ogg) to WAV
        logger.info("Converting audio to WAV format for Whisper...")
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            
            # Whisper works best with 16-bit PCM WAV at a 16000Hz sample rate
            audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Use a temporary file for Whisper processing
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
                audio_segment.export(temp_wav_file.name, format="wav")
                temp_wav_path = temp_wav_file.name
            
            logger.info(f"Audio converted and saved to temporary WAV file: {temp_wav_path}")

        except Exception as conversion_error:
            logger.error(f"❌ Audio conversion with pydub failed: {conversion_error}")
            raise HTTPException(status_code=400, detail="Failed to process audio format.")

        # Transcribe using faster-whisper from the converted WAV file
        logger.info("Transcribing with faster-whisper...")
        segments, info = whisper_model.transcribe(temp_wav_path, beam_size=5, language="en")
        
        # faster-whisper returns a generator, so we join the segments
        transcribed_text = "".join(segment.text for segment in segments).strip()
        
        # Clean up the temporary file
        os.remove(temp_wav_path)
        
        logger.info(f"✅ STT result: '{transcribed_text}'")
        
        return {
            "text": transcribed_text,
            "language": info.language,
            "confidence": info.language_probability
        }
        
    except Exception as e:
        logger.error(f"❌ STT error: {e}")
        # Clean up temp file in case of an error during transcription
        if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")

@a2f_router.post("/web-animation")
async def generate_web_animation(
    request: A2FRequest,
    background_tasks: BackgroundTasks
):
    """Generate web-playable animation with audio"""
    logger.info(f"🎬 Web Animation request for: '{request.text[:50]}...'")
    
    if not A2F_AVAILABLE:
        raise HTTPException(status_code=503, detail="A2F not available")
    
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="TTS not available for A2F - ElevenLabs not configured"
        )
    
    try:
        import math
        
        logger.info("Step 1: Generating TTS audio for web animation...")
        
        # Step 1: Generate TTS audio
        audio_stream = client.text_to_speech.stream(
            text=request.text,
            voice_id="cgSgspJ2msm6clMCkdW9",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Save audio to temporary file and encode to base64
        temp_audio_file = f"temp_audio_{uuid4().hex[:8]}.mp3"
        with open(temp_audio_file, 'wb') as f:
            chunk_count = 0
            for chunk in audio_stream:
                f.write(chunk)
                chunk_count += 1
        
        # Estimate audio duration (rough calculation)
        audio_duration = len(request.text) * 0.08  # ~0.08 seconds per character
        
        logger.info(f"Generated audio: {temp_audio_file} ({chunk_count} chunks), estimated duration: {audio_duration}s")
        
        # Convert audio to base64 for web delivery
        with open(temp_audio_file, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Step 2: Generate realistic animation keyframes
        logger.info("Step 2: Generating realistic face animation...")
        animation_frames = generate_realistic_face_animation(request.text, audio_duration)
        
        # Step 3: Create web-compatible animation package
        web_animation = {
            "metadata": {
                "text": request.text,
                "duration": audio_duration,
                "total_frames": len(animation_frames),
                "fps": 30,
                "voice_id": "cgSgspJ2msm6clMCkdW9",
                "generated_by": "University Assistant A2F Web",
                "version": "1.0"
            },
            "audio": {
                "format": "mp3",
                "base64": audio_base64,
                "duration": audio_duration
            },
            "animation": {
                "type": "face_animation",
                "frames": animation_frames,
                "controls": [
                    "mouth_open", "jaw_open", "lip_pucker", "smile", 
                    "blink", "eyebrow_raise", "head_nod", "head_turn"
                ]
            },
            "playback_info": {
                "recommended_avatar": "university_assistant",
                "sync_audio": True,
                "loop": False
            }
        }
        
        logger.info(f"✅ Web animation generated: {len(animation_frames)} frames")
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_files(temp_audio_file))
        
        return JSONResponse(content=web_animation)
        
    except Exception as e:
        logger.error(f"❌ Web animation error: {e}")
        raise HTTPException(status_code=500, detail=f"Web animation failed: {str(e)}")

@a2f_router.post("/text2animation")
async def process_text_to_animation(
    request: A2FRequest,
    background_tasks: BackgroundTasks
):
    """Generate 3D face animation from text (legacy - returns zip file)"""
    logger.info(f"🎬 A2F request for: '{request.text[:50]}...'")
    
    if not A2F_AVAILABLE:
        raise HTTPException(status_code=503, detail="A2F not available")
    
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="TTS not available for A2F - ElevenLabs not configured"
        )
    
    try:
        logger.info("Step 1: Generating TTS audio (MP3) for playback...")
        
        # Generate TTS audio in MP3 format for the frontend to play
        audio_stream_mp3 = client.text_to_speech.stream(
            text=request.text,
            voice_id="cgSgspJ2msm6clMCkdW9",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        mp3_audio_data = b"".join(chunk for chunk in audio_stream_mp3)
        logger.info(f"Generated {len(mp3_audio_data)} bytes of MP3 audio data")
        
        # Step 2: Convert MP3 to WAV for processing and get accurate duration
        logger.info("Step 2: Converting to WAV for processing and getting duration...")
        try:
            # Load MP3 data into pydub
            audio_segment = AudioSegment.from_file(io.BytesIO(mp3_audio_data), format="mp3")
            
            # Get accurate duration
            audio_duration = len(audio_segment) / 1000.0  # Duration in seconds
            logger.info(f"Accurate audio duration: {audio_duration:.2f}s")

            # Export to WAV format in memory for A2F processing
            # A real A2F service would consume this wav_audio_data
            wav_buffer = io.BytesIO()
            # A2F typically expects a specific sample rate (e.g., 24000Hz), 16-bit, mono
            audio_segment_wav = audio_segment.set_frame_rate(24000).set_channels(1).set_sample_width(2)
            audio_segment_wav.export(wav_buffer, format="wav")
            wav_audio_data = wav_buffer.getvalue()
            logger.info(f"Converted to {len(wav_audio_data)} bytes of WAV data for A2F processing")

        except Exception as e:
            logger.error(f"Could not process audio with pydub: {e}. Falling back to estimation.")
            # Fallback estimation (less accurate)
            audio_duration = len(request.text) * 0.08
            wav_audio_data = None # Can't process if pydub fails
        
        # Step 3: Generate animation frames using the accurate duration
        # A real implementation would pass wav_audio_data to the A2F service.
        logger.info("Step 3: Generating mock animation frames...")
        
        # Create output directory
        output_dir = tempfile.mkdtemp(prefix="a2f_output_")
        logger.info(f"Created output directory: {output_dir}")

        # Generate frames using the accurate duration
        animation_frames = generate_realistic_face_animation(request.text, audio_duration)

        # Prepare data for CSV files
        emotion_records = []
        blendshape_records = []
        for frame in animation_frames:
            emotion_records.append({
                'frame': frame['frame'],
                'time_code': frame['time'],
                'emotion_values.grief': frame['face_controls'].get('grief', 0),
                'emotion_values.joy': frame['face_controls'].get('smile', 0),
                'emotion_values.disgust': 0,
                'emotion_values.outofbreath': 0,
                'emotion_values.pain': 0,
                'emotion_values.anger': 0,
                'emotion_values.amazement': frame['face_controls'].get('eyebrow_raise', 0),
                'emotion_values.cheekiness': 0,
                'emotion_values.sadness': 0,
                'emotion_values.fear': 0,
            })
            blendshape_records.append({
                'frame': frame['frame'],
                'timeCode': frame['time'],
                'blendShapes.mouth_open': frame['face_controls']['mouth_open'],
                'blendShapes.jaw_open': frame['face_controls']['jaw_open'],
                'blendShapes.lip_pucker': frame['face_controls']['lip_pucker'],
                'blendShapes.mouthSmile': frame['face_controls']['mouthSmile'],
                'blendShapes.eyeBlink': frame['face_controls']['eyeBlink'],
                'blendShapes.browUp': frame['face_controls']['browUp'],
                'blendShapes.headNod': frame['face_controls']['headNod'],
                'blendShapes.headTurn': frame['face_controls']['headTurn'],
            })
        
        # Create and save CSV files using pandas
        pd.DataFrame(emotion_records).to_csv(os.path.join(output_dir, "a2f_smoothed_emotion_output.csv"), index=False)
        pd.DataFrame(blendshape_records).to_csv(os.path.join(output_dir, "animation_frames.csv"), index=False)
        
        # Save the PLAYBACK audio (MP3) as out.mp3
        with open(os.path.join(output_dir, "out.mp3"), "wb") as f:
            f.write(mp3_audio_data)
        
        # Step 4: Create zip file
        logger.info("Step 4: Creating animation package...")
        zip_name = f"university_animation_{uuid4().hex[:8]}"
        zip_path = shutil.make_archive(zip_name, 'zip', output_dir)
        
        logger.info(f"✅ A2F animation package created: {zip_path}")
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_files(zip_path, output_dir))
        
        return FileResponse(
            zip_path,
            media_type='application/zip',
            filename="university_animation.zip"
        )
        
    except Exception as e:
        logger.error(f"❌ A2F error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"A2F failed: {str(e)}")


@a2f_router.get("/health")
async def a2f_health_check():
    """A2F health check"""
    health = {
        "status": "healthy",
        "tts_ready": client is not None,
        "stt_ready": whisper_model is not None,
        "a2f_ready": A2F_AVAILABLE,
        "web_animation_ready": True,
        "services": {
            "elevenlabs": "configured" if client else "not configured",
            "whisper": "loaded" if whisper_model else "not loaded",
            "a2f": "available (mock)" if A2F_AVAILABLE else "unavailable"
        }
    }
    logger.info(f"A2F Health check: {health}")
    return health