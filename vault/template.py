"""Render blank form skeletons and list vault templates."""

import os
import re
from datetime import date
from pathlib import Path

from vault.frontmatter import fm_get, split_frontmatter
from vault.scan import scan_vault
from vault.schema import TYPES

TEMPLATE_PATH = re.compile(r"(^|/)(Templates|_Template)/|(^|/)_template\.md$")

TEMPLATE_HINT = {
    "concept": "무엇인가 / 왜 그런가를 적는다. 읽으면 이해가 남는다.",
    "procedure": "따라 하면 결과가 나오게 적는다. 순서와 확인 지점을 넣는다.",
    "principle": "지켜야 할 규칙과 그 이유. 어길 때 무슨 일이 나는지까지.",
    "decision": "무엇을 골랐고 왜인가. Trade-offs 문서와 쌍으로 만든다.",
    "tradeoff": "선택지를 축으로 비교한다. Decision Node와 쌍으로 만든다.",
    "case": "시간 서사로 적는다. 무엇을 시도했고 무엇이 틀렸는지.",
    "capture": "남의 콘텐츠에서 온 것. 출처를 먼저 밝힌다.",
    "review": "외부 작품에 대한 내 감상. 작품 정보와 주관적 평가를 적는다.",
    "reflection": "자기 성찰. 결론보다 과정을 남긴다.",
    "project-doc": "프로젝트 진행 문서.",
    "reference": "찾아보는 용도. 설명하지 말고 나열한다.",
    "log": "그 시점의 기록. 나중에 고치지 않는다.",
    "hub": "다른 문서를 모으는 인덱스. 링크마다 한 줄 설명을 붙인다.",
}


def render_template(type_: str, bare: bool = False) -> str:
    """Return skeleton text for `type_`."""
    if type_ not in TYPES:
        raise ValueError(f"type must be one of schema TYPES: {type_}")

    today = date.today().isoformat()
    summary = "" if bare else "한 줄 요약 — 80자 이내, 제목을 되풀이하지 않는다"
    hint = "" if bare else TEMPLATE_HINT.get(type_, "")

    lines = [
        "---",
        f"type: {type_}",
        f"summary: {summary}".rstrip(),
        f"created: {today}",
        "---",
        "",
        "# 제목",
        "",
    ]
    if hint:
        lines.append(hint)
        lines.append("")
    return "\n".join(lines)


def list_templates(vault_path: Path):
    """Return (relative_path, summary) for all templates in vault."""
    vault = Path(vault_path)
    files, _, _ = scan_vault(vault)
    rows = []
    for rel in files:
        text = (vault / rel).read_text(encoding="utf-8", errors="replace")
        fm, _ = split_frontmatter(text)
        by_type = bool(fm and re.search(r"^type:\s*template\s*$", fm, re.M))
        by_path = bool(TEMPLATE_PATH.search(rel))
        if not (by_type or by_path):
            continue
        summary = fm_get(fm, "summary") if fm else ""
        mark = "" if by_type else "   (경로로 인식 — 태어날 문서의 frontmatter를 담는다)"
        rows.append((rel, (summary or "") + mark))
    return sorted(rows)
