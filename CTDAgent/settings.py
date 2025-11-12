"""설정 파일 (base + ctdmate 통합)"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (CTDAgent 디렉토리에서)
_current_dir = Path(__file__).parent
_env_path = _current_dir / ".env"
load_dotenv(_env_path)

# 로깅
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Llama (ReAct 플래너)
LLAMA_MODEL_PATH = os.getenv(
    "LLAMA_MODEL_PATH",
    "/home/ubuntu/라마/CTDMate/models/llama-3.2-3B-term-normalizer-F16.gguf"
)
LLAMA_CTX = int(os.getenv("LLAMA_CTX", "4096"))
LLAMA_THREADS = int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 8)))
LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "800"))

# Upstage (Solar/Parser)
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
UPSTAGE_MODEL = os.getenv("UPSTAGE_GEN_MODEL", "solar-pro2")
UPSTAGE_SPLIT = os.getenv("UPSTAGE_SPLIT", "page")
UPSTAGE_OUTFMT = os.getenv("UPSTAGE_OUTPUT_FORMAT", "pdf")

# Qdrant + E5
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "ctd")
E5_MODEL_NAME = os.getenv("E5_MODEL_NAME", "intfloat/multilingual-e5-large-instruct")
E5_QUERY_PREFIX = os.getenv("E5_QUERY_PREFIX", "query: ")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./data/qdrant_storage")

# Paths
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
JSONL_DIR = Path(os.getenv("JSONL_DIR", "./output"))
UPLOAD_MAX = int(os.getenv("MAX_FILES", "5"))

# RAG knobs
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_SIM_THRESHOLD = float(os.getenv("RAG_SIM_THRESHOLD", "0.78"))

# Generate gate
GENERATE_GATE = float(os.getenv("GENERATE_GATE", "0.65"))

print(f"✓ Settings loaded")
print(f"  - Llama model: {LLAMA_MODEL_PATH}")
print(f"  - Upstage API: {'configured' if UPSTAGE_API_KEY else 'missing'}")
print(f"  - Output dir: {OUTPUT_DIR}")
