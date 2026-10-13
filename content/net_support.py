"""Simulators for the Phase 7 lessons, loaded from content/sim/. Not a lesson module."""
from pathlib import Path

from auto_support import needs

SIM = Path(__file__).parent / "sim"


def sim(*names):
    """Supporting-files dict for the given simulator files (tools go under bin/)."""
    out = {}
    for name in names:
        text = (SIM / name).read_text()
        out[f"bin/{name}" if "." not in name else name] = text
    return out


__all__ = ["needs", "sim"]
