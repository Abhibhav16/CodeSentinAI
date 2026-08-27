from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class Finding(BaseModel):
    category: Literal["security", "bug", "architecture", "clean_code", "performance"]
    severity: Literal["info", "low", "medium", "high", "critical"]
    line_start: Optional[int] = Field(
        None, 
        description="The starting line number of the code segment related to this finding (1-indexed)."
    )
    line_end: Optional[int] = Field(
        None, 
        description="The ending line number of the code segment related to this finding (1-indexed)."
    )
    description: str = Field(
        ..., 
        description="Clear explanation of the problem, bug, security issue, or design pattern violation."
    )
    suggestion: str = Field(
        ..., 
        description="Actionable suggestion on how to fix or improve the code."
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Model self-reported confidence level (0.0 to 1.0)."
    )

    @field_validator("line_start", "line_end")
    @classmethod
    def validate_lines(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Line numbers must be 1-indexed (greater than or equal to 1).")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0 inclusive.")
        return v


class ReviewResult(BaseModel):
    submission_type: Literal["dsa_problem", "pr_diff", "snippet"]
    summary: str = Field(
        ..., 
        description="A 2-3 sentence high-level overview of the submission and key observations."
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="List of issues, improvements, or bugs identified during the review."
    )
    overall_risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., 
        description="Summary risk rating based on the findings."
    )
