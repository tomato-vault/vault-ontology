"""Command line entry point: `python -m vault lint`."""

import argparse
import sqlite3
import json
import os
import sys
import time

from datetime import date, datetime
from collections import Counter
from pathlib import Path

from vault.create import build_frontmatter, check_new, routing_warning
from vault.doctor import run_doctor
from vault.ingest import ingest_draft


from vault.graph import (
    DB_NAME,
    build,
    by_tag,
    by_type,
    find,
    learning_path,
    near,
    orphans,
    stats,
)
from vault.ask import affected, crossing, evidence, lineage, render, review, together
from vault.lint import lint_vault
from vault.rdf import TTL_NAME, build_graph
from vault.shacl import findings, format_finding, shapes_graph, summarise
from vault.scan import nfc
from vault.schema import TYPES
from vault.tags import FREE, judge, tag_health, tag_vocabulary
from vault.template import list_templates, render_template


DEFAULT_VAULT = Path.home() / (
    "Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
)


def _parser():
    # One shared `--vault`, added to each leaf so it may follow the command
    # the way a person types it: `vault q stats --vault …`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", type=Path, default=DEFAULT_VAULT)

    parser = argparse.ArgumentParser(prog="vault")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("lint", parents=[common], help="check against the schema")
    commands.add_parser("build", parents=[common], help="write the graph")
    commands.add_parser("rdf", parents=[common], help="write the RDF graph")
    validate = commands.add_parser(
        "validate", parents=[common], help="check the graph against the shapes"
    )
    validate.add_argument(
        "--audit",
        action="store_true",
        help="report warnings too, not just violations",
    )
    tags = commands.add_parser(
        "tags", parents=[common], help="list the tag vocabulary (whitelist)"
    )
    tags.add_argument(
        "--health", action="store_true", help="diagnose the axes instead of listing"
    )
    tags.add_argument(
        "--judge", metavar="TAG", help="may this tag be added, and on what terms"
    )
    new = commands.add_parser(
        "new", parents=[common], help="create a document only if it passes"
    )
    new.add_argument("--type", required=True)
    new.add_argument("--title", required=True)
    new.add_argument("--dir", required=True)
    new.add_argument("--summary", default="")
    new.add_argument("--builds-on", dest="builds_on", action="append", default=[])
    new.add_argument("--supersedes", action="append", default=[])
    new.add_argument("--body")
    new.add_argument("--created")
    new.add_argument("--mkdir", action="store_true")

    tmpl = commands.add_parser(
        "template", parents=[common], help="render schema template or list templates"
    )
    tmpl.add_argument("type", nargs="?", help="document type")
    tmpl.add_argument("--list", action="store_true", help="list existing templates")
    tmpl.add_argument("--bare", action="store_true", help="omit hints and sample summary")

    ing = commands.add_parser(
        "ingest", parents=[common], help="ingest an existing draft into the vault"
    )
    ing.add_argument("draft", type=Path, help="path to draft markdown file")
    ing.add_argument("--dir", required=True, help="vault relative directory")
    ing.add_argument("--type", help="document type (defaults to draft frontmatter)")
    ing.add_argument("--title", help="document title (defaults to draft filename)")
    ing.add_argument("--summary", help="summary (defaults to draft frontmatter)")
    ing.add_argument("--builds-on", dest="builds_on", action="append", default=[])
    ing.add_argument("--supersedes", action="append", default=[])
    ing.add_argument("--created")
    ing.add_argument("--mkdir", action="store_true")
    ing.add_argument("--force", action="store_true")
    ing.add_argument("--rm", action="store_true", help="remove draft after ingesting")

    doc = commands.add_parser(
        "doctor", parents=[common], help="check for lost, evicted, or shrunk files"
    )
    doc.add_argument("--restore", action="store_true", help="restore missing files from git")

    # `q` asks the document graph — where a note sits, what it links to.



    # `ask` asks the semantic one — what a judgement rests on, and why.
    # Two groups because the answers have different shapes: `q` returns
    # paths, `ask` returns paths WITH the relation chain that found them.
    asks = commands.add_parser("ask", help="ask the semantic graph").add_subparsers(
        dest="question", required=True
    )
    for name in ("lineage", "evidence", "affected"):
        asks.add_parser(name, parents=[common]).add_argument("note")
    for name in ("review", "crossing", "together"):
        asks.add_parser(name, parents=[common])

    queries = commands.add_parser("q", help="ask the graph").add_subparsers(
        dest="query", required=True
    )
    queries.add_parser("stats", parents=[common])
    for name, argument in (
        ("path", "note"),
        ("near", "note"),
        ("type", "type"),
        ("tag", "tag"),
    ):
        queries.add_parser(name, parents=[common]).add_argument(argument)
    queries.add_parser("orphans", parents=[common]).add_argument("zone", nargs="?")
    queries.add_parser("sql", parents=[common]).add_argument("statement")
    return parser



