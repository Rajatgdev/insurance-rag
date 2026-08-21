"""Structured outputs for the co-pilot.

Shared:
  - Citation           one cited clause (insurer, section, page, one-line detail)
  - Triage             cheap pre-pass (kept for the current single-insurer answerer)
  - PersonaAnswer      base: every persona can EITHER clarify or answer, in one call

Per-persona answer shapes (selected by persona.output_kind):
  - VerdictResponse      Ciara (claims): cited coverage verdict + excess
  - WordingReadResponse  Brian (underwriter): veteran read of one wording
  - ComparisonResponse   Darragh (broker): cited cross-insurer comparison matrix

Envelope wraps a persona answer with an AuditRecord — the E&O / IDD provenance trail that
OUR code assembles from the retrieved context (never the LLM).
"""
from typing import Literal

from pydantic import BaseModel, Field, SerializeAsAny


# ── shared ────────────────────────────────────────────────────────────────
class Citation(BaseModel):
    insurer: str
    section: str
    page: int | None = None
    detail: str = Field(description="What this clause says, in one line, in your own words.")


class Triage(BaseModel):
    """Cheap first pass for single-insurer personas: which one policy are we reading?"""
    insurer: str | None = Field(
        default=None,
        description="Exact insurer name from the allowed list if the user has named one "
                    "anywhere in the conversation, otherwise null.",
    )
    issue: str = Field(description="The coverage question/topic in a few words, e.g. 'windscreen damage'.")


class ComparisonTriage(BaseModel):
    """Cheap first pass for the broker: which insurers to compare, on what topic."""
    insurers: list[str] = Field(
        default_factory=list,
        description="The insurers the user named to compare, each an exact name from the allowed "
                    "list. Empty list means the user named none — compare all of them.",
    )
    issue: str = Field(description="The coverage topic to compare, in a few words, e.g. 'windscreen cover'.")


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


# ── audit record — assembled by OUR code, never the LLM ───────────────────
class ExaminedClause(BaseModel):
    """Metadata for one clause we put in front of the model (not the full text)."""
    insurer: str
    section: str | None = None
    page: int | None = None
    is_exclusion: bool = False


class AuditRecord(BaseModel):
    """Defensible E&O / IDD trail: what was asked, which policies were read, what grounded it.

    Built deterministically from the retrieved context — this is provenance, not model output,
    so it can be trusted as evidence of what was examined.
    """
    persona: str
    query: str
    insurers_examined: list[str] = Field(default_factory=list)
    clauses_examined: list[ExaminedClause] = Field(
        default_factory=list, description="Every clause put in context — proves the whole market was read.")
    clauses_examined_count: int = 0
    clauses_cited_count: int = 0
    timestamp: str = Field(description="UTC ISO-8601 time the answer was produced.")


class Envelope(BaseModel):
    """What the API returns: the persona's answer plus the audit trail that backs it.

    SerializeAsAny keeps every persona subclass's fields (verdict/excess, grants/gaps,
    rows/cells) instead of narrowing to the PersonaAnswer base.
    """
    persona: str
    output_kind: str
    answer: SerializeAsAny[PersonaAnswer]
    audit: AuditRecord