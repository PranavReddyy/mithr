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
NVIDIA_ACE_AVAILABLE = False
A2FControllerServiceStub = None

try:
    from nvidia_ace.services.a2f_controller.v1_pb2_grpc import A2FControllerServiceStub
    NVIDIA_ACE_AVAILABLE = True
    print("✅ NVIDIA ACE A2F Controller imported successfully")
except ImportError as e:
    print(f"⚠️  NVIDIA ACE A2F Controller import failed: {e}")
    # Create a mock stub class
    class MockA2FControllerServiceStub:
        def __init__(self, channel):
            self.channel = channel
        
        def ProcessAudioStream(self):
            return MockStream()
    
    class MockStream:
        pass
    
    A2FControllerServiceStub = MockA2FControllerServiceStub

# Try different possible import paths for A2F client
A2F_CLIENT_AVAILABLE = False
a2f_3d_auth = None
a2f_3d_service = None

try:
    import a2f.a2f_3d.client.auth as a2f_3d_auth
    import a2f.a2f_3d.client.service as a2f_3d_service
    A2F_CLIENT_AVAILABLE = True
    print("✅ A2F 3D client imported successfully (original path)")
except ImportError:
    try:
        from nvidia_ace.a2f_3d.client import auth as a2f_3d_auth
        from nvidia_ace.a2f_3d.client import service as a2f_3d_service
        A2F_CLIENT_AVAILABLE = True
        print("✅ A2F 3D client imported successfully (nvidia_ace path)")
    except ImportError:
        try:
            from nvidia_ace.client import auth as a2f_3d_auth
            from nvidia_ace.client import service as a2f_3d_service
            A2F_CLIENT_AVAILABLE = True
            print("✅ A2F 3D client imported successfully (direct client path)")
        except ImportError:
            print("⚠️  A2F 3D client not available - creating mock implementations")
            
            # Create mock implementations
            class MockAuth:
                @staticmethod
                def create_channel(uri, use_ssl=True, metadata=None):
                    print(f"🎭 Mock: Creating channel to {uri}")
                    return MockChannel()
            
            class MockService:
                @staticmethod
                async def write_to_stream(stream, config_file, data=None, samplerate=24000):
                    print(f"🎭 Mock: Writing {len(data) if data is not None else 0} samples at {samplerate}Hz")
                    await asyncio.sleep(0.1)
                
                @staticmethod
                async def read_from_stream(stream):
                    print("🎭 Mock: Reading animation data")
                    await asyncio.sleep(1)
                    # Create a mock output directory for testing
                    import tempfile
                    temp_dir = tempfile.mkdtemp(prefix="mock_a2f_")
                    # Create a dummy file
                    with open(os.path.join(temp_dir, "mock_animation.txt"), "w") as f:
                        f.write("Mock A2F animation data")
                    return temp_dir

            class MockChannel:
                pass
            
            a2f_3d_auth = MockAuth()
            a2f_3d_service = MockService()

a2f_router = APIRouter(prefix='/a2f')

# ElevenLabs setup
elabs_key = os.getenv("ELEVENLABS_API_KEY")
client = None

if elabs_key is None:
    print("⚠️  ELEVENLABS_API_KEY not set. TTS features will be limited.")
else:
    try:
        client = ElevenLabs(api_key=elabs_key)
        print("✅ ElevenLabs client initialized successfully")
    except Exception as e:
        print(f"❌ ElevenLabs client initialization failed: {e}")


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
    """Optimized audio collection using numpy"""
    chunks = []
    total_size = 0

    for chunk in audio_stream:
        chunks.append(chunk)
        total_size += len(chunk)

    if total_size == 0:
        return rate, np.array([], dtype=np.int16)

    # Pre-allocate buffer
    buffer = bytearray(total_size)
    offset = 0
    for chunk in chunks:
        chunk_len = len(chunk)
        buffer[offset:offset + chunk_len] = chunk
        offset += chunk_len

    # Convert to numpy array
    audio_array = np.frombuffer(buffer, dtype=np.int16)
    return rate, audio_array


