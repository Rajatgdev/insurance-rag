"""Pydantic schemas for structured LLM outputs."""
"""Structured outputs for the co-pilot. The LLM must return one of these shapes exactly."""
from typing import Literal

from pydantic import BaseModel, Field


class Triage(BaseModel):
    """Cheap first pass: figure out which policy we're dealing with before retrieving."""
    insurer: str | None = Field(
        default=None,
        description="Exact insurer name from the allowed list if the user has named one "
                    "anywhere in the conversation, otherwise null.",
    )
    issue: str = Field(description="The coverage question/topic in a few words, e.g. 'windscreen damage'.")


class Citation(BaseModel):
    insurer: str
    section: str
    page: int | None = None
    detail: str = Field(description="What this clause says, in one line, in your own words.")


class CoPilotResponse(BaseModel):
    """Either narrowing questions (clarify) or a grounded verdict (answer)."""
    mode: Literal["clarify", "answer"]

    # mode == "clarify"
    questions: list[str] = Field(
        default_factory=list,
        description="1-3 sharp questions whose answers would change the coverage outcome. "
                    "Ground them in the actual exclusions/conditions of the retrieved policy.",
    )

    # mode == "answer"
    verdict: Literal["Covered", "Not covered", "Partial", "Unclear"] | None = None
    answer: str | None = Field(
        default=None,
        description="The reasoning: state the grant, then the section exceptions, then the "
                    "general exclusions, then the conclusion. Grounded only in the context.",
    )
    citations: list[Citation] = Field(default_factory=list)
    exclusions_checked: list[str] = Field(
        default_factory=list,
        description="Short list of the exclusions/conditions you checked before concluding.",
    )
    confidence: float | None = Field(default=None, description="0.0-1.0 confidence in the verdict.")