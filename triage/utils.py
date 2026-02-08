import difflib
from typing import List


def unified_diff(original: str, modified: str, fromfile: str = "a", tofile: str = "b") -> str:
    """Return a unified diff between original and modified strings."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, mod_lines, fromfile=fromfile, tofile=tofile)
    return "".join(diff)