def main(argv=None):
    """Run a command and return its exit code.

    0 clean · 1 violations found · 2 could not run. A tool that only
    prints cannot go in CI or a pre-commit hook; the exit code is the
    part a machine reads.
    """
    args = _parser().parse_args(argv)
    if not args.vault.is_dir():
        print(f"vault: no such directory: {args.vault}", file=sys.stderr)
        return 2

    if args.command == "lint":
        broken = lint_vault(args.vault)
        for path, code, detail in broken:
            print(f"{path}: {code}" + (f" — {detail}" if detail else ""))
        print(f"{len(broken):,} violations", file=sys.stderr)
        return 1 if broken else 0

    if args.command == "build":
        counts = stats(build(args.vault, args.vault / DB_NAME))
        print(
            f"{DB_NAME}  nodes {counts['node']:,} · edges {counts['edge']:,}"
            f" · tags {counts['tag']:,}"
        )
        for kind, n in sorted(counts["kinds"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:7,}  {kind}")
        print(f"  {counts['unresolved']:7,}  unresolved")
        return 0

    if args.command == "rdf":
        graph = build_graph(args.vault)
        graph.serialize(destination=args.vault / TTL_NAME, format="turtle")
        print(f"{TTL_NAME}  triples {len(graph):,}")
        for prefix, count in _predicate_counts(graph):
            print(f"  {count:7,}  {prefix}")
        return 0

    if args.command == "validate":
        # Built here, not read off disk: a stale `.vault.ttl` would let a
        # violation the author just introduced pass unseen.
        conforms, found = findings(build_graph(args.vault), shapes_graph())
        severities, messages = summarise(found)
        # Without `--audit` only violations print. The vault carries 99
        # warnings of accumulated debt, and a report nobody can finish
        # reading is a report nobody reads.
        shown = (
            found if args.audit else [f for f in found if f["severity"] == "violation"]
        )
        for finding in shown:
            print(format_finding(finding))
        counts = (
            " · ".join(f"{name} {n}" for name, n in severities.most_common()) or "없음"
        )
        print(f"\n{counts}", file=sys.stderr)
        if not args.audit and severities.get("warning"):
            print("--audit 으로 warning 까지 본다", file=sys.stderr)
        return 1 if severities.get("violation") else 0

    if args.command == "ask":
        return _ask(args)

    if args.command == "tags":
        return _tags(args)

    if args.command == "new":
        return _new(args)

    if args.command == "template":
        return _template(args)

    if args.command == "ingest":
        return _ingest(args)

    if args.command == "doctor":
        return _doctor(args)




    database = args.vault / DB_NAME
    if not database.exists():
        print(f"vault: {DB_NAME} not found. run `vault build` first.", file=sys.stderr)
        return 2
    return _query(sqlite3.connect(database), args)


def _tags(args):
    """List the vocabulary, diagnose it, or rule on one proposed tag."""
    if args.judge:
        vocabulary = dict(tag_vocabulary(args.vault))
        verdict, reason = judge(vocabulary, args.judge)
        print(f"{args.judge}\n  [{verdict}] {reason}")
        # 0 when it may be added as it stands, 1 when a person has to
        # decide. `known` is 1 too: nothing needs adding.
        return 0 if verdict == FREE else 1

    if args.health:
        for row in tag_health(args.vault):
            if not row["axis"]:
                for _, detail in row["signals"]:
                    print(f"\n{detail}")
                continue
            marks = "  ".join(f"[{kind}] {detail}" for kind, detail in row["signals"])
            print(
                f"{row['axis']:16} {row['kind']}  값 {row['values']:3} ·"
                f" 부착 {row['uses']:5,} · 고름 {row['spread']:.2f}"
                + (f"   {marks}" if marks else "")
            )
        return 0

    for tag, count in tag_vocabulary(args.vault):
        print(f"{count:6,}  {tag}")
    return 0


def _ask(args):
    """Answer a competency question. 0 answered · 1 nothing written yet.

    The graph is built here rather than read off disk, for the reason
    `validate` builds it: an answer from a stale file is worse than none.
    """
    started = time.perf_counter()
    graph = build_graph(args.vault)
    whole = {"review": review, "crossing": crossing, "together": together}
    note = getattr(args, "note", None)
    if args.question in whole:
        answer = whole[args.question](graph)
    else:
        node = _resolve(graph, args.vault, note)
        if node is None:
            print(f"vault: no such document: {note}", file=sys.stderr)
            _log_ask(args.question, note, "no_such_document", 0, started)
            return 2
        answer = {"lineage": lineage, "evidence": evidence, "affected": affected}[
            args.question
        ](graph, node)

    header = f"{answer.question}  {answer.subject}".strip()
    print(header + "\n")
    for line in render(answer):
        print(line)
    print(f"{len(answer.paths)} 경로 · {answer.status}", file=sys.stderr)
    _log_ask(args.question, note, answer.status, len(answer.paths), started)
    return 0 if answer else 1


def _log_ask(question, note, status, paths, started):
    """Append one line to $VAULT_ASK_LOG, when it is set. Otherwise nothing.

    Opt-in on purpose. The 2026-09-01 observation refused a log inside `ask`
    because a write side effect on an everyday command would have to be torn
    out when the observation ended. An environment variable has no side
    effect until someone sets it, and stays useful after: it is the only
    place a question asked from inside a Claude session leaves a trace —
    the shell history never sees those. What the answer was worth is still
    for a person to write down; this records that it was asked, and what
    came back.
    """
    path = os.environ.get("VAULT_ASK_LOG")
    if not path:
        return
    line = {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "question": question,
        "note": note,
        "status": status,
        "paths": paths,
        "ms": round((time.perf_counter() - started) * 1000),
    }
    with open(os.path.expanduser(path), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _resolve(graph, root, name):
    """Turn what a person typed into the node the graph knows."""
    from vault.rdf import doc_iri
    from vault.scan import resolve_link, scan_vault

    _, index, targets = scan_vault(root)
    landed = resolve_link(nfc(name), index, targets)
    if landed is None or not landed.endswith(".md"):
        return None
    node = doc_iri(landed)
    return node if (node, None, None) in graph else None


def _query(connection, args):
    if args.query == "stats":
        counts = stats(connection)
        for key in ("node", "edge", "tag", "unresolved"):
            print(f"  {counts[key]:7,}  {key}")
        for kind, n in sorted(counts["kinds"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:7,}  {kind}")
        return 0

    if args.query == "type":
        for path in by_type(connection, args.type):
            print(path)
        return 0

    if args.query == "tag":
        for path in by_tag(connection, args.tag):
            print(path)
        return 0

    if args.query == "orphans":
        for path in orphans(connection, args.zone):
            print(path)
        return 0

    if args.query == "sql":
        for row in connection.execute(args.statement):
            print("  " + " · ".join(str(v)[:60] for v in row))
        return 0

    start = find(connection, args.note)

    if start is None:
        print(f"vault: no such document: {args.note}", file=sys.stderr)
        return 2

    if args.query == "path":
        print(f"to understand {start}\n")
        for target, depth in learning_path(connection, start):
            print(f"  {depth}  {target}")
        return 0

    neighbours = near(connection, start)
    print(f"neighbours of {start}\n")
    for key in ("links_to", "linked_by"):
        print(f"  {key}")
        for path in neighbours[key]:
            print(f"      {path}")
    print("  shares_tag  (shared tags, most first)")
    for path, count in neighbours["shares_tag"][:20]:
        print(f"      {count}  {path}")
    return 0


def _new(args):
    """Write a document, or refuse and explain. 0 written · 1 rejected."""
    body = args.body if args.body is not None else sys.stdin.read()
    created = args.created or date.today().isoformat()
    relative = nfc(str(Path(args.dir) / f"{args.title}.md"))
    fm = build_frontmatter(
        args.type, args.summary.strip(), args.builds_on, created, args.supersedes
    )
    if args.mkdir:
        (args.vault / args.dir).mkdir(parents=True, exist_ok=True)

    problems = check_new(args.vault, relative, fm, body)
    if problems:
        print("not created — did not pass the schema.\n", file=sys.stderr)
        for code, detail in problems:
            print(f"  {code:<22}{(' ' + detail) if detail else ''}", file=sys.stderr)
        print(
            "\ntags are not added — add them yourself, from the existing vocabulary.",
            file=sys.stderr,
        )
        return 1

    (args.vault / relative).write_text(
        "---\n" + fm + "\n---\n\n" + body.strip() + "\n", encoding="utf-8"
    )
    print(f"created: {relative}")
    # A warning, not a refusal: the file is already written. Routing level 2.
    if warning := routing_warning(args.vault, relative, args.type):
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _template(args):
    """Render skeleton text or list vault templates. 0 clean · 2 error."""
    if args.list:
        rows = list_templates(args.vault)
        print(f"templates in vault — {len(rows)} found\n")
        for rel, s in rows:
            name = Path(rel).stem
            print(f"  {name}")
            if s:
                print(f"      {s[:74]}")
            print(f"      {rel}")
        return 0

    if not args.type:
        print("vault template: specify a type or --list", file=sys.stderr)
        return 2

    if args.type not in TYPES:
        print(f"vault template: unknown type: {args.type}", file=sys.stderr)
        print("  " + " ".join(sorted(TYPES)), file=sys.stderr)
        return 2

    print(render_template(args.type, bare=args.bare))
    return 0


def _ingest(args):
    """Ingest a draft document. 0 clean · 1 rejected · 2 error."""
    if not args.draft.is_file():
        print(f"vault ingest: no such draft: {args.draft}", file=sys.stderr)
        return 2

    relative, problems = ingest_draft(
        vault_path=args.vault,
        draft_path=args.draft,
        dir_=args.dir,
        type_=args.type,
        title=args.title,
        summary=args.summary,
        builds_on=args.builds_on,
        supersedes=args.supersedes,
        created=args.created,
        mkdir=args.mkdir,
        force=args.force,
        rm=args.rm,
    )
    if problems:
        print("not ingested — did not pass the schema.\n", file=sys.stderr)
        for code, detail in problems:
            print(f"  {code:<22}{(' ' + detail) if detail else ''}", file=sys.stderr)
        return 1

    print(f"ingested: {relative}")
    if warning := routing_warning(args.vault, relative, args.type):
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _doctor(args):
    """Diagnose lost, evicted, or shrunk files in the vault. 0 clean · 1 found issues · 2 error."""
    result = run_doctor(args.vault, restore=args.restore)
    if result is None:
        print(f"vault doctor: not a git repository: {args.vault}", file=sys.stderr)
        return 2

    missing = result["missing"]
    icloud = result["icloud"]
    shrunk = result["shrunk"]
    restored = result["restored"]

    print(f"vault  {args.vault}\n")

    if icloud:
        print(f"■ iCloud evict 진행 중 — {len(icloud)}건")
        print("  내용이 클라우드로 내려갔다. 이대로 커밋하면 삭제로 기록된다.")
        for p in icloud[:20]:
            print(f"    {p}")
        if len(icloud) > 20:
            print(f"    … 외 {len(icloud) - 20}")
        print("  → 복구: brctl download <경로>  또는 Finder에서 열어 내려받기\n")

    if missing:
        print(f"■ git에는 있는데 디스크에 없음 — {len(missing)}건")
        for p in missing[:20]:
            print(f"    {p}")
        if len(missing) > 20:
            print(f"    … 외 {len(missing) - 20}")
        print("  → 복구: vault doctor --restore\n")

    if restored:
        print(f"■ git에서 복구됨 — {len(restored)}건")
        for p in restored[:20]:
            print(f"    {p}")
        print()

    if shrunk:
        print(f"■ 내용이 절반 아래로 줄어듦 — {len(shrunk)}건")
        print("  덮어쓰기 사고일 수 있다. 의도한 것이면 넘어가라.")
        for p, old, new in shrunk[:20]:
            print(f"    {old:>5} → {new:<5}줄  {p}")
        if len(shrunk) > 20:
            print(f"    … 외 {len(shrunk) - 20}")
        print("  → 원본: git show HEAD:<경로>\n")

    if not (missing or icloud or shrunk):
        print("남은 문제 없음.")
        return 0
    return 1





def _predicate_counts(graph):
    """Predicates by how often they are stated, most first."""
    counts = Counter(str(p).rsplit("/", 1)[-1].rsplit("#", 1)[-1] for _, p, _ in graph)
    return counts.most_common()


if __name__ == "__main__":
    sys.exit(main())
