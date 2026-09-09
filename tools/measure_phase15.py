"""Check the built graph against the gold set answers.

Phase 15's first completion condition — "reproduce the asserted graph of the
reference data exactly". The answers were written by hand in Phase 12 and
live in `docs/part3/gold-set-answers.md`; this reads them back and asks the
graph for each one.

Not a unit test: it needs the real vault and a built `.vault.ttl`.

    uv run python -m vault rdf
    uv run python -m tools.measure_phase15
"""

import re
from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal

from vault.frontmatter import split_frontmatter
from vault.graph import in_graph
from vault.links import link_parts
from vault.rdf import RESOLVED, TTL_NAME, V, doc_iri, section_iri, sentinel
from vault.scan import nfc, resolve_link, scan_vault
from vault.sections import item_headings, resolve_anchor

VAULT = Path.home() / (
    "Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
)
ANSWERS = Path(__file__).parent.parent / "docs/part3/gold-set-answers.md"

# A document heading, then its relations in a yaml fence. `answers.py` wrote
# the file in this shape, so the same shape reads it back.
BLOCK = re.compile(r"\*\*`([^`]+)`\*\*[^\n]*\n\n```yaml\n(.*?)```", re.S)
KEY = re.compile(r"^(\w+):")
LINK = re.compile(r'^\s+-\s+"?\[\[(.+?)\]\]"?\s*$')
BARE = re.compile(r"^\s+-\s+(\S+)\s*$")


def answers():
    """Yield (document name, relation, target) for every hand-written fact."""
    for name, block in BLOCK.findall(ANSWERS.read_text(encoding="utf-8")):
        relation = None
        for line in block.split("\n"):
            if match := KEY.match(line):
                relation = match.group(1)
            elif match := LINK.match(line):
                yield name, relation, match.group(1)
            elif match := BARE.match(line):
                # `derived_from: experience` — a source that is not a file.
                yield name, relation, match.group(1)


def main():
    graph = Graph().parse(VAULT / TTL_NAME, format="turtle")
    notes, index, targets = scan_vault(VAULT)
    inside = [note for note in notes if in_graph(note)]
    is_node = set(inside)
    headings = {
        note: item_headings(
            split_frontmatter((VAULT / note).read_text(encoding="utf-8"))[1]
        )
        for note in inside
    }

    def land(name, source=""):
        found = resolve_link(nfc(link_parts(name)[0]), index, targets, source=source)
        return found if found in is_node else None

    found = Counter()
    missing = []
    for name, relation, target in answers():
        source = land(name)
        if source is None:
            missing.append((name, relation, target, "출처 문서를 못 찾음"))
            continue

        # A source that is not a document, before anything is looked up —
        # the order `rdf._edge` uses. Asking the same question through the
        # same function is the point: this check read `experience` as a
        # broken link for as long as it duplicated the answer instead.
        outside = sentinel(target)
        if outside is not None:
            predicate, object_ = RESOLVED[relation], outside
        else:
            document, anchor = link_parts(target)
            landed = land(target, source)
            item = resolve_anchor(headings.get(landed, ()), anchor) if landed else None
            if item:
                predicate, object_ = V[relation], section_iri(landed, item)
            elif landed and not anchor:
                predicate, object_ = V[relation], doc_iri(landed)
            else:
                predicate, object_ = V[relation + "_raw"], Literal(target)

        if (doc_iri(source), predicate, object_) in graph:
            found[relation] += 1
        else:
            missing.append((name, relation, target, "그래프에 없음"))

    total = sum(found.values()) + len(missing)
    print(
        f"gold set 답안 관계 {total}건   재현 {sum(found.values())} · 실패 {len(missing)}"
    )
    for relation, count in found.most_common():
        print(f"   {relation:16} {count}")
    for name, relation, target, why in missing:
        print(f"   ✗ {name[:30]:32} {relation:16} → {target[:38]:40} {why}")


if __name__ == "__main__":
    main()
