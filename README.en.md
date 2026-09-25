# vault-ontology

[![Korean](https://img.shields.io/badge/lang-Korean-blue)](README.md)

> Turning 4,400+ Obsidian notes into a **graph a machine can read** — and learning ontology by hand while doing it.
> The same data gets modelled **twice**: once as a property graph, once as an RDF ontology.

## Highlights

- **The same vault, modelled twice** — Part 1 (Phases 1–5) is a SQLite property graph; Part 2 (Phases 6–9) is RDF · SPARQL · RDFS/OWL · inference. The same question ("what do I have to read before I can understand A?") gets solved three times: with a recursive CTE, with a SPARQL property path, and with a reasoner. **The answers must match and the expressiveness must not.** That gap *is* the difference between a knowledge graph and an ontology
- **Rewritten from scratch with the answer key sitting right there** — the working tool (`vault-cli`, 1,142 lines) is pinned in `reference/` as a commit snapshot. **It doesn't get opened until I'm stuck.** It only covers Phases 1–5; Part 2 has no answer key at all
- **Five places where my code and the answer key disagreed — mine was right in all five**: duplicate-name resolution (126 links) · a check the schema of record requires but the implementation never had (23) · image embeds reported as broken links (582) · `part_of` resolved by global name lookup (139) · tag counting (3,319)
- **The vault got improved before the code did** — schema of record v1.8 (added selection criteria for `builds_on`) · CLAUDE.md v2.43 · 13 dead tag vocabularies deleted · **a broken pre-commit hook restored** (a home-directory rename had broken its path, so it was blocking every commit while running none of the loss checks)
- **241 tests, zero external dependencies through Phase 5** — writing the parsers by hand was the point, so Part 1 uses only the standard library. `rdflib` and `owlrl` are used only in Part 2
- **Measurement is the verdict** — all-green unit tests mean nothing if the numbers come out different on the real vault. Part 1 hit five "silently wrong" failures; how to suspect them is collected in [`learnings/silent-failures.md`](learnings/silent-failures.md)

> **Current status**: Phases 1–9 complete (2026-08-25); Phases 10–19 planned.
> The Part 2 decision remains unchanged: SQLite is the operational choice and RDF/OWL remains
> an output for learning and interoperability. Part 3 is a separate semantic-ontology track for
> claims, events, decisions, principles, and their evidence—not a retrieval upgrade. Its scope is
> the whole vault: engineering knowledge, personal experience, reflection, philosophy, career,
> and life knowledge, with each context preserved while cross-domain connections are discovered.

---

## Why I Built This

I had a rough idea of what an ontology was. A recent conversation with colleagues filled in the details, and the whole time I kept thinking about my Obsidian vault.

The vault exists to be **a database of what I learn while building things**. It has 4,400+ notes, already tangled together by 11,624 wikilinks. To a human eye it is obviously a graph — but **there is no structure a machine can read.** I initially thought an ontology was exactly the tool for that gap. This project tests that hypothesis against the real vault.

So this repo does two things at once.

1. **Learn ontology properly** — this comes first. I'm here to find out how different *reading about it* and *building it* actually are
2. **Actually adopt it in my vault** — not toy data, the vault I use every day. If it turns out not to fit, "it doesn't fit" is a legitimate deliverable

There's a third motive underneath. `vault-cli`, the tool that already extracts the vault into SQLite, **works — but I didn't write it.** Claude did. It runs, and it still has places where it diverges from what I meant. So the parser, the resolver, and the graph builder get rebuilt from a blank file, and the existing code sits beside me **as a subject of review, not an authority.** "The schema of record says so" is where an argument starts, not where it ends.

In Part 1 that gap showed up on both sides: **the new code was better in places, and the vault itself got fixed in others.**

---

## What “Ontology” Means Here

“Ontology” points to three different ideas depending on context. Distinguishing them is necessary to explain what this project built and what it actually wanted.

| Sense | The question it asks | In this project |
|---|---|---|
| **1. Philosophical ontology** | What do we consider to exist in this world? | The vault contains notes, folders, tags, and 13 `type` values; folders and files are different kinds of things |
| **2. Gruber / knowledge-engineering ontology** | How do we state a shared conceptualisation explicitly and formally? | `vault-ontology.ttl` states RDFS/OWL axioms and is processed by a reasoner |
| **3. Operational ontology in industry** | How do data, logic, actions, and permissions drive real operations? | The original goal — helping an AI agent navigate the vault and choose what to do next — is closer to this sense |

**The project built sense 2, but the problem it wanted to solve was closer to sense 3.** It was not an attempt to force a collection of Markdown files into an ontology. It treated the vault as a **personal knowledge operating environment** in which notes, relationships, and rules work together, then tested whether a formal ontology was actually needed to make that environment machine-readable.

RDFS/OWL inference ultimately produced zero useful facts that SQLite could not already derive. Markdown therefore remains the source of truth, the SQLite graph remains the operational tool, and RDF/OWL remains an artefact for learning and interoperability. **Building sense 2 made it possible to identify what sense 3 actually needed.** The evidence behind that decision is in [`learnings/verdict.md`](learnings/verdict.md).

---

## Modelled Twice

```
            4,400+ markdown notes  (the source)
                     │
  Phase 1~3     parse         frontmatter · wikilinks · file index
                     │
  Phase 4       validate      "what you create must pass the check"
                     │
                     ▼
  Phase 5       SQLite graph — node / edge / tag        ← end of Part 1
                (a property graph)                        = Part 2's baseline
                     │
                     ▼
  Phase 6~9     RDF triples — SPARQL · RDFS/OWL/SKOS · inference
                (the ontology proper)
```

**One variable changes per step.** Everything Part 1 produces becomes the regression baseline for Phases 6–9.

The starting point was a single sentence already written into the schema design doc:

> **A property graph (Neo4j) is not an ontology.** No formal semantics, no reasoner. To learn ontology, the RDF family is the right place.

Which means the SQLite graph is **a knowledge graph, not an ontology.** Part 1 reproduces it by hand; Part 2 crosses over to the real thing. Modelling the same data twice is the only way that distinction ends up in my hands instead of in a sentence.

---

## How It's Built

```
RED       write the test → read the failure message with it
GREEN     minimum implementation → passing → commit
REFACTOR  look for improvements (deciding "there are none" is also a result) → separate commit
MEASURE   run it against the real vault and compare with the answer key
```

That last line is the verdict. **Green says "the implementation matches the tests." It never says "the tests are right."** Only real data knows that.

Parsers suit TDD unusually well, because every trap has the shape "for this input, that output." The **"I miscounted four times right here"** table from the `vault-cli` README became the test case list verbatim.

| Trap | Symptom | Phase |
|---|---|---|
| `\s*(.+)$` | `\s` eats the newline, so an empty `summary:` swallows the next line | 1 |
| `\|` inside a table | `[[note\|alias]]` leaves a trailing backslash on the target | 2 |
| `splitext` | `No.013 The Philosopher's Stone` → `No` + `.013 The Philosopher's Stone` | 3 |
| Unicode normalisation | macOS stores filenames as NFD. Links in the body are NFC | 3 |
| Case sensitivity | macOS does not distinguish `python` from `Python` | 3 |
| `2026-13-99` | Right shape, non-existent date | 4 |

"A string prefix doesn't know about boundaries" came up **five separate times**. The regex fragment reference lives in [`learnings/regex-reference.md`](learnings/regex-reference.md).

---

## Roadmap

### Part 1 — Property graph (answer key available)

| Phase | What gets built | What it teaches | Status |
|---|---|---|---|
| **1** | [frontmatter parser](docs/phases/phase01.md) | Text into structure — where regex stops | ✅ |
| **2** | [wikilink parser](docs/phases/phase02.md) | A parsing trap is a statistics error | ✅ |
| **3** | [scan · link resolution](docs/phases/phase03.md) | **A name is not an identifier** (NFC · case · duplicates) | ✅ |
| **4** | [validation = refusal](docs/phases/phase04.md) | Turning constraints into something checkable | ✅ |
| **5** | [SQLite graph](docs/phases/phase05.md) | Node/edge modelling · transitive closure via recursive CTE | ✅ |

### Part 2 — Ontology (no answer key)

| Phase | What gets built | What it teaches | Status |
|---|---|---|---|
| **6** | [remodel as RDF](docs/phases/phase06.md) | **IRI design** · namespaces · literal vs resource | ✅ |
| **7** | [SPARQL queries](docs/phases/phase07.md) | Graph patterns · property path `+` · inverse `^` | ✅ |
| **8** | [vocabulary design (RDFS/OWL/SKOS)](docs/phases/phase08.md) | **Writing the schema as data** · reusing standard vocabularies | ✅ |
| **9** | [inference (owlrl)](docs/phases/phase09.md) | Materialisation · **open world assumption** · measuring growth · the final call | ✅ |

### Part 3 — Semantic ontology and knowledge operations

| Phase | What gets built | Gate | Status |
|---|---|---|---|
| **10** | [Problem contract and competency questions](docs/phases/phase10.md) | 30 questions, every one adjudicated by running it | ✅ Delivered |
| **11** | [Labelling pilot](docs/phases/phase11.md) | 15 min per note · 60% agreement on relabel | In progress |
| **12** | [Semantic authoring contract and gold set](docs/phases/phase12.md) | 50 labelled notes with sustainable authoring cost | Planned |
| **13** | [Artifact/knowledge identity split](docs/phases/phase13.md) | Identity survives rename, move, split, and merge | Planned |
| **14** | [Core domain ontology](docs/phases/phase14.md) | Every term serves a competency question | Planned |
| **15** | [Semantic assertion graph](docs/phases/phase15.md) | Asserted, proposed, and inferred facts stay separate | Planned |
| **16** | [SHACL semantic contract](docs/phases/phase16.md) | Results match gold violations | Planned |
| **17** | [Purpose-bound inference and rules](docs/phases/phase17.md) | New answers are explainable and retractable | Planned |
| **18** | [Semantic queries and explanations](docs/phases/phase18.md) | Two-week real-use trial — **where part 3 ends** | Planned |
| **19** | [Proposal, approval, and retraction](docs/phases/phase19.md) | No unapproved fact contaminates the asserted graph | ⏸ Held |
| **20** | [Bounded knowledge operations](docs/phases/phase20.md) | Shadow mode, approval, audit, and rollback | ⏸ Held |

Phases 1–9 remain closed and preserved. The full Part 3 plan, risks, prerequisites, and stop rules
are in [`docs/README.md`](docs/README.md); [`docs/NEXT.md`](docs/NEXT.md) is the resume point.
Vector retrieval is a separate track and is not implemented by these phases.

“Whole vault” does not mean annotating every note up front. Measurement put **31% of the vault
outside part 3** — 914 transcribed book chapters are the author's words, not mine, and 700 Life Stack
is a dictionary rather than a set of judgements. 900 Archive is not deprecation but PARA's “interest
has faded”, so a question names the documents it needs instead of the band joining wholesale. Technical claims, personal beliefs, values, and interpretations retain different
epistemic status, perspective, and time context.
The current graph excludes `900 Archive`; Part 3 must reintroduce it behind an explicit read-only
archive boundary so past beliefs and decisions do not masquerade as current facts.

Per-phase guides are in [`docs/`](docs); Q&A and retrospectives are in [`learnings/`](learnings). [`docs/NEXT.md`](docs/NEXT.md) records the closed state and follow-up boundary.

### Success Criteria

"The code runs" is not a success criterion. There is a real risk this ends up as just one more tool, and the original project docs wrote that risk down themselves — **becoming a machine that turns organising knowledge into a way of postponing the actual work.** Going in with eyes open.

- [x] Phase 5 — did **hand-written code** reproduce the measured numbers?
- [x] Phase 8 — the 13 `type` values support a useful three-role hierarchy: Content, Imported, and Structural
- [x] Phase 9 — inference produced **zero useful facts that SQLite could not already derive at query time**
- [x] Final — a recursive CTE is enough for this vault; do not operate rdflib continuously

Part 3 has separate success criteria:

- [ ] Separate artifacts from knowledge entities and preserve stable identity.
- [ ] Answer competency questions the current graph cannot answer.
- [ ] Trace every semantic and derived fact back to source evidence.
- [ ] Keep proposed, inferred, and approved states separate and retractable.
- [ ] Demonstrate value greater than annotation and review cost in real use.
- [ ] Require shadow mode, preview, approval, audit, and rollback before writes.
- [ ] Explain evidence-backed connections across engineering, personal, philosophical, career,
      and life knowledge.

That last item is the real deliverable. The measured result separates the operational tool from the learning artefact.

---

## Part 1 Results (2026-08-21)

### Against the answer key

Both run on the same vault, on the same day.

| | This repo | Answer key | |
|---|---:|---:|---|
| **Nodes** | **3,981** | **3,981** | ✅ |
| **`builds_on`** | **396** | **396** | ✅ |
| **`supersedes`** | **3** | **3** | ✅ |
| `links_to` | 10,195 | 10,763 | answer key counts 568 attachments as edges |
| `part_of` | 1,017 | 1,152 | 139 wrong hits from its global name lookup |
| Tags | **3,319** | 0 | answer key reads tags from the body |

**Three axes match exactly, and on the three that diverge this repo is right.** The pass criterion moved from "everything matches" to **"every difference has a reason"** because of that last row: the answer key is a fixed 2026-08-11 snapshot, so after the 16 August tag consolidation its tag count is permanently zero. **The moving baseline wasn't just the vault — it was the answer key itself.**

Build 1.3s · query 55ms. Maximum `builds_on` depth is 7 — the Design System series comes out in order from `00` to `08`. **A curriculum nobody wrote down.**

### Where the answer key was wrong

| Phase | What | Scale |
|---|---|---:|
| 3 | Resolves duplicate names by name (it never took where the link came from) | 126 links |
| 4 | A "judgement-type summary" check exists in the schema of record but not in code | 23 |
| 4 | Image embeds reported as broken links (I stepped on this once too) | 582 |
| 5 | `part_of` resolved by global name lookup | 139 |
| 5 | Tags read from the body (11 August snapshot) | 3,319 |

### What's left besides code

| | |
|---|---|
| Vault schema of record v1.8 | Added selection criteria for `builds_on` — 3 qualifying conditions · 3 picking rules · 4 prohibitions |
| CLAUDE.md v2.43 | Relaxed tagging rules (within the existing vocabulary only · report when adding) |
| 13 dead tag vocabularies deleted · 8 conflicted copies cleaned up | |
| `.vault-lint.json` redesigned | Split link exclusions from frontmatter exclusions (coverage 89% → 100%) |
| **Restored a broken pre-commit hook** | A home-directory rename had broken its path, so it was **blocking every commit while running none of the loss checks** |

The Part 1 retrospective is in [`learnings/part1-retrospective.md`](learnings/part1-retrospective.md).

---

## Running It

```bash
uv sync
uv run pytest -v          # 241 passing is the correct starting point
```

The vault path defaults to `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault`, and every command accepts `--vault`.

```bash
uv run python -m vault lint          # violations against the schema of record (currently 354)
uv run python -m vault build         # rebuild .vault-graph.db — dropped and recreated every time

uv run python -m vault q stats
uv run python -m vault q path "CIDR"     # what to read first to understand this (recursive CTE)
uv run python -m vault q near "CIDR"     # links · backlinks · shared-tag neighbours
uv run python -m vault q type concept
uv run python -m vault q tag Stack/Python
uv run python -m vault q orphans 200     # notes nothing points at
```

Exit codes are `0` clean · `1` violations found · `2` could not run. **A tool that only prints cannot go in CI or a pre-commit hook.**

`q path` is the representative query. It walks `builds_on` up through multiple hops to produce a reading order. **Neither the filesystem nor grep can do this** — you can see one hop, but you cannot count a transitive closure.

### A few design decisions

| Decision | Reason |
|---|---|
| The graph is **derived**. Dropped and rebuilt every time | Markdown is the source. No MERGE, no constraints, no idempotency needed |
| `edge.dst` may be NULL, and `raw` is stored alongside it | **A broken link is a fact about the graph too.** Dropping it loses "what was this trying to point at" |
| Derivable facts are not stored | `part_of` is derived from the path at build time. No `updated` field either — git knows |
| Normalise **once, at the boundary** | 5,341 links (21.9%) hang on this |
| For duplicate names, fix the **resolver**, not the names | Don't put in the filename what the path already knows |
| Lint exclusions live in a **committed config file**, not in code | What was excluded, and why, is subject to audit |
| Defaults are empty | With no config, everything gets checked. The safe direction |

The full list is under "여기까지 오면서 확정한 것" in [`docs/NEXT.md`](docs/NEXT.md).

---

## Project Structure

```
vault-ontology/
├── vault/                  code — standard library only through Phase 5
│   ├── frontmatter.py      split_frontmatter · fm_get · fm_list
│   ├── links.py            link_target · strip_code · iter_links
│   ├── scan.py             scan_vault · resolve_link · duplicate names · case collisions
│   ├── schema.py           the schema of record, as code
│   ├── lint.py             lint_vault — validation against the schema
│   ├── graph.py            build · stats · by_type · by_tag · learning_path · near · orphans
│   └── __main__.py         CLI — lint · build · q
├── tests/                  241 of them
├── tools/                  per-phase measurement scripts
├── docs/                   phase guides — what gets built and why (+ NEXT.md)
├── learnings/              Q&A · retrospectives — what was actually learned
└── reference/              the answer key. vault-cli snapshot (21faa91, 2026-08-11)
```

### What `reference/` is

A copy of `vault-cli` (a single 1,142-line file written by Claude), taken **from the committed `HEAD`** rather than the working tree — the answer key has to be a state where the docs and the measured numbers agree with each other.

**It doesn't get opened until I'm stuck.** While the TDD cycle is running, the tests are the specification. Reading the answer first skips "why should it be written this way" and leaves only "how was it written."

There are three moments it may be opened: stuck for over 30 minutes · **the Phase 5 comparison (mandatory)** · after a phase closes, to compare. Full rules in [`reference/README.md`](reference/README.md).

**Phases 6–9 have no answer key.** Their baseline is the SQLite graph built by hand in Phase 5.

---

## Reading Order (if you're here to learn)

1. [`docs/README.md`](docs/README.md) — the full roadmap and success criteria
2. [`learnings/part1-retrospective.md`](learnings/part1-retrospective.md) — the difference between building it and reading about it
3. [`learnings/silent-failures.md`](learnings/silent-failures.md) — six ways to suspect a failure that **doesn't crash and produces plausible numbers**
4. [`docs/phase05.md`](docs/phases/phase05.md) — six lines of recursive CTE. Required reading before Phase 7's one-line `builds_on+` means anything
5. [`docs/phase06.md`](docs/phases/phase06.md) – [`phase09.md`](docs/phases/phase09.md) — the ontology proper
6. [`docs/NEXT.md`](docs/NEXT.md) — where things stand and what's next

> Note: `docs/` and `learnings/` are written in Korean.

---

## Tech Stack

| | |
|---|---|
| Python 3.14 · uv | |
| **Phases 1–5** | standard library only (`re` · `sqlite3` · `unicodedata` · `argparse`) |
| **Phase 6+** | `rdflib` (RDF · SPARQL) · `owlrl` (inference) |
| Tests | pytest — 241 |

Holding off on dependencies wasn't taste, it was the point. **Writing the parsers by hand is what Phases 1–5 are for**, and the constraint lifts in Phase 6, where that purpose ends.

---

## Related Projects & Articles

- [`repo-ontology (otlg)`](https://github.com/tomato-vault/repo-ontology): Executable ontology framework and CLI porting Palantir Foundry / AIP primitives (Objects, Links, Actions, Functions) into Git codebases.
- [Engineering Blog (tomato-vault.github.io)](https://tomato-vault.github.io): Technical essays on knowledge graphs, practical ontologies, and agentic workflows.

