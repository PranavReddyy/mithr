import shutil
import io
import os
import asyncio
import time
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from elevenlabs.client import ElevenLabs
from pydantic import BaseModel
# Remove pydub import - replace with numpy/scipy
# from pydub import AudioSegment
import numpy as np
from scipy.io import wavfile
import soundfile as sf
import wave

# Add Pydantic models for request bodies
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "cgSgspJ2msm6clMCkdW9"

class A2FRequest(BaseModel):
    text: str
    function_id: str = "0961a6da-fb9e-4f2e-8491-247e5fd7bf8d"
    uri: str = "grpc.nvcf.nvidia.com:443"
    config_file: str = "a2f/config/config_claire.yml"

# Try to import NVIDIA ACE components with proper error handling
try:
    from nvidia_ace.services.a2f_controller.v1_pb2_grpc import A2FControllerServiceStub
    NVIDIA_ACE_AVAILABLE = True
    print("✅ NVIDIA ACE A2F Controller imported successfully")
except ImportError as e:
    print(f"⚠️  NVIDIA ACE A2F Controller import failed: {e}")
    NVIDIA_ACE_AVAILABLE = False

# Try different possible import paths for A2F client
A2F_CLIENT_AVAILABLE = False
try:
    # Try the original import path first
    import a2f.a2f_3d.client.auth as a2f_3d_auth
    import a2f.a2f_3d.client.service as a2f_3d_service
    A2F_CLIENT_AVAILABLE = True
    print("✅ A2F 3D client imported successfully (original path)")
except ImportError:
    try:
        # Try alternative import path
        from nvidia_ace.a2f_3d.client import auth as a2f_3d_auth
        from nvidia_ace.a2f_3d.client import service as a2f_3d_service
        A2F_CLIENT_AVAILABLE = True
        print("✅ A2F 3D client imported successfully (nvidia_ace path)")
    except ImportError:
        try:
            # Try direct nvidia_ace client path
            from nvidia_ace.client import auth as a2f_3d_auth
            from nvidia_ace.client import service as a2f_3d_service
            A2F_CLIENT_AVAILABLE = True
            print("✅ A2F 3D client imported successfully (direct client path)")
        except ImportError:
            print("⚠️  A2F 3D client not available - creating mock implementations")
            
            # Create minimal mock implementations to prevent crashes
            class MockAuth:
                @staticmethod
                def create_channel(uri, use_ssl=True, metadata=None):
                    print(f"🎭 Mock: Creating channel to {uri}")
                    return MockChannel()
            
            class MockService:
                @staticmethod
                async def write_to_stream(stream, config_file, data=None, samplerate=24000):
                    print(f"🎭 Mock: Writing {len(data)} samples at {samplerate}Hz")
                    await asyncio.sleep(0.1)  # Simulate processing
                
                @staticmethod
                async def read_from_stream(stream):
                    print("🎭 Mock: Reading animation data")
                    await asyncio.sleep(1)  # Simulate processing
                    return None  # Mock will return None to trigger error handling

            class MockChannel:
                pass
            
            a2f_3d_auth = MockAuth()
            a2f_3d_service = MockService()
            A2F_CLIENT_AVAILABLE = False

a2f_router = APIRouter(prefix='/a2f')

# ElevenLabs setup with better error handling
elabs_key = os.getenv("ELEVENLABS_API_KEY")
if elabs_key is None:
    print("⚠️  ELEVENLABS_API_KEY not set. TTS features will be limited.")
    client = None
else:
    try:
        client = ElevenLabs(api_key=elabs_key)
        print("✅ ElevenLabs client initialized successfully")
    except Exception as e:
        print(f"❌ ElevenLabs client initialization failed: {e}")
        client = None


def cleanup_files(*paths):
    """Clean up temporary files"""
    def cleanup():
        time.sleep(2)
        for path in paths:
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        print(f"🗑️  Cleaned up directory: {path}")
                    elif os.path.isfile(path):
                        os.remove(path)
                        print(f"🗑️  Cleaned up file: {path}")
            except Exception as e:
                print(f"Error cleaning up {path}: {e}")
    return cleanup


def optimize_audio_collection_and_export(audio_stream, rate=24000):
    """
    Optimized audio collection using numpy instead of pydub
    """
    # First pass: collect chunks and calculate total size
    chunks = []
    total_size = 0

    for chunk in audio_stream:
        chunks.append(chunk)
        total_size += len(chunk)

    if total_size == 0:
        return rate, np.array([], dtype=np.int16)

    # Pre-allocate buffer with exact size needed
    buffer = bytearray(total_size)

    # Second pass: copy chunks directly into buffer
    offset = 0
    for chunk in chunks:
        chunk_len = len(chunk)
        buffer[offset:offset + chunk_len] = chunk
        offset += chunk_len

    # Convert directly to numpy array
    audio_array = np.frombuffer(buffer, dtype=np.int16)
    return rate, audio_array


def convert_audio_format(audio_data, sample_rate, target_format="wav"):
    """
    Convert audio data to different formats using soundfile instead of pydub
    """
    try:
        # Convert to float32 for processing
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32767.0
        else:
            audio_float = audio_data.astype(np.float32)
        
        # Create temporary file
        temp_file = f"temp_audio_{uuid4().hex}.{target_format}"
        
        # Write using soundfile
        sf.write(temp_file, audio_float, sample_rate)
        
        return temp_file
    except Exception as e:
        print(f"Audio conversion error: {e}")
        return None


