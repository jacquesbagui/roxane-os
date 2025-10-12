#!/bin/bash
###############################################################################
# Roxane OS - AI Models Download
# Downloads all required AI models for Roxane
###############################################################################

set -e

MODELS_DIR="/opt/roxane/data/models"
CACHE_DIR="/opt/roxane/data/cache"

echo "Downloading AI models..."

# Create directories
mkdir -p "$MODELS_DIR"
mkdir -p "$CACHE_DIR"
chown -R roxane:roxane /opt/roxane/data

# Install huggingface-cli
pip3 install huggingface-hub[cli]

# Function to download model
download_model() {
    local model_name=$1
    local local_dir=$2
    
    echo "📥 Downloading: $model_name"
    sudo -u roxane huggingface-cli download "$model_name" \
        --local-dir "$local_dir" \
        --local-dir-use-symlinks False
}

# 1. LLM Model (for development - lightweight)
echo ""
echo "=== Downloading Language Model ==="
download_model "TinyLlama/TinyLlama-1.1B-Chat-v1.0" "$MODELS_DIR/tinyllama-1.1b"

# For production with GPU:
# download_model "TheBloke/Llama-2-70B-GPTQ" "$MODELS_DIR/llama-2-70b-gptq"

# 2. Embedding Model
echo ""
echo "=== Downloading Embedding Model ==="
download_model "BAAI/bge-large-en-v1.5" "$MODELS_DIR/bge-large-en-v1.5"

# 3. Whisper Model (Speech-to-Text)
echo ""
echo "=== Downloading Whisper Model ==="
download_model "openai/whisper-large-v3" "$MODELS_DIR/whisper-large-v3"

# Alternative: smaller model for development
# download_model "openai/whisper-base" "$MODELS_DIR/whisper-base"

# 4. TTS Model (Text-to-Speech) - Coqui XTTS
echo ""
echo "=== Downloading TTS Model ==="
mkdir -p "$MODELS_DIR/coqui-xtts-v2"

# Download XTTS v2
sudo -u roxane pip3 install TTS

# Download model files
sudo -u roxane python3 << 'EOF'
from TTS.api import TTS
import os

model_path = "/opt/roxane/data/models/coqui-xtts-v2"
os.makedirs(model_path, exist_ok=True)

# Initialize TTS to download model
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
print("✅ XTTS v2 model downloaded")
EOF

# 5. VAD Model (Voice Activity Detection)
echo ""
echo "=== Downloading VAD Model ==="
download_model "snakers4/silero-vad" "$MODELS_DIR/silero-vad"

# 6. NER Model (Named Entity Recognition)
echo ""
echo "=== Downloading NER Model ==="
download_model "dslim/bert-base-NER" "$MODELS_DIR/bert-base-ner"

# Set permissions
chown -R roxane:roxane "$MODELS_DIR"
chown -R roxane:roxane "$CACHE_DIR"

# Create model info file
cat > "$MODELS_DIR/models.json" << EOF
{
  "llm": {
    "name": "TinyLlama-1.1B-Chat-v1.0",
    "path": "$MODELS_DIR/tinyllama-1.1b",
    "type": "causal-lm",
    "size": "1.1B"
  },
  "embeddings": {
    "name": "bge-large-en-v1.5",
    "path": "$MODELS_DIR/bge-large-en-v1.5",
    "dimension": 1024
  },
  "stt": {
    "name": "whisper-large-v3",
    "path": "$MODELS_DIR/whisper-large-v3",
    "languages": ["fr", "en"]
  },
  "tts": {
    "name": "xtts-v2",
    "path": "$MODELS_DIR/coqui-xtts-v2",
    "languages": ["fr", "en"]
  },
  "vad": {
    "name": "silero-vad",
    "path": "$MODELS_DIR/silero-vad"
  },
  "ner": {
    "name": "bert-base-NER",
    "path": "$MODELS_DIR/bert-base-ner"
  }
}
EOF

echo ""
echo "✅ All AI models downloaded successfully"
echo ""
echo "📁 Models directory: $MODELS_DIR"
du -sh "$MODELS_DIR"