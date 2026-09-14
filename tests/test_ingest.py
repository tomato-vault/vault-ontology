from pathlib import Path
import pytest

from vault.ingest import fm_blocks, ingest_draft
from vault.__main__ import main


def make(tmp_path, files):
    for relative, text in files.items():
        p = tmp_path / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def test_fm_blocks_preserves_multiline_lists():
    fm = "type: concept\ntags:\n  - Stack/Python\n  - Stack/AI\nsummary: ok"
    blocks = fm_blocks(fm)
    assert len(blocks) == 3
    assert blocks[0] == ("type", "type: concept")
    assert blocks[1] == ("tags", "tags:\n  - Stack/Python\n  - Stack/AI")
    assert blocks[2] == ("summary", "summary: ok")


def test_ingest_draft_respects_existing_frontmatter(tmp_path):
    vault = tmp_path / "vault"
    draft = tmp_path / "draft.md"
    draft.write_text(
        "---\n"
        "type: concept\n"
        "tags:\n"
        "  - Stack/Python\n"
        "summary: Existing summary\n"
        "---\n\n"
        "# Content\n",
        encoding="utf-8"
    )
    make(vault, {"200 Dev/Base.md": "---\ntype: concept\nsummary: ok\ncreated: 2026-08-01\n---\nbody\n"})

    relative, problems = ingest_draft(
        vault_path=vault,
        draft_path=draft,
        dir_="200 Dev",
        mkdir=True,
    )
    assert problems == []
    assert relative == "200 Dev/draft.md"
    written = (vault / relative).read_text(encoding="utf-8")
    assert "type: concept" in written
    assert "tags:\n  - Stack/Python" in written
    assert "summary: Existing summary" in written
    assert "# Content" in written


def test_ingest_draft_overrides_when_specified(tmp_path):
    vault = tmp_path / "vault"
    draft = tmp_path / "draft.md"
    draft.write_text("---\ntype: concept\n---\n# Content\n", encoding="utf-8")
    make(vault, {"200 Dev/Base.md": "---\ntype: concept\nsummary: ok\ncreated: 2026-08-01\n---\nbody\n"})

    relative, problems = ingest_draft(
        vault_path=vault,
        draft_path=draft,
        dir_="200 Dev",
        summary="Overridden summary",
        mkdir=True,
    )
    assert problems == []
    written = (vault / relative).read_text(encoding="utf-8")
    assert "summary: Overridden summary" in written


def test_ingest_draft_rm_deletes_source(tmp_path):
    vault = tmp_path / "vault"
    draft = tmp_path / "draft.md"
    draft.write_text("---\ntype: concept\nsummary: ok\n---\n# Content\n", encoding="utf-8")
    make(vault, {"200 Dev/Base.md": "---\ntype: concept\nsummary: ok\ncreated: 2026-08-01\n---\nbody\n"})

    relative, problems = ingest_draft(
        vault_path=vault,
        draft_path=draft,
        dir_="200 Dev",
        mkdir=True,
        rm=True,
    )
    assert problems == []
    assert not draft.exists()
    assert (vault / relative).exists()


def test_cli_ingest(tmp_path, capsys):
    vault = tmp_path / "vault"
    draft = tmp_path / "draft.md"
    draft.write_text("---\ntype: concept\nsummary: ok\n---\n# Content\n", encoding="utf-8")
    make(vault, {"200 Dev/Base.md": "---\ntype: concept\nsummary: ok\ncreated: 2026-08-01\n---\nbody\n"})

    rc = main(["ingest", str(draft), "--dir", "200 Dev", "--vault", str(vault)])
    assert rc == 0
    assert (vault / "200 Dev/draft.md").exists()
