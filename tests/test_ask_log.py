"""`vault ask` leaves a line in $VAULT_ASK_LOG — and only then."""
import json

from vault.__main__ import main

NOTE = "---\ntype: principle\nsummary: ok\ncreated: 2026-09-01\nderived_from:\n  - \"[[사건]]\"\n---\n본문\n"
CASE = "---\ntype: case\nsummary: ok\ncreated: 2026-08-01\n---\n사건의 전말\n"


def vault(tmp_path):
    (tmp_path / "200 Dev").mkdir()
    (tmp_path / "200 Dev/원칙.md").write_text(NOTE, encoding="utf-8")
    (tmp_path / "200 Dev/사건.md").write_text(CASE, encoding="utf-8")
    return tmp_path


def test_without_the_variable_nothing_is_written(tmp_path, monkeypatch):
    v = vault(tmp_path)
    monkeypatch.delenv("VAULT_ASK_LOG", raising=False)
    assert main(["ask", "evidence", "원칙", "--vault", str(v)]) == 0
    assert not list(tmp_path.glob("*.jsonl"))


def test_with_the_variable_each_question_appends_a_line(tmp_path, monkeypatch):
    v = vault(tmp_path)
    log = tmp_path / "ask.jsonl"
    monkeypatch.setenv("VAULT_ASK_LOG", str(log))
    assert main(["ask", "evidence", "원칙", "--vault", str(v)]) == 0
    assert main(["ask", "review", "--vault", str(v)]) in (0, 1)
    assert main(["ask", "lineage", "없는 문서", "--vault", str(v)]) == 2
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert [r["question"] for r in rows] == ["evidence", "review", "lineage"]
    assert rows[0]["note"] == "원칙" and rows[0]["status"] == "answered" and rows[0]["paths"] == 1
    assert rows[1]["note"] is None
    assert rows[2]["status"] == "no_such_document" and rows[2]["paths"] == 0
    assert all("at" in r and "ms" in r for r in rows)
