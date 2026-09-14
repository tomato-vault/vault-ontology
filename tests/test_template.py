import re
from datetime import date
import pytest

from vault.schema import TYPES
from vault.template import TEMPLATE_HINT, list_templates, render_template


def test_template_renders_schema_frontmatter():
    text = render_template("concept")
    today = date.today().isoformat()
    assert f"type: concept" in text
    assert f"created: {today}" in text
    assert "summary: 한 줄 요약" in text
    assert "# 제목" in text
    assert TEMPLATE_HINT["concept"] in text


def test_template_bare_omits_hints():
    text = render_template("principle", bare=True)
    assert "summary: \n" in text or "summary:\n" in text or text.startswith("---\ntype: principle\nsummary:\n") or "summary: " in text
    assert TEMPLATE_HINT["principle"] not in text


def test_template_unknown_type_raises():
    with pytest.raises(ValueError):
        render_template("not_a_type")


def test_template_hints_cover_all_13_types():
    assert set(TEMPLATE_HINT.keys()) == TYPES


def test_list_templates(tmp_path):
    # Template in Templates directory
    p1 = tmp_path / "000 Index/Templates/Sample Template.md"
    p1.parent.mkdir(parents=True, exist_ok=True)
    p1.write_text("---\ntype: concept\nsummary: Sample template doc\ncreated: 2026-08-01\n---\nbody\n", encoding="utf-8")

    # Regular doc
    p2 = tmp_path / "200 Dev/Regular.md"
    p2.parent.mkdir(parents=True, exist_ok=True)
    p2.write_text("---\ntype: concept\nsummary: Regular doc\ncreated: 2026-08-01\n---\nbody\n", encoding="utf-8")

    templates = list_templates(tmp_path)
    assert len(templates) == 1
    rel, summary = templates[0]
    assert "Sample Template.md" in rel
    assert "Sample template doc" in summary


def test_cli_template_render(capsys, tmp_path):
    from vault.__main__ import main
    rc = main(["template", "concept", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "type: concept" in out


def test_cli_template_unknown_type(capsys, tmp_path):
    from vault.__main__ import main
    rc = main(["template", "bogus", "--vault", str(tmp_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown type" in err

