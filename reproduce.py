#!/usr/bin/env python3
# Copyright 2026 Helium Dual contributors.
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
# Modified: 2026-09-09 (source-publication preparation).
"""Prepare or build the pinned private Helium Dual tree without global installs.

Preparation only accepts a dedicated checkout with no build/src directory.
It never deletes a source tree, installs applications, or launches the browser.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent


def fail(message):
    raise SystemExit(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(argv, *, cwd=None, env=None, capture=False):
    print("RUN", " ".join(str(arg) for arg in argv), flush=True)
    result = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env,
                            text=True, check=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def check_package(require_sealed=True):
    lock = json.loads((ROOT / "source-lock.json").read_text())
    if require_sealed and not lock.get("local_patch"):
        fail("Delivery is not sealed: maintainer must run seal_delivery.py first.")
    if lock.get("local_patch") and digest(ROOT / lock["local_patch"]["path"]) != lock["local_patch"]["sha256"]:
        fail("Local patch checksum mismatch")
    for name, expected in lock.get("delivery_files", {}).items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            fail("Delivery checksum mismatch: " + name)
    overlay = lock["fixture_overlay"]
    if digest(ROOT / overlay["path"]) != overlay["sha256"]:
        fail("Original test input archive checksum mismatch")
    return lock


def read_overlay():
    manifest = json.loads(
        (ROOT / "fixtures/original-test-inputs.manifest.json").read_text())
    expected = {entry["path"]: entry for entry in manifest["files"]}
    if len(expected) != 1270 or sum(e["bytes"] for e in expected.values()) != 12331656:
        fail("Unexpected original test input manifest")
    payloads = {}
    with tarfile.open(ROOT / "fixtures/original-test-inputs.tar.gz", "r:gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or ".." in name.parts
                    or name.parts[:3] != ("chrome", "test", "data")
                    or member.name not in expected or member.name in payloads):
                fail("Unexpected overlay archive member: " + member.name)
            entry = expected[member.name]
            if member.size != entry["bytes"]:
                fail("Overlay size mismatch: " + member.name)
            stream = archive.extractfile(member)
            if stream is None:
                fail("Cannot read overlay member: " + member.name)
            data = stream.read()
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                fail("Overlay content mismatch: " + member.name)
            payloads[member.name] = data
    if payloads.keys() != expected.keys():
        fail("Original test input archive is incomplete")
    return payloads


def restore_inputs(src):
    payloads = read_overlay()
    # Check every destination before writing the first file. This must run
    # before the local patch, whose fixture hunks intentionally change bytes.
    pending = []
    for name, data in payloads.items():
        destination = src / name
        if any(parent.is_symlink() for parent in destination.parents if parent != src.parent):
            fail("Symlink in overlay destination: " + name)
        if destination.exists():
            if not destination.is_file() or destination.is_symlink() or destination.read_bytes() != data:
                fail("Refusing to replace an existing different test input: " + name)
        else:
            pending.append((destination, data))
    for path, data in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
    print(f"Restored {len(pending)} missing original inputs; {1270-len(pending)} identical inputs retained.")


def check_checkout(repo, lock, *, clean):
    for path, key in ((repo, "helium_macos"), (repo / "helium-chromium", "helium_chromium")):
        actual = run(["git", "-C", path, "rev-parse", "HEAD"], capture=True)
        if actual != lock[key]["commit"]:
            fail(f"Wrong {key} pin: {actual}")
        if clean and run(["git", "-C", path, "status", "--porcelain", "--untracked-files=no"], capture=True):
            fail("Tracked files are modified; use a separate clean checkout: " + str(path))


def build_environment(args):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        fail("This reproduction configuration targets native macOS arm64.")
    env = os.environ.copy()
    env["PATH"] = str(args.python.parent) + os.pathsep + str(args.tools_bin) + os.pathsep + env["PATH"]
    env["DEVELOPER_DIR"] = str(args.developer_dir)
    for tool in ("git", "greadlink", "quilt", "ninja", "gpatch", "gsed", "patch", "diff"):
        if not shutil.which(tool, path=env["PATH"]):
            fail("Missing build tool in the supplied PATH: " + tool)
    for variable in ("SISO_REAPI_ADDRESS", "SISO_REAPI_INSTANCE", "RBE_service_no_security"):
        env.pop(variable, None)
    run([args.python, "-c", "import httplib2, requests, PIL, certifi"], env=env)
    cert = run([args.python, "-c", "import certifi; print(certifi.where())"], env=env, capture=True)
    env["SSL_CERT_FILE"] = cert
    env["REQUESTS_CA_BUNDLE"] = cert
    run(["/usr/bin/xcodebuild", "-version"], env=env)
    return env


def helium_function(repo, function, env):
    # zsh preserves the upstream scripts' sourced-file $0 convention.
    run(["/bin/zsh", "-f", "-c", 'set -e\nsource "$1/dev.sh"\n"$2"',
         "helium-dual", repo, function], cwd=repo, env=env)


def quilt_environment(repo, env):
    env = env.copy()
    env["QUILT_PATCHES"] = str(repo / "patches")
    env["QUILT_SERIES"] = "series.merged"
    return env


def prepare(args, lock, env):
    repo = args.repo
    src = repo / "build/src"
    if src.exists() or src.is_symlink():
        fail("Refusing an existing build/src; choose another dedicated checkout. No files removed.")
    if (repo / "patches/local/helium-dual-window.patch").exists():
        fail("Local patch is already present; use a clean checkout.")
    check_checkout(repo, lock, clean=True)
    if not args.archive:
        fail("prepare requires --archive with the downloaded pinned Chromium lite archive.")
    if args.archive.stat().st_size != lock["chromium"]["bytes"] or digest(args.archive) != lock["chromium"]["sha256"]:
        fail("Chromium lite archive SHA256/size mismatch; nothing extracted.")
    read_overlay()
    src.mkdir(parents=True)
    run(["/usr/bin/tar", "-xf", args.archive, "--strip-components=1", "-C", src], env=env)
    version = dict(line.split("=", 1) for line in (src / "chrome/VERSION").read_text().splitlines() if "=" in line)
    if ".".join(version[k] for k in ("MAJOR", "MINOR", "BUILD", "PATCH")) != lock["chromium"]["version"]:
        fail("Extracted Chromium version mismatch; source retained for inspection.")
    core = repo / "helium-chromium"
    cache = repo / "build/download_cache"
    cache.mkdir(exist_ok=True)
    for config in (repo / "downloads.ini", core / "deps.ini"):
        for action in ("retrieve", "unpack"):
            command = [args.python, core / "utils/downloads.py", action, "-i", config, "-c", cache]
            if action == "unpack":
                command.append(src)
            run(command, env=env)
    run([args.python, core / "utils/prune_binaries.py", src, core / "pruning.list"], env=env)
    helium_function(repo, "___helium_toolchain", env)
    (src / "out/Default").mkdir(parents=True, exist_ok=True)
    helium_function(repo, "___helium_resources", env)
    run([args.python, core / "utils/helium_version.py", "--tree", core,
         "--platform-tree", repo, "--chromium-tree", src], env=env)
    helium_function(repo, "___helium_patches_merge", env)
    qenv = quilt_environment(repo, env)
    run(["quilt", "--quiltrc=-", "push", "-a", "--refresh"], cwd=src, env=qenv)
    restore_inputs(src)
    patch = repo / "patches/local/helium-dual-window.patch"
    patch.parent.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / lock["local_patch"]["path"], patch)
    series = repo / "patches/series.merged"
    with series.open("a") as output:
        output.write("\nlocal/helium-dual-window.patch\n")
    run(["quilt", "--quiltrc=-", "push"], cwd=src, env=qenv)
    shutil.copyfile(ROOT / "args.gn", src / "out/Default/args.gn")
    stamp = {"patch_sha256": lock["local_patch"]["sha256"], "args_sha256": digest(ROOT / "args.gn")}
    (repo / "build/helium-dual-prepared.json").write_text(json.dumps(stamp, indent=2) + "\n")
    print("Prepared. Run the configure command next; no browser has been compiled or launched.")


def check_prepared(repo, lock):
    check_checkout(repo, lock, clean=False)
    stamp = json.loads((repo / "build/helium-dual-prepared.json").read_text())
    if stamp["patch_sha256"] != lock["local_patch"]["sha256"]:
        fail("Prepared tree belongs to a different delivery patch.")
    if digest(repo / "patches/local/helium-dual-window.patch") != lock["local_patch"]["sha256"]:
        fail("Checkout's local patch differs from the sealed delivery.")
    if digest(repo / "build/src/out/Default/args.gn") != digest(ROOT / "args.gn"):
        fail("Build args differ from this reproduction configuration.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-inputs", "prepare", "configure", "build"))
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--tools-bin", type=Path)
    parser.add_argument("--developer-dir", type=Path, default=Path("/Applications/Xcode.app/Contents/Developer"))
    parser.add_argument("--target", choices=("chrome", "helium_dual_state_smoke", "helium_dual_session_tests"), default="chrome")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    lock = check_package(require_sealed=args.command != "verify-inputs")
    if args.command == "verify-inputs":
        read_overlay()
        print("Verified all 1,270 original Chromium test inputs and package checksums.")
        return
    if not args.repo or not args.tools_bin:
        fail("Supply --repo and --tools-bin; dependencies are never installed globally.")
    # Keep the venv's python symlink path: resolving it would select the base
    # interpreter and lose the venv's packages and bin directory.
    args.python = args.python.expanduser().absolute()
    if not args.python.is_file():
        fail("Python executable does not exist: " + str(args.python))
    for name in ("repo", "tools_bin", "developer_dir"):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    if args.archive:
        args.archive = args.archive.resolve(strict=True)
    if args.jobs < 1:
        fail("--jobs must be positive.")
    env = build_environment(args)
    if args.command == "prepare":
        prepare(args, lock, env)
        return
    check_prepared(args.repo, lock)
    if args.command == "configure":
        helium_function(args.repo, "___helium_configure", env)
    else:
        src = args.repo / "build/src"
        env["SISO_PATH"] = str(src / "third_party/siso/cipd/siso")
        run([args.python, src / "third_party/depot_tools/autoninja.py", "-C", src / "out/Default",
             "-j", str(args.jobs), args.target], cwd=src, env=env)


if __name__ == "__main__":
    main()
