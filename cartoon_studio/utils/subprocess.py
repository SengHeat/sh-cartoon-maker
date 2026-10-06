from __future__ import annotations

import subprocess
from collections.abc import Sequence


class CommandError(RuntimeError):
    pass


def run_checked(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise CommandError(f"Command failed ({result.returncode}): {' '.join(command)}\n{message}")
    return result

