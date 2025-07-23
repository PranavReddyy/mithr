#!/bin/bash
# filepath: /Users/Pranav/mithr_airport/install_python313_compatible.sh

echo "🎓 Setting up University Assistant with Python 3.13 Compatibility"
echo "=============================================================="

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "🐍 Python version: $python_version"

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install system dependencies
echo "📦 Installing system audio dependencies..."
brew install portaudio ffmpeg

# Navigate to project directory
cd /Users/Pranav/mithr_airport

# Remove old virtual environment if it exists
if [ -d "venv" ]; then
    echo "🗑️  Removing old virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install build tools
echo "📦 Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Install packages in order to avoid conflicts
echo "📦 Installing core dependencies..."
pip install fastapi uvicorn[standard] python-multipart

echo "📦 Installing audio processing packages..."
pip install numpy scipy soundfile librosa sounddevice

echo "📦 Installing PyTorch..."
pip install torch torchaudio

echo "📦 Installing Whisper..."
pip install openai-whisper

echo "📦 Installing ElevenLabs..."
pip install elevenlabs

echo "📦 Installing NVIDIA A2F dependencies..."
pip install grpcio protobuf

echo "📦 Installing HTTP and data processing..."
pip install requests aiohttp httpx pandas pyyaml

echo "📦 Installing development tools..."
pip install python-dotenv langchain-core typing-extensions

echo "📦 Installing visualization tools..."
pip install matplotlib networkx

echo "📦 Installing audio alternatives..."
pip install mutagen audioread

echo "🧪 Testing critical imports..."
python -c "
try:
    import torch; print('✅ PyTorch OK')
    import numpy; print('✅ NumPy OK') 
    import sounddevice; print('✅ SoundDevice OK')
    import whisper; print('✅ Whisper OK')
    import elevenlabs; print('✅ ElevenLabs OK')
    import soundfile; print('✅ SoundFile OK')
    import librosa; print('✅ Librosa OK')
    from scipy.io.wavfile import write; print('✅ SciPy OK')
    import fastapi; print('✅ FastAPI OK')
    import grpcio; print('✅ gRPC OK')
    print('🎉 All critical dependencies installed successfully!')
except ImportError as e:
    print(f'❌ Import error: {e}')
"

echo "🎉 Installation complete!"
echo "🚀 You can now start the server with:"
echo "   cd src && python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload"