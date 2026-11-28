"""A tracked file must keep the line-ending style (CRLF or LF) it has in the last commit.

Two commits on 26-28 Nov 2026 accidentally converted CRLF files to LF, turning a few
changed lines into a whole-file diff. .gitattributes stops git from converting; this
test catches a conversion done on disk by an editor or script, before it is committed.
"""
import subprocess

import pytest

from agents.reference_data import ROOT


def _git(*args, text=True):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=text, check=True).stdout


def _style(data):
    if b"\0" in data[:8000]:
        return None                       # binary
    crlf = data.count(b"\r\n")
    lone_lf = data.count(b"\n") - crlf
    if crlf and lone_lf:
        return "mixed"
    return "crlf" if crlf else "lf"


def _tracked():
    try:
        return [f for f in _git("ls-files").splitlines() if f]
    except Exception:  # noqa: BLE001
        return []


def test_line_endings_unchanged_since_last_commit():
    files = _tracked()
    if not files:
        pytest.skip("not a git checkout")
    changed = []
    for f in files:
        path = ROOT / f
        if not path.exists():
            continue
        try:
            head = _git("show", f"HEAD:{f}", text=False)
        except subprocess.CalledProcessError:
            continue                      # new file, not in HEAD yet
        before, after = _style(head), _style(path.read_bytes())
        if before and after and before != after and "\n" in head.decode("utf-8", "ignore"):
            changed.append(f"{f}: {before} -> {after}")
    assert not changed, "line endings changed (restore them before committing):\n" + "\n".join(changed)


def test_gitattributes_preserves_line_endings():
    assert "* -text" in (ROOT / ".gitattributes").read_text()
