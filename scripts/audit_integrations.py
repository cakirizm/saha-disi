"""Read-only local integration audit. Never prints credential values.

Run with --signing inside Codemagic's appstore environment to require signing
variables. Local absence says nothing about values stored in Codemagic.
This is a limited pattern scan, not proof that every possible secret is absent.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SIGNING = (
    "APP_STORE_CONNECT_ISSUER_ID",
    "APP_STORE_CONNECT_KEY_IDENTIFIER",
    "APP_STORE_CONNECT_PRIVATE_KEY",
    "CERTIFICATE_PRIVATE_KEY",
)
PATTERNS = (
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"\bgithub_pat_[A-Za-z0-9_]{40,}\b",
    r"\bAIza[0-9A-Za-z_-]{35}\b",
    r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b",
)


def audit(require_signing=False):
    failures = []
    for key in SIGNING:
        present = bool(os.environ.get(key, "").strip())
        print(f"LOCAL {key}: {'present' if present else 'absent (remote unknown)'}")
        if require_signing and not present:
            failures.append(f"Missing signing variable: {key}")

    files = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    for name in filter(None, files):
        path = ROOT / name
        if not path.is_file():
            continue
        if path.suffix.lower() in {".p8", ".p12", ".pfx", ".pem", ".key", ".mobileprovision"} or (
            path.name.startswith(".env") and not path.name.endswith(".example")
        ):
            failures.append(f"Tracked credential file: {name}")
        data = path.read_bytes()
        if b"\0" not in data and any(re.search(pattern, data.decode("utf-8", errors="replace")) for pattern in PATTERNS):
            failures.append(f"Possible credential pattern: {name} (value hidden)")

    for name in (".env", "backend/.env.local", "AuthKey_test.p8", "distribution.p12", "private.pem", "test.mobileprovision"):
        result = subprocess.run(["git", "check-ignore", "--no-index", "-q", name], cwd=ROOT)
        if result.returncode != 0:
            failures.append(f"Credential path not ignored: {name}")

    with (ROOT / "ios/SahaDisi/Info.plist").open("rb") as stream:
        settings = plistlib.load(stream)
    if not settings.get("SahaDisiFeedURL", "").startswith("https://"):
        failures.append("Production feed URL must use HTTPS")

    feed = json.loads((ROOT / "backend/feed.json").read_text(encoding="utf-8"))
    health = json.loads((ROOT / "backend/collector_health.json").read_text(encoding="utf-8"))
    print(f"FEED snapshot: {feed.get('generated_at')}; commentators={len(feed.get('commentators', []))}; statements={len(feed.get('statements', []))}; matches={len(feed.get('matches', []))}")
    print(f"COLLECTOR snapshot: {health.get('generated_at')}; totals={json.dumps(health.get('totals', {}))}")
    for source in health.get("sources", []):
        if source.get("kind") == "youtube" and not source.get("candidates"):
            print("NOTE YouTube source produced no candidates; inspect transcript access and attribution, not just API keys.")
            break
    print("NOTE Network availability, remote secrets, signing validity and APNs delivery are not tested.")
    for failure in failures:
        print(f"FAIL {failure}")
    print("FAIL local configuration audit" if failures else "PASS local configuration audit (limited checks)")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signing", action="store_true", help="Require all four signing variables in this process")
    args = parser.parse_args()
    raise SystemExit(audit(args.signing))
