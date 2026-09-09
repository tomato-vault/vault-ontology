"""Turn a vault note into RDF triples.

Identity is decided in `doc_iri` and nowhere else - see docs/iri-policy.md.
"""

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS, XSD

from vault.frontmatter import fm_get, fm_list, split_frontmatter
from vault.graph import in_graph
from vault.links import link_parts
from vault.scan import folder_note, resolve_link, scan_vault
from vault.sections import (
    item_date,
    item_headings,
    item_prefix,
    iter_links_by_item,
    resolve_anchor,
)

BASE = "https://tomato.vault/"
V = Namespace(BASE + "schema/")
DOC = Namespace(BASE + "doc/")
FOLDER = Namespace(BASE + "folder/")
TAG = Namespace(BASE + "tag/")
# Outside the vault. A namespace of its own, because these resolve to no
# file here and sharing `doc/` would make `doc_path` name one.
EXTERNAL = Namespace(BASE + "external/")
TTL_NAME = ".vault.ttl"

# An IRI carries most of Unicode, so Korean goes in as it is - that is what
# the `I` buys, and a readable IRI was half the reason paths were chosen at
# all. These few are structurally special and have to be escaped. A single
# `translate` pass, so escaping `%` cannot double-escape what follows.
ESCAPES = str.maketrans(
    {
        " ": "%20",
        "#": "%23",
        "?": "%3F",
        "%": "%25",
        '"': "%22",
        "<": "%3C",
        ">": "%3E",
        "\\": "%5C",
        "^": "%5E",
        "`": "%60",
        "{": "%7B",
        "}": "%7D",
        "|": "%7C",
    }
)

UNESCAPES = {code: chr(char) for char, code in ESCAPES.items()}


def doc_iri(relative):
    """Mint the IRI for a document. The ONE place identity is decided.

    Path based, per `docs/iri-policy.md`. The `/` stays a separator: encoding
    it would flatten the hierarchy out of the IRI. `.md` comes off, because
    the extension says how the note is stored and not what it is - the same
    document must survive a change of format.

    When the switch to a stable ID comes, this function is the whole cost.
    """
    return DOC[relative.removesuffix(".md").translate(ESCAPES)]


def _unescape(encoded):
    """Undo `ESCAPES`. Reversible only because escaping was one pass."""
    for code, char in UNESCAPES.items():
        encoded = encoded.replace(code, char)
    return encoded


def doc_path(iri):
    """Turn a document IRI back into its vault path. The inverse of `doc_iri`.

    Phase 7 needs it: SPARQL answers in IRIs, but a result has to line up
    with SQLite, which answers in paths. Reversible only because the escape
    was a single `translate` pass - see `doc_iri`.
    """
    return _unescape(str(iri).removeprefix(DOC)) + ".md"


def section_iri(relative, heading):
    """Mint the IRI for one item inside a document.

    A fragment on the document's own IRI, so the section is visibly part of
    it and no second namespace is needed. `#` is the separator and the ONLY
    unescaped one: a heading may hold its own `#` (Obsidian writes a nested
    anchor as `doc#outer#inner`) and that one is escaped like any other
    character. So the raw `#` in a section IRI always means the same thing.
    """
    return URIRef(f"{doc_iri(relative)}#{heading.translate(ESCAPES)}")


def section_path(iri):
    """Turn a section IRI back into (vault path, heading written in full).

    Step 5 asks for the round trip: a semantic fact has to lead back to the
    line it was read from, and that line is a heading in a file.
    """
    document, _, heading = str(iri).partition("#")
    return doc_path(document), _unescape(heading)


def folder_iri(path):
    """Mint the IRI for a folder.

    Same escaping as a document, a different namespace. Both can carry the
    same path: `200 Dev/Network` is a folder, and dropping `.md` from
    `200 Dev/Network/Network.md` yields a document one segment longer. The
    split guarantees they never collide.
    """
    return FOLDER[path.translate(ESCAPES)]


def tag_iri(tag):
    """Mint the IRI for a tag.

    The slash stays, so `tag:Stack/Python` reads the way it was written.
    That slash is for a human eye only — hierarchy is stated by
    `skos:broader`, never parsed back out of the IRI. Reading structure out
    of a name is what Phase 3 spent itself proving wrong.
    """
    return TAG[tag.translate(ESCAPES)]


