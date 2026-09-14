from vault.graph import build, by_tag, by_type, stats, learning_path, near, orphans

NOTE = "---\ntype: concept\nsummary: ok\ncreated: 2026-08-10\n---\n{body}\n"


def make(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def rows(connection, sql):
    return connection.execute(sql).fetchall()


def test_a_note_becomes_a_node(tmp_path):
    make(tmp_path, {"200 Dev/CIDR.md": NOTE.format(body="본문")})
    db = build(tmp_path)
    assert rows(db, "SELECT path, name, zone, type FROM node") == [
        ("200 Dev/CIDR.md", "CIDR", "200 Dev", "concept")
    ]


def test_an_excluded_zone_is_not_a_node(tmp_path):
    make(
        tmp_path,
        {
            "CIDR.md": NOTE.format(body="본문"),
            "900 Archive/현자의 돌.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT path FROM node") == [("CIDR.md",)]


def test_a_template_is_not_a_node(tmp_path):
    # A template's frontmatter is a placeholder, not data. It became
    # visible when the vault dropped `type: template`: each template then
    # carried the type of the document it produces, and `type: decision`
    # started answering with the Decision Node Template.
    make(
        tmp_path,
        {
            "CIDR.md": NOTE.format(body="본문"),
            "000 Index/Templates/Decision Node Template.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT path FROM node") == [("CIDR.md",)]


def test_a_zone_is_counted_by_directory_not_by_prefix(tmp_path):
    # `000 Index/Templates` must not swallow a sibling that merely starts
    # with the same letters. Seventh time this boundary has come up.
    make(
        tmp_path,
        {
            "000 Index/Templates 사용법.md": NOTE.format(body="본문"),
            "000 Index/Templates/Daily Template.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT path FROM node") == [
        ("000 Index/Templates 사용법.md",)
    ]


def test_claude_md_is_not_a_node(tmp_path):
    make(tmp_path, {"CIDR.md": NOTE.format(body="본문"), "CLAUDE.md": "지시문"})
    assert rows(build(tmp_path), "SELECT path FROM node") == [("CIDR.md",)]


def test_a_builds_on_becomes_an_edge(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="본문").replace(
                "---\n본문", 'builds_on:\n  - "[[CIDR]]"\n---\n본문'
            ),
            "CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT src, dst, kind FROM edge") == [
        ("a.md", "CIDR.md", "builds_on")
    ]


def test_a_body_link_becomes_a_links_to_edge(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="[[CIDR]] 참조"),
            "CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT src, dst, kind FROM edge") == [
        ("a.md", "CIDR.md", "links_to")
    ]


def test_a_frontmatter_link_is_not_counted_as_a_body_link(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="본문").replace(
                "---\n본문", 'builds_on:\n  - "[[CIDR]]"\n---\n본문'
            ),
            "CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(1,)]


def test_an_unresolved_link_keeps_its_raw_and_a_null_dst(tmp_path):
    make(tmp_path, {"a.md": NOTE.format(body="[[없는 문서]] 참조")})
    assert rows(build(tmp_path), "SELECT dst, raw FROM edge") == [(None, "없는 문서")]


def test_a_link_into_an_excluded_zone_gets_a_null_dst(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="[[현자의 돌]] 참조"),
            "900 Archive/현자의 돌.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT dst, raw FROM edge") == [(None, "현자의 돌")]


def test_an_embed_of_an_attachment_is_not_an_edge(tmp_path):
    make(tmp_path, {"a.md": NOTE.format(body="![[가상화.png]] 그림")})
    (tmp_path / "가상화.png").write_bytes(b"png")
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def test_a_tag_becomes_a_row(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="본문").replace(
                "type: concept", "type: concept\ntags:\n  - Stack/Python"
            )
        },
    )
    assert rows(build(tmp_path), "SELECT path, tag FROM tag") == [
        ("a.md", "Stack/Python")
    ]


def test_building_twice_does_not_double_the_rows(tmp_path):
    make(tmp_path, {"CIDR.md": NOTE.format(body="본문")})
    database = tmp_path / "graph.db"
    build(tmp_path, database)
    assert rows(build(tmp_path, database), "SELECT count(*) FROM node") == [(1,)]


