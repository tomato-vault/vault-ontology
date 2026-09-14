"""Ingest an existing draft into the vault under schema compliance."""

from datetime import date
from pathlib import Path
import re
import sys

from vault.create import build_frontmatter, check_new, routing_warning
from vault.frontmatter import split_frontmatter
from vault.scan import nfc


def fm_blocks(fm):
    """Split frontmatter into (key, block_text) pairs preserving multi-line lists."""
    out, key, buf = [], None, []
    for line in (fm or "").splitlines():
        m = re.match(r"^([\w-]+):", line)
        if m:
            if key is not None:
                out.append((key, "\n".join(buf)))
            key, buf = m.group(1), [line]
        elif key is not None:
            buf.append(line)
    if key is not None:
        out.append((key, "\n".join(buf)))
    return out


def ingest_draft(
    vault_path: Path,
    draft_path: Path,
    dir_: str,
    type_: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    builds_on: list[str] | None = None,
    supersedes: list[str] | None = None,
    created: str | None = None,
    mkdir: bool = False,
    force: bool = False,
    rm: bool = False,
):
    """Ingest a draft into the vault. Return (relative_path, problems)."""
    vault = Path(vault_path)
    src = Path(draft_path)
    if not src.is_file():
        return None, [("missing draft", str(src))]

    raw = src.read_text(encoding="utf-8")
    fm0, body = split_frontmatter(raw)
    blocks = fm_blocks(fm0)
    have = {}
    for k, b in blocks:
        # scalar value
        m = re.match(r"^[\w-]+:[ \t]*(.*)$", b)
        have[k] = m.group(1).strip() if m else ""

    doc_type = type_ or have.get("type")
    if not doc_type:
        return None, [("type missing", "draft has no type and --type was not given")]

    doc_summary = (summary or have.get("summary", "")).strip()
    doc_created = created or have.get("created") or date.today().isoformat()
    doc_title = title or src.stem
    relative = nfc(str(Path(dir_) / f"{doc_title}.md"))

    # Keep domain fields that are not schema standard
    keep = [
        (k, b)
        for k, b in blocks
        if k not in ("type", "summary", "created", "builds_on", "supersedes")
    ]
    # builds_on / supersedes: command line flags take priority if provided, otherwise preserve draft's
    doc_builds_on = builds_on if builds_on else []
    doc_supersedes = supersedes if supersedes else []

    fm = build_frontmatter(
        type_=doc_type,
        summary=doc_summary,
        builds_on=doc_builds_on,
        created=doc_created,
        supersedes=doc_supersedes,
        extra=keep,
    )

    if mkdir:
        (vault / dir_).mkdir(parents=True, exist_ok=True)

    problems = check_new(vault, relative, fm, body, force=force)
    if problems:
        return relative, problems

    dest = vault / relative
    dest.write_text(
        "---\n" + fm + "\n---\n\n" + body.strip() + "\n", encoding="utf-8"
    )

    if rm:
        src.unlink()

    return relative, []
