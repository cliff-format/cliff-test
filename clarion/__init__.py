"""CLARION - the CLIF format benchmark harness.

CLARION stands for *Contextual Localization Accuracy, Robustness,
Instruction-following and Overhead beNchmark*. It measures a localization file
format - not a model - along seven dimensions:

    D1  token cost, CLIF versus other formats in their plain form
    D2  token cost, CLIF versus other formats carrying the same context
    D3  translation quality, plain formats
    D4  translation quality, context-carrying formats
    D5  translation wall-clock cost, plain formats
    D6  translation wall-clock cost, context-carrying formats
    D7  format validity after LLM edits (cross-format edit robustness)

Every arm of every dimension is generated from ONE canonical CLIF document
through pyclif, so no format ever receives a hand-tuned advantage.
"""

from __future__ import annotations

__version__ = "0.1.0"

NAME = "CLARION"
FULL_NAME = (
    "Contextual Localization Accuracy, Robustness, "
    "Instruction-following and Overhead beNchmark"
)
CORPUS_NAME = "CLARION-Core"

__all__ = ["CORPUS_NAME", "FULL_NAME", "NAME", "__version__"]