def test_a_note_is_part_of_the_folder_note_inside_its_folder(tmp_path):
    make(
        tmp_path,
        {
            "200 Dev/Network/Network.md": NOTE.format(body="본문"),
            "200 Dev/Network/CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT src, dst, raw FROM edge") == [
        ("200 Dev/Network/CIDR.md", "200 Dev/Network/Network.md", "Network")
    ]


def test_a_note_is_part_of_the_folder_note_beside_its_folder(tmp_path):
    make(
        tmp_path,
        {
            "200 Dev/Network.md": NOTE.format(body="본문"),
            "200 Dev/Network/CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT src, dst FROM edge") == [
        ("200 Dev/Network/CIDR.md", "200 Dev/Network.md")
    ]


def test_a_folder_note_is_not_part_of_itself(tmp_path):
    make(tmp_path, {"200 Dev/Network/Network.md": NOTE.format(body="본문")})
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def test_a_folder_without_a_folder_note_makes_no_edge(tmp_path):
    make(tmp_path, {"200 Dev/Network/CIDR.md": NOTE.format(body="본문")})
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def test_a_note_at_the_vault_root_makes_no_edge(tmp_path):
    make(tmp_path, {"CIDR.md": NOTE.format(body="본문")})
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def test_a_note_named_after_the_folder_elsewhere_is_not_the_folder_note(tmp_path):
    make(
        tmp_path,
        {
            "500 Mind/Network.md": NOTE.format(body="본문"),
            "200 Dev/Network/CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def test_part_of_in_the_frontmatter_is_ignored(tmp_path):
    make(
        tmp_path,
        {
            "a.md": NOTE.format(body="본문").replace(
                "---\n본문", 'part_of:\n  - "[[CIDR]]"\n---\n본문'
            ),
            "CIDR.md": NOTE.format(body="본문"),
        },
    )
    assert rows(build(tmp_path), "SELECT count(*) FROM edge") == [(0,)]


def small(tmp_path):
    """A vault with two typed notes, a tag tree and one broken link."""
    make(
        tmp_path,
        {
            "200 Dev/CIDR.md": NOTE.format(body="[[Subnet mask]] 참조").replace(
                "type: concept", "type: concept\ntags:\n  - Stack/Python"
            ),
            "200 Dev/Subnet mask.md": NOTE.format(body="[[없는 문서]]").replace(
                "type: concept", "type: procedure\ntags:\n  - Stack\n  - Stacked"
            ),
        },
    )
    return build(tmp_path)


def test_stats_counts_each_table(tmp_path):
    counts = stats(small(tmp_path))
    assert (counts["node"], counts["edge"], counts["tag"]) == (2, 2, 3)


def test_stats_counts_unresolved_edges(tmp_path):
    assert stats(small(tmp_path))["unresolved"] == 1


def test_stats_counts_each_edge_kind(tmp_path):
    assert stats(small(tmp_path))["kinds"] == {"links_to": 2}


def test_by_type_returns_only_that_type(tmp_path):
    assert by_type(small(tmp_path), "concept") == ["200 Dev/CIDR.md"]


def test_a_type_nothing_carries_returns_nothing(tmp_path):
    assert by_type(small(tmp_path), "tradeoff") == []


def test_by_tag_returns_the_notes_carrying_it(tmp_path):
    assert by_tag(small(tmp_path), "Stack/Python") == ["200 Dev/CIDR.md"]


def test_a_parent_tag_matches_its_children(tmp_path):
    assert by_tag(small(tmp_path), "Stack") == [
        "200 Dev/CIDR.md",
        "200 Dev/Subnet mask.md",
    ]


def test_a_tag_prefix_stops_at_a_slash(tmp_path):
    assert by_tag(small(tmp_path), "Stacked") == ["200 Dev/Subnet mask.md"]


def test_results_come_back_sorted(tmp_path):
    assert by_tag(small(tmp_path), "Stack") == sorted(by_tag(small(tmp_path), "Stack"))


def graph_of(tmp_path, links):
    """Build a vault where each key `builds_on` the names listed under it."""
    files = {}
    for name, prerequisites in links.items():
        block = "".join(f'  - "[[{p}]]"\n' for p in prerequisites)
        files[f"{name}.md"] = (
            "---\ntype: concept\nsummary: ok\n"
            + (f"builds_on:\n{block}" if block else "")
            + "created: 2026-08-10\n---\n본문\n"
        )
    return build((make(tmp_path, files)))


def test_a_direct_prerequisite_comes_back_at_depth_one(tmp_path):
    db = graph_of(tmp_path, {"A": ["B"], "B": []})
    assert learning_path(db, "A.md") == [("B.md", 1)]


def test_a_chain_comes_back_deepest_last(tmp_path):
    db = graph_of(tmp_path, {"A": ["B"], "B": ["C"], "C": ["D"], "D": []})
    assert learning_path(db, "A.md") == [("B.md", 1), ("C.md", 2), ("D.md", 3)]


def test_a_note_with_no_prerequisite_returns_nothing(tmp_path):
    db = graph_of(tmp_path, {"A": []})
    assert learning_path(db, "A.md") == []


def test_the_start_is_not_its_own_prerequisite(tmp_path):
    db = graph_of(tmp_path, {"A": ["B"], "B": ["A"]})
    assert learning_path(db, "A.md") == [("B.md", 1)]


def test_a_diamond_reports_each_note_once_at_its_shortest_depth(tmp_path):
    db = graph_of(tmp_path, {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []})
    assert learning_path(db, "A.md") == [("B.md", 1), ("C.md", 1), ("D.md", 2)]


def test_a_long_chain_stops_at_the_limit(tmp_path):
    db = graph_of(tmp_path, {chr(65 + n): [chr(66 + n)] for n in range(6)} | {"G": []})
    assert learning_path(db, "A.md", limit=3) == [("B.md", 1), ("C.md", 2), ("D.md", 3)]


def test_an_unresolved_prerequisite_is_not_a_step(tmp_path):
    db = graph_of(tmp_path, {"A": ["없는 문서"]})
    assert learning_path(db, "A.md") == []


def test_only_builds_on_is_followed(tmp_path):
    make(
        tmp_path,
        {
            "A.md": NOTE.format(body="[[B]] 참조"),
            "B.md": NOTE.format(body="본문"),
        },
    )
    assert learning_path(build(tmp_path), "A.md") == []


def note(body="본문", tags=()):
    """A minimal valid note, optionally tagged."""
    block = "".join(f"  - {tag}\n" for tag in tags)
    return (
        "---\ntype: concept\n"
        + (f"tags:\n{block}" if block else "")
        + f"summary: ok\ncreated: 2026-08-10\n---\n{body}\n"
    )


def test_a_note_lists_what_it_points_at(tmp_path):
    db = build(make(tmp_path, {"A.md": note("[[B]]"), "B.md": note()}))
    assert near(db, "A.md")["links_to"] == ["B.md"]


def test_a_note_lists_what_points_at_it(tmp_path):
    db = build(make(tmp_path, {"A.md": note("[[B]]"), "B.md": note()}))
    assert near(db, "B.md")["linked_by"] == ["A.md"]


def test_a_shared_tag_makes_a_neighbour(tmp_path):
    db = build(
        make(
            tmp_path,
            {
                "A.md": note(tags=["Stack/Python"]),
                "B.md": note(tags=["Stack/Python"]),
            },
        )
    )
    assert near(db, "A.md")["shares_tag"] == [("B.md", 1)]


def test_more_shared_tags_rank_higher(tmp_path):
    db = build(
        make(
            tmp_path,
            {
                "A.md": note(tags=["Stack/Python", "Topic/Career"]),
                "B.md": note(tags=["Stack/Python"]),
                "C.md": note(tags=["Stack/Python", "Topic/Career"]),
            },
        )
    )
    assert near(db, "A.md")["shares_tag"] == [("C.md", 2), ("B.md", 1)]


def test_a_tag_neighbour_already_linked_is_not_repeated(tmp_path):
    db = build(
        make(
            tmp_path,
            {
                "A.md": note("[[B]]", tags=["Stack/Python"]),
                "B.md": note(tags=["Stack/Python"]),
            },
        )
    )
    assert near(db, "A.md")["shares_tag"] == []


def test_a_note_does_not_neighbour_itself(tmp_path):
    db = build(make(tmp_path, {"A.md": note(tags=["Stack/Python"])}))
    assert near(db, "A.md") == {"links_to": [], "linked_by": [], "shares_tag": []}


def test_a_note_nobody_points_at_is_an_orphan(tmp_path):
    db = build(make(tmp_path, {"A.md": note("[[B]]"), "B.md": note()}))
    assert orphans(db) == ["A.md"]


def test_a_folder_note_is_not_an_orphan(tmp_path):
    db = build(
        make(
            tmp_path,
            {
                "200 Dev/Network/Network.md": note(),
                "200 Dev/Network/CIDR.md": note(),
            },
        )
    )
    assert orphans(db) == ["200 Dev/Network/CIDR.md"]


def test_an_unresolved_link_rescues_nobody(tmp_path):
    db = build(make(tmp_path, {"A.md": note("[[없는 문서]]"), "B.md": note()}))
    assert orphans(db) == ["A.md", "B.md"]


def test_orphans_can_be_limited_to_a_zone(tmp_path):
    db = build(
        make(
            tmp_path,
            {
                "200 Dev/A.md": note(),
                "500 Mind/B.md": note(),
            },
        )
    )
    assert orphans(db, "500 Mind") == ["500 Mind/B.md"]


def test_cli_q_sql(tmp_path, capsys):
    from vault.__main__ import main
    db_file = tmp_path / ".vault-graph.db"
    make(tmp_path, {"200 Dev/CIDR.md": NOTE.format(body="본문")})
    build(tmp_path, db_file)

    rc = main(["q", "sql", "SELECT name, zone FROM node", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CIDR · 200 Dev" in out

