"""Persona registry — a persona is an operating contract, not a voice.

Each Persona parameterises the same engine:
  - retrieval_mode : 'single_insurer' (Ciara, Brian) | 'multi_insurer' (Darragh)
  - output_kind    : selects the answer schema + the UI renderer
  - prompt_file    : the operating-contract system prompt (kept in personas/*.md)
  - disclaimer     : the decision-owner guardrail, stamped on every answer
"""
from dataclasses import dataclass
from pathlib import Path

from reasoning.schemas import VerdictResponse, WordingReadResponse, ComparisonResponse

_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    role: str
    lane: str                      # "claim" | "wording" | "comparison" — the work this persona owns
    retrieval_mode: str            # "single_insurer" | "multi_insurer"
    output_kind: str               # "verdict" | "wording_read" | "comparison"
    prompt_file: str
    disclaimer: str
    schema: type                   # the Pydantic answer model for this persona

    def prompt(self) -> str:
        return (_DIR / self.prompt_file).read_text()


PERSONAS: dict[str, Persona] = {
    "ciara": Persona(
        id="ciara", name="Ciara", role="Claims assessor", lane="claim",
        retrieval_mode="single_insurer", output_kind="verdict", prompt_file="ciara.md",
        disclaimer="Informational coverage read — the insurer makes the final claim decision.",
        schema=VerdictResponse,
    ),
    "brian": Persona(
        id="brian", name="Brian", role="Underwriter", lane="wording",
        retrieval_mode="single_insurer", output_kind="wording_read", prompt_file="brian.md",
        disclaimer="A reading of the wording, not a priced quote — the underwriter remains accountable.",
        schema=WordingReadResponse,
    ),
    "darragh": Persona(
        id="darragh", name="Darragh", role="Broker", lane="comparison",
        retrieval_mode="multi_insurer", output_kind="comparison", prompt_file="darragh.md",
        disclaimer="Supports comparison across insurers; the broker advises. Not a statement that "
                   "one policy is best. Aligned with IDD duties.",
        schema=ComparisonResponse,
    ),
}

DEFAULT_PERSONA = "ciara"

# lane -> persona id. One owner per lane; adding a persona self-registers its lane.
LANE_OWNER: dict[str, str] = {p.lane: p.id for p in PERSONAS.values()}


def get_persona(persona_id: str | None) -> Persona:
    """Resolve a persona id; unknown/None (incl. legacy 'generic') falls back to the default."""
    return PERSONAS.get(persona_id or "", PERSONAS[DEFAULT_PERSONA])


def persona_for_lane(lane: str) -> Persona | None:
    """The persona that owns a lane, if any."""
    owner = LANE_OWNER.get(lane)
    return PERSONAS[owner] if owner else None