def _class_name(type_):
    """`capture` becomes `CaptureDocument`.

    RDF names classes UpperCamelCase and properties lowerCamelCase, so the
    shape of a name says which of the two it is.

    The `Document` suffix is Phase 13's. `v:Principle` used to name the file
    whose `type:` is principle — but that reads as the principle itself,
    which is what the file is ABOUT, not what it IS. The suffix keeps the
    bare name free for the knowledge entity.
    """
    stem = "".join(part.capitalize() for part in type_.split("-"))
    # `project-doc` alone would stutter into ProjectDocDocument.
    return ("Project" if stem == "ProjectDoc" else stem) + "Document"


# Only 인사이트 has a class. Phase 14 declared v:Insight and v:Question and
# stopped there: `패턴` is the vault's most common item - 150 of them - and no
# competency question asks for one, so it stays a section with no class. A
# recorded hole, not an oversight.
#
# The type is ASSERTED, never inferred. Nothing in the data implies that a
# heading beginning `인사이트` is a belief; only the prefix says so, and the
# ontology says as much in its own comment.
ENTITY_CLASS = {"인사이트": "Insight"}

# The vault's 2026-08-31 alignment decided this: a `By Subquestion/` document
# keeps `type: reflection` and the builder reads the question off the path.
# A fact you can derive is not written into frontmatter twice.
SUBQUESTION = "By Subquestion/"

# Sources that are not documents. The authoring reference table names
# these, and before 2026-09-01 the builder honoured none of them - they
# fell through to `_raw`, the same predicate a broken link lands on. A
# deliberate value and a mistake were indistinguishable.
#
#   experience         it came out of work I did       -> v:experience
#   ext:repo/path      it lives outside the vault      -> external:repo/path
#
# Intercepted BEFORE resolution: `experience` is not a note name to look
# up, and looking it up is what put it on `_raw` in the first place.
EXPERIENCE = "experience"
EXTERNAL_PREFIX = "ext:"


def node_triples(relative, text):
    """Yield (subject, predicate, object) for one note's own facts.

    A missing field yields NO triple. RDF has no NULL - silence means
    "not stated", never "empty". The open world assumption arrives here,
    at the very first step.
    """
    subject = doc_iri(relative)
    fm, body = split_frontmatter(text)

    type_ = fm_get(fm, "type")
    if type_:
        # A resource, not a string. Phase 8 has to be able to say
        # `Concept rdfs:subClassOf Document`, and a literal can never be
        # a subject — so a literal here would end the conversation.
        yield subject, RDF.type, V[_class_name(type_)]

    # Frontmatter order: type, tags, summary, … — kept, so the triples read
    # in the same order the note does.
    for tag in fm_list(fm, "tags"):
        yield subject, DCTERMS.subject, tag_iri(tag)

    summary = fm_get(fm, "summary")
    if summary:
        yield subject, DCTERMS.abstract, Literal(summary)

    created = fm_get(fm, "created")
    if created:
        # Declaring a type is not checking it: `"2026-13-99"^^xsd:date`
        # serialises happily. Phase 4's lint is what refuses; the model
        # only states. That gap is the subject of Phase 9.
        yield subject, DCTERMS.created, Literal(created, datatype=XSD.date)

    if SUBQUESTION in relative:
        yield subject, RDF.type, V.Question

    # "I looked and found nothing", which is a different fact from saying
    # nothing at all. The ontology has carried this term since Phase 14
    # and the builder never emitted it; 0 documents write it today, so
    # this is the emitter waiting for the first one.
    if fm_get(fm, "source_unknown") in ("true", "True", "yes"):
        yield subject, V.source_unknown, Literal(True)

    for heading in item_headings(body):
        section = section_iri(relative, heading)
        # No `a v:Section` here. `dcterms:hasPart rdfs:range v:Section`
        # types it, the way isPartOf's range types folders - and Step 5
        # forbids stating what the graph already yields.
        yield subject, DCTERMS.hasPart, section

        entity = ENTITY_CLASS.get(item_prefix(heading))
        if entity:
            yield section, RDF.type, V[entity]

        # When the belief held, which the file's `created` cannot say:
        # 24 insights share one file date.
        as_of = item_date(heading)
        if as_of:
            yield section, V.as_of, Literal(as_of, datatype=XSD.date)


# The document relations, unchanged since Phase 6. They say how one note
# stands to another as a WRITING - what it was built on, what it replaced.
STRUCTURAL = ("builds_on", "supersedes")

