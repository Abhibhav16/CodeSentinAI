import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import httpx

from autoreview.api import app
from autoreview.schemas import ReviewResult

# Initialize the FastAPI TestClient
client = TestClient(app)

def test_health_ok():
    """Test /health endpoint when Ollama server is reachable."""
    mock_response = httpx.Response(200, text="Ollama is running")
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/health")
        
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_unreachable():
    """Test /health endpoint when Ollama server is unreachable."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        response = client.get("/health")
        
    assert response.status_code == 200
    assert response.json() == {"status": "ollama_unreachable"}

def test_review_endpoint_mocked():
    """Test /review endpoint by mocking the LLM reviewer call."""
    mock_result = ReviewResult(
        submission_type="dsa_problem",
        summary="This is a mocked review summary for testing purposes.",
        overall_risk_level="low",
        findings=[
            {
                "category": "clean_code",
                "severity": "info",
                "line_start": 1,
                "line_end": 1,
                "description": "Mocked finding description.",
                "suggestion": "Mocked finding suggestion.",
                "confidence": 0.99
            }
        ]
    )
    
    with patch("autoreview.api.run_code_review") as mock_review:
        mock_review.return_value = mock_result
        
        # Call review endpoint using multipart form data
        response = client.post(
            "/review",
            data={
                "code": "def solve(x):\n    return x + 1",
                "mode": "dsa_problem",
                "question": "Does this work?"
            }
        )
        
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["submission_type"] == "dsa_problem"
    assert res_json["overall_risk_level"] == "low"
    assert len(res_json["findings"]) == 1
    assert res_json["findings"][0]["category"] == "clean_code"
    assert res_json["findings"][0]["confidence"] == 0.99
