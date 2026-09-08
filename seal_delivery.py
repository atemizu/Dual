#!/usr/bin/env python3
# Copyright 2026 Helium Dual contributors.
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
# Modified: 2026-09-09 (source-publication preparation).
"""Maintainer step: copy the final refreshed patch and seal delivery hashes."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    text = args.patch.read_text()
    for marker in ("helium_dual_browser_mac.mm", "helium_dual_window_host_mac.mm",
                   "helium_dual_state.h", "chrome/test/data/webui/"):
        if marker not in text:
            raise SystemExit("Final patch is missing expected content: " + marker)
    destination = root / "helium-dual-window.patch"
    if args.patch.resolve() != destination:
        shutil.copyfile(args.patch, destination)
    lock = json.loads((root / "source-lock.json").read_text())
    lock["local_patch"] = {"path": destination.name,
                           "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    lock["status"] = "source-delivery-sealed; browser build/runtime status recorded separately"
    lock["delivery_files"] = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "source-lock.json" and "__pycache__" not in p.parts and ".git" not in p.parts
    }
    (root / "source-lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
    print("Sealed", len(lock["delivery_files"]), "files; patch", lock["local_patch"]["sha256"])


if __name__ == "__main__":
    main()