# Phase 14's seven, in the order the ontology declares them. These say how
# one piece of thinking stands to another, which is the whole of part 3.
SEMANTIC = (
    "derived_from",
    "contradicts",
    "diverges_from",
    "applies",
    "informed_by",
    "expresses",
    "answered_by",
)

# The frontmatter relations, in the order the schema of record names them.
NAMED = STRUCTURAL + SEMANTIC

# A resolved edge's predicate. `supersedes` reuses the Dublin Core term;
# the rest stay ours, and the seven are subproperties of PROV or nothing at
# all. An unresolved edge keeps our `_raw` predicate regardless - a broken
# link has no standard, it is just text we could not place.
RESOLVED = {
    "builds_on": V.builds_on,
    "supersedes": DCTERMS.replaces,
    "links_to": V.links_to,
    **{kind: V[kind] for kind in SEMANTIC},
}


def edge_triples(relative, text, resolve, headings):
    """Yield (subject, predicate, object) for one note's relations.

    `resolve(target) -> path | None` is passed in, so this module never
    learns how resolution works — a dict's `.get` is a valid resolver.
    `headings(path) -> that document's items` is injected the same way. It
    is the only place the builder asks about a file it is not walking, and
    it is needed because an anchor is checked against its TARGET.

    A target that does not land keeps its text on a `_raw` predicate:

        doc:a  v:builds_on      doc:CIDR        resolved, a resource
        doc:a  v:builds_on_raw  "없는 문서"       not resolved, a literal

    RDF has no NULL, so the SQLite `dst IS NULL` row becomes a different
    predicate rather than an empty object. Minting an IRI for the missing
    document would work too — an IRI need not resolve — but then
    `rdfs:range` would let a reasoner declare 357 phantoms to be Documents,
    and two broken links sharing a name would collapse into one resource.

    `v:supersedes_raw` is the NORMAL case, not a fault: that relation
    points at a document the merge deleted.
    """
    subject = doc_iri(relative)
    fm, body = split_frontmatter(text)

    for kind in NAMED:
        for item in fm_list(fm, kind):
            yield from _edge(subject, kind, *link_parts(item), resolve, headings)

    # A link written under an item belongs to the ITEM. The gold set
    # measured why: 500's documents carry no relation of their own because
    # each insight links for itself, and hanging all of them off the file
    # is what made that band unlabelable.
    for item, target, heading in iter_links_by_item(body):
        source = section_iri(relative, item) if item else subject
        yield from _edge(source, "links_to", target, heading, resolve, headings)

    # Derived from the path, and the target is the FOLDER — not the note
    # that happens to represent it. That note is a sibling, not a container.
    directory = relative.rsplit("/", 1)[0] if "/" in relative else ""
    if directory:
        yield subject, DCTERMS.isPartOf, folder_iri(directory)


def sentinel(target):
    """The resource a non-document source names, or None.

    None means "this is a note name, go and resolve it". Returning a
    resource here is what keeps `_raw` meaning BROKEN rather than
    "anything the resolver could not place".

    Public because `tools/measure_phase15` has to ask the same question in
    the same order. It used to answer it on its own and went stale the day
    the sentinel stopped being a broken link.
    """
    if target == EXPERIENCE:
        return V.experience
    if target.startswith(EXTERNAL_PREFIX):
        outside = target[len(EXTERNAL_PREFIX) :].strip()
        return EXTERNAL[outside.translate(ESCAPES)] if outside else None
    return None


def _edge(subject, kind, target, heading, resolve, headings):
    """One relation, as a resource when it lands and as text when it does not.

    A heading sends the edge one level down, onto the item it names - but
    only when the TARGET document actually holds that item. When it does
    not, the two kinds part company:

        links_to      falls back to the document
        the seven     stay raw

    That asymmetry is semantic-identity.md's, stated in as many words: a
    broken body link is tolerated, a broken semantic fact is not. 58 of the
    vault's 59 `#` links point at an ordinary heading and mean "go read
    this part" - the document is where they land. A `derived_from` naming
    an item that is not there is a claim about nothing, and filing it
    against the whole document would hide that.
    """
    # A source that is not a document, before anything is looked up.
    outside = sentinel(target)
    if outside is not None:
        yield subject, RESOLVED[kind], outside
        return

    landed = resolve(target)
    # Kept whole so lint can report what was MEANT, not just which file
    # went missing.
    written = f"{target}#{heading}" if heading else target

    if landed is None:
        yield subject, V[kind + "_raw"], Literal(written)
        return
    # An attachment is neither a relation nor a broken link — Phase 4 cost
    # us 582 false reports before that was clear.
    if not landed.endswith(".md"):
        return

    if heading:
        matched = resolve_anchor(headings(landed) or (), heading)
        if matched:
            yield subject, RESOLVED[kind], section_iri(landed, matched)
            return
        if kind in SEMANTIC:
            yield subject, V[kind + "_raw"], Literal(written)
            return

    yield subject, RESOLVED[kind], doc_iri(landed)


