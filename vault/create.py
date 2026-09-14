"""Make a document only if it passes the schema. The write half of `lint`.

`new` shares `schema.validate` and `resolve_link` with `lint` on purpose -
a seconde copy of the rules would drift. What is added here lives outside
the frontmatter: the filename, the folder, a clashing name.
"""

import re
from collections import Counter
from pathlib import Path

from vault.frontmatter import fm_get, fm_list, split_frontmatter
from vault.graph import in_graph
from vault.links import link_target
from vault.scan import nfc, resolve_link, scan_vault
from vault.schema import validate

# `|` is banned in note names; `#`/`^` are link separators; the rest break
# the path or the parser. A name carrying one makes an unlikable note.
BAD_NAME = re.compile(r'[`\[\]|#^\\/:*?"<>]')


def build_frontmatter(type_, summary, builds_on, created, supersedes=None, extra=None):
    """Frontmatter text in schema order: type, summary, relations, created.

    A bare target is wrapped: `Base` becomes `[[Base]]`. Extra holds
    unrecognized domain fields from an ingested draft.
    """
    lines = [f"type: {type_}"]
    if summary:
        lines.append(f"summary: {summary}")
    for _, block in (extra or []):
        lines.append(block.rstrip())
    for field, items in (("builds_on", builds_on), ("supersedes", supersedes)):
        if items:
            lines.append(f"{field}:")
            for item in items:
                item = item.strip()
                if not (item.startswith("[[") and item.endswith("]]")):
                    item = f"[[{item}]]"
                lines.append(f'  - "{item}"')
    lines.append(f"created: {created}")
    return "\n".join(lines)


def check_new(root, relative, fm, body, force=False):
    """Every reason this document must not be written, as (code, detail).

    Empty means safe to write. `builds_on` must resolve - it names a
    document you build upon, so that document has to exist. `supersedes`
    must NOT: it names what this note replaces, usually a deleted one, and
    an unresolved supersedes is the noramal case, not a fault (Phase 6).
    """
    problems = list(validate(fm))

    _, index, targets = scan_vault(Path(root))
    for item in fm_list(fm, "builds_on"):
        if resolve_link(link_target(item), index, targets, source=relative) is None:
            problems.append(("builds_on unresolved", item))

    name = relative.rsplit("/", 1)[-1].removesuffix(".md")
    bad = BAD_NAME.search(name)
    if bad:
        problems.append(("bad filename char", bad.group(0)))
    if not body.strip():
        problems.append(("empty body", ""))

    destination = Path(root) / relative
    if not force:
        if destination.exists():
            problems.append(("file exists", relative))
        # A name already in the vault makes any link to it ambiguous.
        if nfc(name) in index:
            problems.append(("duplicate filename", name))

    if not destination.parent.is_dir():
        problems.append(("missing direcotry", relative.rsplit("/", 1)[0]))

    return problems



# Routing, level 2 of the schema doc's three: warn when `--type` is a first
# for the folder it is going into. Never refuse - the folder/type map is not
# total (`case` lives in 200 and in 300 alike), so a first can be right.
#
# The old CLI kept this as a hand-written table (reference/vault.py
# ZONE_TYPES / SUBDIR_TYPES) "drawn from the vault's real distribution".
# Frozen, it rotted in three weeks: `209 Principles` became 299 and
# `template` left the schema. So the vault IS the table now, read at call
# time. Measured 2026-09-03: 90% of documents carry their folder's majority
# type and 496 of 752 folders hold a single type, which is what makes a
# first-of-its-kind worth one line.
ROUTING_MIN_DOCS = 5


def routing_warning(root, relative, type_, minimum=ROUTING_MIN_DOCS):
    """One line when `type_` has never appeared where `relative` is going.

    None when it fits, or when there is too little around to say. The
    narrowest folder with at least `minimum` typed documents speaks; a thin
    sub-folder defers to its parent, up to the zone. Documents the graph
    excludes (templates, the archive) do not count as neighbours.
    """
    directory = relative.rsplit("/", 1)[0] if "/" in relative else ""
    if not directory:
        return None
    parts = directory.split("/")
    zone = parts[0]

    root = Path(root)
    notes, _, _ = scan_vault(root)
    types = {}
    for note in notes:
        if note == relative or not note.startswith(zone + "/") or not in_graph(note):
            continue
        fm, _ = split_frontmatter((root / note).read_text(encoding="utf-8"))
        if kind := fm_get(fm, "type"):
            types[note] = kind

    for depth in range(len(parts), 0, -1):
        prefix = "/".join(parts[:depth])
        seen = Counter(kind for note, kind in types.items() if note.startswith(prefix + "/"))
        total = sum(seen.values())
        if total < minimum:
            continue
        if seen.get(type_):
            return None
        kinds = " · ".join(f"{kind} {n}" for kind, n in seen.most_common())
        return f"{prefix} 의 문서 {total}개는 {kinds} 다. `{type_}` 는 여기서 처음이다 — 맞으면 그대로 둔다"
    return None
