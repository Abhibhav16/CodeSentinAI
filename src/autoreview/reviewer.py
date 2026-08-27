import logging
import httpx
import instructor
from openai import OpenAI
from typing import Optional

from autoreview.config import OLLAMA_HOST, AUTOREVIEW_MODEL
from autoreview.schemas import ReviewResult

logger = logging.getLogger("autoreview.reviewer")

class OllamaConnectionError(Exception):
    """Raised when the Ollama server is unreachable."""
    pass

class ReviewError(Exception):
    """Raised when the LLM fails to produce valid structured output after retries."""
    pass

def get_instructor_client(host: str, model: str) -> instructor.Instructor:
    """
    Creates an instructor-wrapped client targeting the local Ollama instance.
    We target Ollama's OpenAI-compatible endpoint for maximum reliability.
    """
    # Ollama's OpenAI-compatible base URL is usually OLLAMA_HOST + "/v1"
    base_url = f"{host.rstrip('/')}/v1"
    
    # We patch OpenAI client with instructor
    client = instructor.from_openai(
        OpenAI(
            base_url=base_url,
            api_key="ollama",  # Required by OpenAI client but ignored by Ollama
        ),
        # Ollama supports JSON mode
        mode=instructor.Mode.JSON,
    )
    return client

def run_code_review(
    code_content: str,
    submission_type: str,
    question: Optional[str] = None,
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> ReviewResult:
    """
    Runs the code review using Ollama and instructor.
    """
    target_model = model or AUTOREVIEW_MODEL
    target_host = host or OLLAMA_HOST

    client = get_instructor_client(target_host, target_model)

    system_msg = (
        "You are a professional, senior software engineer and security auditor.\n"
        "Your task is to review the code submission and provide a structured, "
        "highly detailed code review. Focus on finding actual bugs, security "
        "vulnerabilities, architectural issues, clean code violations, and performance bottlenecks.\n"
        "Be extremely specific and precise. Ensure that 'line_start' and 'line_end' (1-indexed) "
        "refer exactly to the relevant lines in the provided code snippet or diff if applicable."
    )

    user_msg = f"Submission Type: {submission_type}\n\n"
    
    if submission_type == "pr_diff":
        user_msg += "--- GIT DIFF TO AUDIT ---\n"
    else:
        user_msg += "--- SOURCE CODE TO AUDIT ---\n"
        
    user_msg += f"{code_content}\n"
    user_msg += "---------------------------\n"

    if question:
        user_msg += f"\nUser Question/Context:\n{question}\n"

    logger.info(f"Sending review request to Ollama model '{target_model}' at '{target_host}'...")

    try:
        # Use instructor's patched client with automatic retries (max_retries=2)
        response = client.chat.completions.create(
            model=target_model,
            response_model=ReviewResult,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_retries=2,
        )
        return response
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        raise OllamaConnectionError(
            f"Could not connect to Ollama server at '{target_host}'.\n"
            f"Please make sure the Ollama daemon is running locally (e.g. run 'ollama serve') "
            f"and that you can access it."
        ) from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ReviewError(
                f"Model '{target_model}' was not found on your Ollama server.\n"
                f"Please pull it first by running: ollama pull {target_model}"
            ) from e
        logger.error(f"HTTP status error during review: {e}")
        raise ReviewError(f"Ollama server returned HTTP error: {e}") from e
    except Exception as e:
        # Catch validation or other instructor client errors
        logger.error(f"Instructor review failed: {e}")
        raise ReviewError(
            f"Failed to obtain a valid structured code review from the model.\n"
            f"Error details: {e}"
        ) from e
