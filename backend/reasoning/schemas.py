"""Structured outputs for the co-pilot.

Shared:
  - Citation           one cited clause (insurer, section, page, one-line detail)
  - Triage             cheap pre-pass (kept for the current single-insurer answerer)
  - PersonaAnswer      base: every persona can EITHER clarify or answer, in one call

Per-persona answer shapes (selected by persona.output_kind):
  - VerdictResponse      Ciara (claims): cited coverage verdict + excess
  - WordingReadResponse  Brian (underwriter): veteran read of one wording
  - ComparisonResponse   Darragh (broker): cited cross-insurer comparison matrix

CoPilotResponse is retained until the answerer is migrated (step 2), so nothing breaks.
"""
from typing import Literal

from pydantic import BaseModel, Field


# ── shared ────────────────────────────────────────────────────────────────
class Citation(BaseModel):
    insurer: str
    section: str
    page: int | None = None
    detail: str = Field(description="What this clause says, in one line, in your own words.")


class Triage(BaseModel):
    """Cheap first pass: figure out which policy we're dealing with before retrieving."""
    insurer: str | None = Field(
        default=None,
        description="Exact insurer name from the allowed list if the user has named one "
                    "anywhere in the conversation, otherwise null.",
    )
    issue: str = Field(description="The coverage question/topic in a few words, e.g. 'windscreen damage'.")


class PersonaAnswer(BaseModel):
    """Base every persona answer inherits: clarify OR answer, decided in one call."""
    mode: Literal["clarify", "answer"]
    questions: list[str] = Field(
        default_factory=list,
        description="When mode='clarify': 1-3 sharp questions whose answers change the outcome, "
                    "grounded in the actual exclusions/conditions of the retrieved wording.",
    )


# ── Ciara — claims: cited coverage verdict ────────────────────────────────
class VerdictResponse(PersonaAnswer):
    verdict: Literal["Covered", "Not covered", "Partial", "Unclear"] | None = None
    answer: str | None = Field(
        default=None,
        description="Reasoning: grant of cover, then section exceptions, then general "
                    "exclusions, then the conclusion. Grounded only in the context.",
    )
    excess: str | None = Field(
        default=None,
        description="The excess/deductible that would apply to this claim, if stated.",
    )
    citations: list[Citation] = Field(default_factory=list)
    exclusions_checked: list[str] = Field(
        default_factory=list,
        description="The exclusions/conditions you checked before concluding.",
    )
    confidence: float | None = Field(default=None, description="0.0-1.0 confidence in the verdict.")


# ── Brian — underwriter: veteran read of one wording ──────────────────────
class WordingReadResponse(PersonaAnswer):
    summary: str | None = Field(default=None, description="What this cover does, in plain English.")
    grants: list[str] = Field(default_factory=list, description="The cover actually granted.")
    notable_exclusions: list[Citation] = Field(
        default_factory=list, description="Exclusions a veteran would circle, each cited.")
    warranties_conditions: list[Citation] = Field(
        default_factory=list, description="Conditions/warranties that must be met, each cited.")
    gaps: list[str] = Field(
        default_factory=list, description="Cover that is limited, absent, or easily assumed but not present.")
    endorsements_plain: list[str] = Field(
        default_factory=list, description="Any endorsements decoded into plain English.")
    citations: list[Citation] = Field(default_factory=list)
    confidence: float | None = Field(default=None)


# ── Darragh — broker: cited cross-insurer comparison ──────────────────────
class ComparisonCell(BaseModel):
    insurer: str
    value: str = Field(description="This insurer's position on the dimension, in a few words.")
    section: str | None = None
    page: int | None = None
    is_gap: bool = Field(default=False, description="True where this insurer is materially weaker or silent.")


class ComparisonRow(BaseModel):
    dimension: str = Field(description="One coverage dimension, e.g. 'Windscreen replacement limit'.")
    cells: list[ComparisonCell] = Field(description="One cell per compared insurer, in column order.")


class ComparisonResponse(PersonaAnswer):
    topic: str | None = Field(default=None, description="The coverage topic being compared.")
    insurers: list[str] = Field(default_factory=list, description="Insurers compared, in column order.")
    rows: list[ComparisonRow] = Field(default_factory=list)
    gaps: list[str] = Field(
        default_factory=list, description="Notable cross-insurer variances a broker should raise.")
    summary: str | None = Field(default=None, description="Client-ready read of the differences.")
    confidence: float | None = Field(default=None)


# ── retained until answerer migration (step 2) ────────────────────────────
class CoPilotResponse(PersonaAnswer):
    verdict: Literal["Covered", "Not covered", "Partial", "Unclear"] | None = None
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    exclusions_checked: list[str] = Field(default_factory=list)
    confidence: float | None = None