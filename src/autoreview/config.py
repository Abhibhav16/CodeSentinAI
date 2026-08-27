import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
AUTOREVIEW_MODEL = os.getenv("AUTOREVIEW_MODEL", "qwen2.5-coder:7b")
