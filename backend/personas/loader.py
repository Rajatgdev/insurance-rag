"""Load a persona system prompt by id (brian|ciara|darragh)."""
"""Load a persona voice skin by id. Personas change tone/emphasis, not the pipeline."""
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_DEFAULT = "You are a sharp, careful insurance co-pilot assisting a professional."


def load_persona(name: str = "generic") -> str:
    path = _DIR / f"{name}.md"
    return path.read_text() if path.exists() else _DEFAULT