@a2f_router.get("/status")
async def a2f_status():
    """Get detailed A2F system status"""
    return {
        "nvidia_ace_controller": NVIDIA_ACE_AVAILABLE,
        "a2f_client": A2F_CLIENT_AVAILABLE,
        "elevenlabs": client is not None,
        "nvidia_api_key": os.getenv("NVIDIA_API_KEY") is not None,
        "ready": NVIDIA_ACE_AVAILABLE and A2F_CLIENT_AVAILABLE and client is not None and os.getenv("NVIDIA_API_KEY") is not None,
        "mode": "real" if (NVIDIA_ACE_AVAILABLE and A2F_CLIENT_AVAILABLE) else "mock"
    }


@a2f_router.post("/text2animation")
async def process_audio_to_animation(
    request: A2FRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Process text to 3D face animation using ElevenLabs TTS + NVIDIA A2F
    """
    # Extract parameters from request body
    text = request.text
    function_id = request.function_id
    uri = request.uri
    config_file = request.config_file
    
    # Check prerequisites
    if not client:
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs TTS not available. Please configure ELEVENLABS_API_KEY."
        )
    
    if not NVIDIA_ACE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="NVIDIA ACE not available. Please install nvidia-ace package."
        )
    
    if not A2F_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="A2F client not available. Running in mock mode - no animation will be generated."
        )
    
    if not os.getenv("NVIDIA_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="NVIDIA API key not configured. Please set NVIDIA_API_KEY environment variable."
        )
    
    try:
        print(f"🎬 Processing text to animation: {text[:50]}...")
        
        # Generate audio using ElevenLabs
        start_time = time.perf_counter()
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id="cgSgspJ2msm6clMCkdW9",  # University-appropriate voice
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000",
        )
        audio_gen_time = time.perf_counter() - start_time
        print(f"🎤 Audio generation: {audio_gen_time:.3f}s")

        # Collect and process audio
        start_time = time.perf_counter()
        rate, data = optimize_audio_collection_and_export(audio_stream)
        audio_proc_time = time.perf_counter() - start_time
        print(f"🎵 Audio processing: {audio_proc_time:.3f}s ({len(data)} samples)")

        # Create gRPC channel for A2F
        start_time = time.perf_counter()
        metadata_args = [("function-id", function_id), ("authorization", "Bearer " + os.getenv("NVIDIA_API_KEY", ""))]
        channel = a2f_3d_auth.create_channel(uri=uri, use_ssl=True, metadata=metadata_args)
        stub = A2FControllerServiceStub(channel)
        channel_time = time.perf_counter() - start_time
        print(f"🔗 Channel creation: {channel_time:.3f}s")

        # Process audio through A2F
        start_time = time.perf_counter()
        stream = stub.ProcessAudioStream()
        write = asyncio.create_task(a2f_3d_service.write_to_stream(stream, config_file, data=data, samplerate=rate))
        read = asyncio.create_task(a2f_3d_service.read_from_stream(stream))

        await write
        await read
        a2f_proc_time = time.perf_counter() - start_time
        print(f"🎬 A2F processing: {a2f_proc_time:.3f}s")

        # Get results and create zip
        path = read.result()
        if path:
            # Create zip with unique name
            zip_name = f"university_animation_{uuid4().hex[:8]}"
            zip_path = shutil.make_archive(zip_name, 'zip', path)
            
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                raise HTTPException(status_code=500, detail="Failed to create zip archive.")
            
            total_time = audio_gen_time + audio_proc_time + channel_time + a2f_proc_time
            print(f"✅ Animation complete: {os.path.basename(zip_path)} ({os.path.getsize(zip_path)} bytes, {total_time:.3f}s total)")
            
            background_tasks.add_task(cleanup_files(zip_path, path))
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=os.path.basename(zip_path),
                headers={
                    "X-Processing-Time": f"{total_time:.3f}s",
                    "X-Audio-Samples": str(len(data))
                }
            )
        else:
            raise HTTPException(status_code=500, detail="A2F processing failed - no output generated")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in text2animation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Animation processing failed: {str(e)}")


@a2f_router.post("/tts-only")
async def text_to_speech_only(
    request: TTSRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Text-to-speech only (without A2F animation) for testing
    """
    # Extract parameters from request body
    text = request.text
    voice_id = request.voice_id
    
    if not client:
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs TTS not available. Please configure ELEVENLABS_API_KEY."
        )
    
    try:
        print(f"🎤 Generating TTS for: {text[:50]}...")
        
        # Generate audio using ElevenLabs
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Collect audio data
        audio_data = b""
        for chunk in audio_stream:
            audio_data += chunk
        
        # Save to temporary file with unique name
        temp_file = f"university_tts_{uuid4().hex[:8]}.mp3"
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        
        print(f"✅ TTS generated: {temp_file} ({len(audio_data)} bytes)")
        
        background_tasks.add_task(cleanup_files(temp_file))
        
        return FileResponse(
            temp_file,
            media_type='audio/mpeg',
            filename=os.path.basename(temp_file),
            headers={
                "X-Audio-Length": str(len(audio_data))
            }
        )
        
    except Exception as e:
        print(f"❌ Error in TTS: {e}")
        raise HTTPException(status_code=500, detail=f"TTS processing failed: {str(e)}")


@a2f_router.get("/health")
async def a2f_health_check():
    """Health check for A2F system"""
    return {
        "status": "healthy",
        "elevenlabs": "connected" if client else "not configured",
        "nvidia_ace": "available" if NVIDIA_ACE_AVAILABLE else "not available",
        "a2f_client": "available" if A2F_CLIENT_AVAILABLE else "not available", 
        "nvidia_api_key": "configured" if os.getenv("NVIDIA_API_KEY") else "not configured",
        "ready_for_animation": NVIDIA_ACE_AVAILABLE and A2F_CLIENT_AVAILABLE and client is not None and os.getenv("NVIDIA_API_KEY") is not None,
        "ready_for_tts": client is not None
    }