def folder_triples(path, hub=None):
    """Yield what is true of a folder itself.

    A folder is not a file, so SQLite would have needed a fake row and used
    the folder note as a stand-in — which is why `part_of` used to point at
    a sibling and the chain died at depth 2 while paths go 6 deep. An IRI
    costs nothing here, so the compromise is not needed.
    """
    subject = folder_iri(path)
    if "/" in path:
        yield subject, DCTERMS.isPartOf, folder_iri(path.rsplit("/", 1)[0])
    if hub:
        # `type: hub` says what a document IS; this says which folder it is
        # FOR. Measured: 76 hubs are no folder's note, and 27 folder notes
        # are not typed hub. Neither stands in for the other.
        yield subject, V.hub, doc_iri(hub)


def tag_triples(tag):
    """Yield a tag's whole ancestry, one level per triple.

    Every level, not just the parent. Unlike a folder, an intermediate tag
    may exist nowhere: measured, 12 of the vault's 20 parent tags sit on no
    document at all. `Stack` is one of them, and `by_tag("Stack")` still
    answers for 945 document - that hierarchy lived only inside a query.

    `skos:broader`, not a predicate of our own. Looking for the standard
    vocabulary first is the rule, and this is precisely what it says.
    """
    while "/" in tag:
        parent = tag.rsplit("/", 1)[0]
        yield tag_iri(tag), SKOS.broader, tag_iri(parent)
        tag = parent


def _resolver(index, targets, is_node, source):
    """Build the `resolve` that `edge_triples` asks for.

    A note in an excluded zone reads as unresolved. The file is there, but
    the graph does not hold it, so a link into it is the same `_raw` case
    as a link to nothing — which is what the SQLite model wrote as a NULL
    `dst` beside a kept `raw`.
    """

    def resolve(target):
        landed = resolve_link(target, index, targets, source=source)
        if landed is None or (landed.endswith(".md") and landed not in is_node):
            return None
        return landed

    return resolve


def build_graph(root):
    """Assemble the whole vault as one graph.

    Derived and rebuilt, exactly like the SQLite one. Nothing incremental.

    Folders and tags are collected while walking the notes and emitted
    afterwards, because a folder or a tag is stated once no matter how many
    notes point at it.
    """
    graph = Graph()
    for prefix, namespace in (
        ("v", V),
        ("doc", DOC),
        ("folder", FOLDER),
        ("tag", TAG),
        ("skos", SKOS),
        ("dcterms", DCTERMS),
    ):
        graph.bind(prefix, namespace)

    notes, index, targets = scan_vault(root)
    inside = [note for note in notes if in_graph(note)]
    is_node = set(inside)
    folders, tags = set(), set()

    # Read once, then index the items. An anchor is checked against the
    # document it POINTS AT, so every document's headings have to be known
    # before the first edge is written.
    texts = {r: (root / r).read_text(encoding="utf-8") for r in inside}
    headings = {r: item_headings(split_frontmatter(t)[1]) for r, t in texts.items()}.get

    for relative in inside:
        text = texts[relative]
        for triple in node_triples(relative, text):
            graph.add(triple)
        for triple in edge_triples(
            relative, text, _resolver(index, targets, is_node, relative), headings
        ):
            graph.add(triple)

        directory = relative.rsplit("/", 1)[0] if "/" in relative else ""
        while directory:
            folders.add(directory)
            directory = directory.rsplit("/", 1)[0] if "/" in directory else ""

        fm, _ = split_frontmatter(text)
        tags.update(fm_list(fm, "tags"))

    for directory in sorted(folders):
        for triple in folder_triples(directory, folder_note(directory, is_node)):
            graph.add(triple)
    for tag in sorted(tags):
        for triple in tag_triples(tag):
            graph.add(triple)
    return graph
