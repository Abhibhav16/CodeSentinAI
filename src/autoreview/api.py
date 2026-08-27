import logging
from typing import Optional
import httpx
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from autoreview.config import OLLAMA_HOST
from autoreview.classifier import classify_content
from autoreview.ast_reducer import reduce_python_code
from autoreview.reviewer import run_code_review, OllamaConnectionError, ReviewError
from autoreview.schemas import ReviewResult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autoreview.api")

app = FastAPI(
    title="AutoReview-AI Web Backend",
    description="API server for performing local structured code auditing.",
    version="0.1.0",
)

# Enable CORS for localhost and all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """
    Checks connection to local Ollama instance.
    Returns status: ok or ollama_unreachable.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Check Ollama directly (Ollama returns "Ollama is running" at the base url)
            response = await client.get(OLLAMA_HOST, timeout=2.0)
            if response.status_code == 200:
                return {"status": "ok"}
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            
    return {"status": "ollama_unreachable"}

@app.post("/review", response_model=ReviewResult)
async def review(
    code: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    question: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
):
    """
    Performs a structured code review on pasted code or an uploaded file.
    Reuses the same classifier, AST reducer, and reviewer logic as the CLI.
    """
    # 1. Resolve code content
    code_content = ""
    filename = "snippet.py"

    if file:
        try:
            file_bytes = await file.read()
            code_content = file_bytes.decode("utf-8")
            filename = file.filename or "uploaded_file.py"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read uploaded file: {e}"
            )
    elif code:
        code_content = code
        filename = "pasted_code.py"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either code block or file upload must be provided."
        )

    if not code_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided code content is empty."
        )

    # 2. Determine mode/submission_type
    submission_type = mode
    if not submission_type or submission_type == "auto":
        submission_type = classify_content(code_content, filename)
    else:
        valid_modes = ["dsa_problem", "pr_diff", "snippet"]
        if submission_type not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode '{submission_type}'. Must be one of {valid_modes}"
            )

    # 3. Apply AST reduction (only for Python files classified as DSA or Snippet)
    final_content = code_content
    is_python = filename.lower().endswith(".py")
    if submission_type in ("dsa_problem", "snippet") and is_python:
        try:
            reduced, orig_chars, red_chars = reduce_python_code(code_content)
            logger.info(f"API AST Reduction: {orig_chars} -> {red_chars} characters.")
            final_content = reduced
        except Exception as e:
            logger.warning(f"API AST reduction failed, using original code: {e}")
            final_content = code_content

    # 4. Trigger review call
    try:
        result = run_code_review(
            code_content=final_content,
            submission_type=submission_type,
            question=question,
        )
        return result
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ReviewError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during review: {e}"
        )
