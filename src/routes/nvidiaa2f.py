import shutil
import io
import os
import asyncio
import time
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from elevenlabs.client import ElevenLabs
# Remove pydub import - replace with numpy/scipy
# from pydub import AudioSegment
import numpy as np
from scipy.io import wavfile
import soundfile as sf
from nvidia_ace.services.a2f_controller.v1_pb2_grpc import A2FControllerServiceStub
import wave

import a2f.a2f_3d.client.auth as a2f_3d_auth
import a2f.a2f_3d.client.service as a2f_3d_service

a2f_router = APIRouter(prefix='/a2f')

elabs_key = os.getenv("ELEVENLABS_API_KEY")
if elabs_key is None:
    raise ValueError("Please set the ELEVENLABS_API_KEY environment variable.")
client = ElevenLabs(api_key=elabs_key)


def cleanup_files(*paths):
    time.sleep(2)
    for path in paths:
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
        except Exception as e:
            print(f"Error cleaning up {path}: {e}")


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


@a2f_router.post("/text2animation")
async def process_audio_to_animation(
    text: str,
    function_id: str = "0961a6da-fb9e-4f2e-8491-247e5fd7bf8d",
    uri: str = "grpc.nvcf.nvidia.com:443",
    config_file: str = "a2f/config/config_claire.yml",
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Process text to 3D face animation using ElevenLabs TTS + NVIDIA A2F
    """
    try:
        # Generate audio using ElevenLabs
        start_time = time.perf_counter()
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id="cgSgspJ2msm6clMCkdW9",  # University-appropriate voice
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000",
        )
        end_time = time.perf_counter()
        print(f"Audio generation took {end_time - start_time:.6f} seconds")

        # Collect and process audio
        start_time = time.perf_counter()
        rate, data = optimize_audio_collection_and_export(audio_stream)
        end_time = time.perf_counter()
        print(f"Audio collection took {end_time - start_time:.6f} seconds")

        # Create gRPC channel for A2F
        start_time = time.perf_counter()
        metadata_args = [("function-id", function_id), ("authorization", "Bearer " + os.getenv("NVIDIA_API_KEY", ""))]
        channel = a2f_3d_auth.create_channel(uri=uri, use_ssl=True, metadata=metadata_args)
        stub = A2FControllerServiceStub(channel)
        end_time = time.perf_counter()
        print(f"Channel creation took {end_time - start_time:.6f} seconds")

        # Process audio through A2F
        start_time = time.perf_counter()
        stream = stub.ProcessAudioStream()
        write = asyncio.create_task(a2f_3d_service.write_to_stream(stream, config_file, data=data, samplerate=rate))
        read = asyncio.create_task(a2f_3d_service.read_from_stream(stream))

        await write
        await read
        end_time = time.perf_counter()
        print(f"Stream processing took {end_time - start_time:.6f} seconds")

        # Get results and create zip
        path = read.result()
        if path:
            zip_path = shutil.make_archive("animation", 'zip', path)
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                raise HTTPException(status_code=500, detail="Failed to create zip archive.")
            
            background_tasks.add_task(cleanup_files, zip_path, path)
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=os.path.basename(zip_path)
            )
        else:
            raise HTTPException(status_code=500, detail="A2F processing failed")
            
    except Exception as e:
        print(f"Error in text2animation: {e}")
        raise HTTPException(status_code=500, detail=f"Animation processing failed: {str(e)}")


@a2f_router.get("/health")
async def a2f_health_check():
    """Health check for A2F system"""
    return {
        "status": "healthy",
        "elevenlabs": "connected" if elabs_key else "not configured",
        "nvidia_a2f": "configured" if os.getenv("NVIDIA_API_KEY") else "not configured"
    }