"""Check for lost, evicted, or shrunk files in the vault using git and filesystem."""

import os
from pathlib import Path
import subprocess

SHRINK_MIN_LINES = 20
SHRINK_RATIO = 0.5


class Git:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _run(self, *args):
        r = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
        )
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


    def lines(self, *args):
        return [l for l in self._run(*args).splitlines() if l]

    def show(self, rev, path):
        """File content at rev. None if not in git."""
        r = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{rev}:{path}"],
            capture_output=True,
        )
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def check_missing(g: Git):
    """Files tracked in git but missing from local disk."""
    return [p for p in g.lines("ls-files", "--deleted") if p.endswith(".md")]


def check_shrunk(g: Git, vault: Path, min_lines=SHRINK_MIN_LINES, ratio=SHRINK_RATIO):
    """Files whose lines dropped below ratio of HEAD."""
    out = []
    for p in g.lines("diff", "--name-only", "HEAD"):
        if not p.endswith(".md"):
            continue
        head = g.show("HEAD", p)
        if head is None:
            continue
        f = Path(vault) / p
        if not f.exists():
            continue
        old = len(head.splitlines())
        new = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        if old >= min_lines and new < old * ratio:
            out.append((p, old, new))
    return out


def check_icloud(vault: Path):
    """.icloud placeholder files indicating content eviction."""
    out = []
    vault_path = Path(vault)
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            if f.endswith(".icloud"):
                # `.name.md.icloud` -> `name.md`
                real = f[1:-7] if f.startswith(".") else f[:-7]
                out.append(str(Path(root).relative_to(vault_path) / real))
    return sorted(out)


def run_doctor(vault: Path, restore: bool = False):
    """Run all three checks and optionally restore missing files."""
    vault = Path(vault)
    if not (vault / ".git").exists():
        return None


    g = Git(vault)
    missing = check_missing(g)
    icloud = check_icloud(vault)
    shrunk = check_shrunk(g, vault)
    restored = []

    if restore and missing:
        subprocess.run(["git", "-C", str(vault), "checkout", "--", *missing], check=True)
        still_missing = check_missing(g)
        restored = [p for p in missing if p not in still_missing]
        missing = still_missing

    return {
        "missing": missing,
        "icloud": icloud,
        "shrunk": shrunk,
        "restored": restored,
    }
