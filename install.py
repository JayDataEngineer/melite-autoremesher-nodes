"""install.py — the ComfyUI-Manager install door for the autoremesher binary.

A pack install must converge the pack: Manager clones this repo and
runs this file, which fetches the pinned autoremesher binary release
asset into this pack's own native/ directory (sha256-verified — a
drifted asset is a refusal, never a silent pass) and marks it
executable. No estate tooling, no environment variables, no manual
steps: after Manager installs this pack, find_binary() resolves.

stdlib only — this runs before pip requirements converge.
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

TAG = "autoremesher-d9ef96bd"
URL = (
    "https://github.com/JayDataEngineer/melite-autoremesher-nodes/releases/download/"
    + TAG
    + "/autoremesher-asset"
)
SHA256 = "b84901ca07062a2c0ab7b1e0055e3d4c6fa2d5c6340b70576350ab542bc06161"

NATIVE_DIR = Path(__file__).resolve().parent / "native"
NATIVE_BIN = NATIVE_DIR / "autoremesher"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if NATIVE_BIN.is_file() and _sha256(NATIVE_BIN) == SHA256:
        os.chmod(NATIVE_BIN, 0o755)
        print(f"[melite autoremesher] binary already converged: {NATIVE_BIN}")
        return 0
    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = NATIVE_BIN.with_suffix(".download")
    print(f"[melite autoremesher] fetching binary {TAG} …")
    try:
        urllib.request.urlretrieve(URL, tmp)
    except Exception as exc:  # noqa: BLE001 — report every network shape once
        print(
            f"[melite autoremesher] FAILED to fetch {URL}: {exc}\n"
            "The binary is a pinned release asset of this pack's own repo —\n"
            "retry the install, or set AUTOREMESHER_BIN to a binary you built.",
            file=sys.stderr,
        )
        return 1
    got = _sha256(tmp)
    if got != SHA256:
        tmp.unlink(missing_ok=True)
        print(
            f"[melite autoremesher] REFUSED: sha256 mismatch for {TAG}\n"
            f"  expected {SHA256}\n  got      {got}\n"
            "A drifted asset never installs. Re-pin the pack.",
            file=sys.stderr,
        )
        return 1
    tmp.replace(NATIVE_BIN)
    os.chmod(NATIVE_BIN, 0o755)
    print(f"[melite autoremesher] binary installed: {NATIVE_BIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
