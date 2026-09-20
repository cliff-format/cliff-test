"""The two CLIFF readings a caller can ask for.

CLIFF 1.1 defines a tolerant parsing mode for one consumer: an automated
translation pipeline that must not lose a translation because a model
punctuated a line differently (specification Appendix C). Strict parsing is
unchanged by that appendix and remains the reference-toolchain reading.

Both readings are legitimate and answer different questions, so the mode is
always explicit and always travels with the number it produced (Appendix C.1:
"the mode in effect MUST be observable by the caller"). This module exists so
the run configuration and the answer reader share one definition of the two
values instead of each spelling them out.
"""

from __future__ import annotations

STRICT = "strict"
TOLERANT = "tolerant"

#: Every reading the harness supports, in the order they are offered.
READ_MODES: tuple[str, ...] = (STRICT, TOLERANT)

#: The reading a translation pipeline uses unless a caller says otherwise.
DEFAULT_READ_MODE = TOLERANT


def is_tolerant(read_mode: str) -> bool:
    """Whether ``read_mode`` selects the Appendix C reading."""
    return validate(read_mode) == TOLERANT


def validate(read_mode: str) -> str:
    """Return ``read_mode`` if it is supported, raise otherwise.

    A typo must fail loudly: silently scoring a run under the wrong reading
    would make every number in its report unreadable.
    """
    if read_mode not in READ_MODES:
        raise ValueError(
            f"read_mode must be one of {', '.join(READ_MODES)}, got '{read_mode}'"
        )
    return read_mode