@a2f_router.get("/status")
async def a2f_status():
    """Get detailed A2F system status"""
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    
    return {
        "nvidia_ace": {"ready": NVIDIA_ACE_AVAILABLE},
        "a2f_mode": "real" if (NVIDIA_ACE_AVAILABLE and A2F_CLIENT_AVAILABLE) else "mock"
    }


@a2f_router.post("/text2animation")
async def process_audio_to_animation(
    request: A2FRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Process text to 3D face animation using ElevenLabs TTS + NVIDIA A2F"""
    
    text = request.text
    function_id = request.function_id
    uri = request.uri
    config_file = request.config_file
    
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    
    # Check prerequisites
    if not client:
        raise HTTPException(status_code=503, detail="ElevenLabs TTS not available")
    
    if not nvidia_api_key:
        raise HTTPException(status_code=503, detail="NVIDIA API key not configured")
    
    try:
        print(f"🎬 Generating university assistant animation for: '{text[:50]}...'")
        
        # Generate audio using ElevenLabs
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id="cgSgspJ2msm6clMCkdW9",
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000",
        )
        
        # Process audio
        rate, data = optimize_audio_collection_and_export(audio_stream)
        print(f"🎵 Audio processed: {len(data)} samples")

        # A2F Processing
        metadata_args = [
            ("function-id", function_id), 
            ("authorization", f"Bearer {nvidia_api_key}")
        ]
        
        channel = a2f_3d_auth.create_channel(uri=uri, use_ssl=True, metadata=metadata_args)
        stub = A2FControllerServiceStub(channel)
        
        stream = stub.ProcessAudioStream()
        
        # Process through A2F
        write_task = asyncio.create_task(
            a2f_3d_service.write_to_stream(stream, config_file, data=data, samplerate=rate)
        )
        read_task = asyncio.create_task(
            a2f_3d_service.read_from_stream(stream)
        )

        await write_task
        await read_task
        
        # Create zip
        path = read_task.result()
        if path and os.path.exists(path):
            zip_name = f"university_assistant_animation_{uuid4().hex[:8]}"
            zip_path = shutil.make_archive(zip_name, 'zip', path)
            
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                raise HTTPException(status_code=500, detail="Failed to create animation")
            
            print(f"✅ University assistant animation ready: {os.path.basename(zip_path)}")
            
            background_tasks.add_task(cleanup_files(zip_path, path))
            
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=os.path.basename(zip_path)
            )
        else:
            raise HTTPException(status_code=500, detail="Animation generation failed")
            
    except Exception as e:
        print(f"❌ Animation error: {e}")
        raise HTTPException(status_code=500, detail=f"Animation failed: {str(e)}")


@a2f_router.post("/tts-only")
async def text_to_speech_only(
    request: TTSRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Generate TTS for university assistant"""
    
    text = request.text
    voice_id = request.voice_id
    
    if not client:
        raise HTTPException(status_code=503, detail="TTS not available")
    
    try:
        print(f"🎤 Generating university assistant voice: '{text[:50]}...'")
        
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Collect audio
        audio_data = b""
        for chunk in audio_stream:
            audio_data += chunk
        
        # Save audio
        temp_file = f"university_assistant_voice_{uuid4().hex[:8]}.mp3"
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        
        print(f"✅ University assistant voice ready: {temp_file}")
        
        background_tasks.add_task(cleanup_files(temp_file))
        
        return FileResponse(
            temp_file,
            media_type='audio/mpeg',
            filename=os.path.basename(temp_file)
        )
        
    except Exception as e:
        print(f"❌ TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@a2f_router.get("/health")
async def a2f_health_check():
    """Simple health check"""
    return {
        "status": "healthy", 
        "tts_ready": client is not None,
        "a2f_ready": NVIDIA_ACE_AVAILABLE and A2F_CLIENT_AVAILABLE
    }