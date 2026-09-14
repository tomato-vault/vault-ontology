# CLI 로드맵 — 생성 계열 유틸리티를 새 저장소로

> 목표: 옛 `reference/vault.py`(단일 파일)의 유틸리티를 전부 새 저장소
> (`vault-ontology`, 모듈형)로 옮겨 스킬이 한 실행 경로만 참조하도록 한다.

## 배경

- 스킬(vault-new 등)이 부르던 `~/Desktop/Code/vault-cli/vault.py`는 **경로가
  더 이상 유효하지 않다.** 그 파일은 현재 이 저장소의 `reference/vault.py`에 고정해 두었다.
- 이 저장소는 Phase 1~9에서 읽기·그래프·온톨로지 기능을 재구현했다. **생성 계열
  (new·ingest·template·doctor·q sql)은 아직 안 옮겼다.**
- Phase 9 결론에 따라 상시 운용에는 이 저장소의 SQLite 구현을 사용한다. 생성 계열 명령도 이 저장소로 옮긴다.

## 호출 규약

`vault` 는 **전역 명령**이다. 어느 디렉터리에서든 부른다.

```bash
vault <command> [args]        # --vault 생략 시 iCloud vault 기본값
```

editable 설치라 이 저장소의 코드를 고치면 **재설치 없이 바로 반영**된다. 다시
깔거나 다른 Mac에 놓을 때는 저장소에서 한 번:

```bash
uv tool install --editable .
```

`~/.local/bin/vault` 에 실행 파일이 생긴다. 그 경로가 `PATH` 에 있어야 한다.

## 명령 이관 순서

각 단계는 앞 단계의 코드를 재사용한다. TDD(RED→GREEN→REFACTOR→실측)로 간다.

| 단계 | 명령 | 하는 일 | 재사용/근거 | 상태 |
|---|---|---|---|---|
| 1 | `new` | 표준 입력이나 인자로 받은 문서를 **스키마 검사 후** 생성. 통과하지 못하면 파일을 만들지 않음 | `schema.validate` + `scan.resolve_link` 재사용 → `vault/create.py` | ✅ 완료 |
| 2 | `template` | 스키마 뼈대 출력 / `--list`로 `type:template` 나열 | `new`의 스키마 로직 공유 → `vault/template.py` | ✅ 완료 |
| 3 | `ingest` | 기존 초안 `.md`를 편입. frontmatter 존중, 빈 것만 채움. `--rm` | `new`의 변형 → `vault/ingest.py` | ✅ 완료 |
| 4 | `doctor` | 유실·손상 검사(iCloud의 로컬 파일 제거·Git 누락·내용 급감). `--restore` | 독립적인 Git 기반 기능 → `vault/doctor.py` | ✅ 완료 |
| 5 | `q sql` | 그래프 DB에 직접 SQL 실행 | `q` 하위 명령에 추가 | ✅ 완료 |

### 관계 필드 — 생성 시 강제

`new`/`ingest`는 스키마 관계를 그대로 검사한다. 이번 스킬 개정의 두 규약을
CLI가 뒷받침한다.

- `--supersedes "[[삭제될 원본]]"` — daily-distill이 Progress Note를 지우며
  승격할 때. 대상이 사라지므로 그래프에선 `supersedes_raw`(정상).
- `--builds-on "[[원본 Learnings]]"` — monthly-elevate가 승격 문서를 만들 때.
  대상이 남으므로 해석할 수 있다. 그래프 역질의(`q near`)로 원본을 추적할 수 있다.

## 완료 기준

- [x] 다섯 명령이 이 저장소에 있고 테스트가 있다
- [x] 스킬이 옛 경로(`~/Desktop/Code/vault-cli/vault.py`)를 한 곳도 안 부른다
- [x] `reference/vault.py`는 참고용으로만 남고 실행 경로에서 빠진다

