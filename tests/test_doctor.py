import subprocess
from pathlib import Path
import pytest

from vault.doctor import Git, check_icloud, check_missing, check_shrunk, run_doctor
from vault.__main__ import main


def init_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)


def test_check_missing_detects_deleted_files(tmp_path):
    init_git_repo(tmp_path)
    f = tmp_path / "note.md"
    f.write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    f.unlink()
    g = Git(tmp_path)
    missing = check_missing(g)
    assert missing == ["note.md"]


def test_check_icloud_detects_icloud_placeholders(tmp_path):
    sub = tmp_path / "200 Dev"
    sub.mkdir(parents=True)
    (sub / ".note.md.icloud").write_text("", encoding="utf-8")

    evicted = check_icloud(tmp_path)
    assert evicted == ["200 Dev/note.md"]


def test_check_shrunk_detects_drastic_content_reduction(tmp_path):
    init_git_repo(tmp_path)
    f = tmp_path / "big.md"
    f.write_text("\n".join(f"line {i}" for i in range(30)), encoding="utf-8")
    subprocess.run(["git", "add", "big.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    # Shrunk from 30 lines to 5 lines
    f.write_text("\n".join(f"line {i}" for i in range(5)), encoding="utf-8")
    g = Git(tmp_path)
    shrunk = check_shrunk(g, tmp_path)
    assert len(shrunk) == 1
    p, old_len, new_len = shrunk[0]
    assert p == "big.md"
    assert old_len == 30
    assert new_len == 5


def test_doctor_restore_checks_out_missing(tmp_path):
    init_git_repo(tmp_path)
    f = tmp_path / "note.md"
    f.write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    f.unlink()
    res = run_doctor(tmp_path, restore=True)
    assert f.exists()
    assert res["restored"] == ["note.md"]


def test_cli_doctor(tmp_path, capsys):
    init_git_repo(tmp_path)
    rc = main(["doctor", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no issues found" in out.lower() or "남은 문제 없음" in out
