from pathlib import Path

from vault.create import build_frontmatter, check_new, routing_warning
from vault.__main__ import main

BASE = "---\ntype: concept\nsummary: ok\ncreated: 2026-08-10\n---\n본문\n"


def make(tmp_path, files):
    for relative, text in files.items():
        p = tmp_path / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def test_frontmatter_is_built_in_schema_order():
    fm = build_frontmatter("concept", "한 줄 요약", ["[[Base]]"], "2026-08-25")
    assert fm == (
        "type: concept\n"
        "summary: 한 줄 요약\n"
        "builds_on:\n"
        '  - "[[Base]]"\n'
        "created: 2026-08-25"
    )


def test_a_bare_builds_on_gets_wrapped():
    assert '  - "[[Base]]"' in build_frontmatter("concept", "x", ["Base"], "2026-08-25")


def test_a_clean_document_has_no_problems(tmp_path):
    root = make(tmp_path, {"200 Dev/Base.md": BASE})
    fm = build_frontmatter("concept", "ok", ["[[Base]]"], "2026-08-25")
    assert check_new(root, "200 Dev/CIDR.md", fm, "본문") == []


def test_a_long_summary_is_rejected(tmp_path):
    root = make(tmp_path, {"200 Dev/Base.md": BASE})
    fm = build_frontmatter("concept", "가" * 81, None, "2026-08-25")
    codes = [c for c, _ in check_new(root, "200 Dev/CIDR.md", fm, "본문")]
    assert any("summary" in c for c in codes)


def test_an_unresolved_builds_on_is_rejected(tmp_path):
    root = make(tmp_path, {"200 Dev/Base.md": BASE})
    fm = build_frontmatter("concept", "ok", ["[[없는문서]]"], "2026-08-25")
    codes = [c for c, _ in check_new(root, "200 Dev/CIDR.md", fm, "본문")]
    assert any("builds_on" in c for c in codes)


def test_an_unresolved_supersedes_is_allowed(tmp_path):
    # supersedes points at a deleted doc — the normal case (Phase 6).
    root = make(tmp_path, {"200 Dev/Base.md": BASE})
    fm = build_frontmatter(
        "log", "ok", None, "2026-08-25", supersedes=["[[지워진 Plan]]"]
    )
    assert check_new(root, "200 Dev/CIDR.md", fm, "본문") == []


def test_a_bad_filename_char_is_rejected(tmp_path):
    root = make(tmp_path, {"200 Dev/Base.md": BASE})
    fm = build_frontmatter("concept", "ok", None, "2026-08-25")
    codes = [c for c, _ in check_new(root, "200 Dev/a|b.md", fm, "본문")]
    assert any("filename" in c for c in codes)


def test_a_duplicate_name_is_rejected(tmp_path):
    root = make(tmp_path, {"200 Dev/CIDR.md": BASE})
    fm = build_frontmatter("concept", "ok", None, "2026-08-25")
    codes = [c for c, _ in check_new(root, "300 Life/CIDR.md", fm, "본문")]
    assert any("duplicate" in c for c in codes)


def test_new_writes_a_passing_document(tmp_path):
    (tmp_path / "200 Dev").mkdir(parents=True)
    code = main(
        [
            "new",
            "--type",
            "concept",
            "--title",
            "CIDR",
            "--dir",
            "200 Dev",
            "--summary",
            "서브넷 계산",
            "--body",
            "# CIDR\n본문",
            "--vault",
            str(tmp_path),
        ]
    )
    assert code == 0
    written = (tmp_path / "200 Dev/CIDR.md").read_text(encoding="utf-8")
    assert "type: concept" in written
    assert "# CIDR" in written


def test_new_refuses_a_bad_document(tmp_path):
    (tmp_path / "200 Dev").mkdir(parents=True)
    code = main(
        [
            "new",
            "--type",
            "concept",
            "--title",
            "CIDR",
            "--dir",
            "200 Dev",
            "--summary",
            "가" * 81,
            "--body",
            "# CIDR",
            "--vault",
            str(tmp_path),
        ]
    )
    assert code == 1
    assert not (tmp_path / "200 Dev/CIDR.md").exists()


# ── routing warning — the folder's own documents are the table ──────────────


def typed(type_):
    return f"---\ntype: {type_}\nsummary: ok\ncreated: 2026-08-10\n---\n본문\n"


def test_a_type_new_to_its_folder_gets_a_routing_warning(tmp_path):
    root = make(tmp_path, {f"600 Content/601 Books/b{i}.md": typed("capture") for i in range(5)})
    warning = routing_warning(root, "600 Content/601 Books/새 노트.md", "decision")
    assert warning is not None
    assert "600 Content/601 Books" in warning
    assert "capture 5" in warning and "`decision`" in warning


def test_a_type_the_folder_already_holds_is_fine(tmp_path):
    root = make(tmp_path, {f"600 Content/601 Books/b{i}.md": typed("capture") for i in range(5)})
    assert routing_warning(root, "600 Content/601 Books/새 노트.md", "capture") is None


def test_one_neighbour_of_the_type_is_enough(tmp_path):
    files = {f"200 Dev/Network/c{i}.md": typed("concept") for i in range(5)}
    files["200 Dev/Network/사건.md"] = typed("case")
    root = make(tmp_path, files)
    assert routing_warning(root, "200 Dev/Network/또 사건.md", "case") is None


def test_too_few_neighbours_say_nothing(tmp_path):
    root = make(tmp_path, {f"600 Content/601 Books/b{i}.md": typed("capture") for i in range(2)})
    assert routing_warning(root, "600 Content/601 Books/새 노트.md", "decision") is None


def test_a_thin_folder_defers_to_its_parent(tmp_path):
    files = {f"300 Runtime/301 Day Notes/2026-08-{10 + i}.md": typed("log") for i in range(6)}
    files["300 Runtime/301 Day Notes/sub/하나.md"] = typed("log")
    root = make(tmp_path, files)
    warning = routing_warning(root, "300 Runtime/301 Day Notes/sub/새.md", "concept")
    assert warning is not None
    assert warning.startswith("300 Runtime/301 Day Notes 의")   # the parent spoke, not `sub`


def test_excluded_folders_do_not_count_as_neighbours(tmp_path):
    root = make(tmp_path, {f"000 Index/Templates/t{i}.md": typed("tradeoff") for i in range(5)})
    assert routing_warning(root, "000 Index/Templates/새.md", "concept") is None


def test_the_warning_never_blocks_new(tmp_path):
    root = make(tmp_path, {f"200 Dev/c{i}.md": typed("concept") for i in range(5)})
    code = main(["new", "--type", "log", "--title", "오늘", "--dir", "200 Dev",
                 "--body", "# 오늘", "--vault", str(root)])
    assert code == 0
    assert (root / "200 Dev/오늘.md").exists()
