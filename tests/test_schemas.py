import pytest
from pydantic import ValidationError
from autoreview.schemas import ReviewResult, Finding

def test_valid_schema_parsing():
    valid_data = {
        "submission_type": "dsa_problem",
        "summary": "This is a brief 2-3 sentence overview of the submission. The algorithm is O(N) time complexity.",
        "overall_risk_level": "low",
        "findings": [
            {
                "category": "clean_code",
                "severity": "info",
                "line_start": 5,
                "line_end": 5,
                "description": "Consider adding type hints for completeness.",
                "suggestion": "Add typing annotations.",
                "confidence": 0.95
            }
        ]
    }
    
    result = ReviewResult(**valid_data)
    assert result.submission_type == "dsa_problem"
    assert result.overall_risk_level == "low"
    assert len(result.findings) == 1
    assert result.findings[0].category == "clean_code"
    assert result.findings[0].confidence == 0.95

def test_invalid_category_raises_error():
    invalid_data = {
        "submission_type": "snippet",
        "summary": "Summary",
        "overall_risk_level": "medium",
        "findings": [
            {
                "category": "invalid_category_name",  # Should trigger error
                "severity": "low",
                "line_start": 1,
                "line_end": 1,
                "description": "Desc",
                "suggestion": "Sug",
                "confidence": 0.8
            }
        ]
    }
    with pytest.raises(ValidationError):
        ReviewResult(**invalid_data)

def test_invalid_confidence_raises_error():
    invalid_data = {
        "submission_type": "snippet",
        "summary": "Summary",
        "overall_risk_level": "medium",
        "findings": [
            {
                "category": "bug",
                "severity": "low",
                "line_start": 1,
                "line_end": 1,
                "description": "Desc",
                "suggestion": "Sug",
                "confidence": 1.5  # Out of range (0.0 - 1.0)
            }
        ]
    }
    with pytest.raises(ValidationError):
        ReviewResult(**invalid_data)

def test_invalid_line_number_raises_error():
    invalid_data = {
        "submission_type": "snippet",
        "summary": "Summary",
        "overall_risk_level": "medium",
        "findings": [
            {
                "category": "bug",
                "severity": "low",
                "line_start": 0,  # Line number should be >= 1
                "line_end": 1,
                "description": "Desc",
                "suggestion": "Sug",
                "confidence": 0.8
            }
        ]
    }
    with pytest.raises(ValidationError):
        ReviewResult(**invalid_data)
