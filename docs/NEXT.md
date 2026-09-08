# NEXT — Phase 1~9 종료 상태와 Phase 10 재개 지점

> Phase 1~9는 2026-08-25에 모두 끝났다. 그 결론은 변경하지 않는다.
> 같은 저장소에서 별도 목표의 3부를 시작하며, 다음 재개 지점은 Phase 10이다.

---

## 환경 복원 절차

```bash
git clone git@github.com:tomato-data/vault-ontology.git ~/Desktop/Code/vault-ontology
cd ~/Desktop/Code/vault-ontology
uv sync
uv run pytest -q          # 2026-09-01 기준 433개 통과해야 정상 출발점
```

### 전역 `vault` 명령

`uv run python -m vault …` 로도 전부 되지만, 매일 쓰려면 설치해 두는 편이 낫다.

```bash
uv tool install --force -e --with pyshacl .
```
`-e` (editable) 라 레포의 현재 코드를 그대로 쓴다 — 고칠 때마다 재설치하지 않는다 (2026-09-08).
`vault` 와 `vo` 두 이름이 생긴다. **손으로 칠 땐 `vo`, 문서·스크립트엔 `vault`.**


**`--with pyshacl` 이 필요하다.** `vault validate` 가 SHACL 을 쓰는데 그것만 선택
의존성이라, 빼고 설치하면 `validate` 하나가 죽는다 (2026-09-01 에 실제로 겪었다 —
그때는 최상위 import 라 `vault lint` 까지 함께 죽었고, 그래서 import 를 게으르게
바꿨다).

저장소를 고친 뒤 전역 명령이 옛 동작을 하면 uv 가 휠을 캐시한 것이다.

```bash
uv tool install --force --reinstall -e --with pyshacl .
```

### 셸 히스토리는 기본으로 안 남는다

이 기계에서 확인했다 — `SAVEHIST=0`, `~/.zshrc` 에 히스토리 설정이 없고
`~/.zsh_history` 의 마지막 기록이 **2025-06-15**였다. 무엇을 언제 실행했는지가
필요하면 먼저 켠다.

```bash
# ~/.zshrc
export HISTFILE=~/.zsh_history
export HISTSIZE=50000
export SAVEHIST=50000
setopt EXTENDED_HISTORY INC_APPEND_HISTORY
```

**2주 실사용 관측이 이걸 쓴다** — 켜 두면 「무엇을 언제 물었나」를 손으로 안 적어도
된다. 안 켜도 관측은 되고, 날짜를 손으로 적을 뿐이다.

### 답안지

`reference/`에 함께 들어 있다 (vault-cli `21faa91`, 2026-08-11 스냅샷). 별도로 받을 것이 없다.

**막히기 전에는 열지 않는다.** 자세한 사용 규칙은 [`reference/README.md`](../reference/README.md).
Phase 1~5까지만 답이 있고, **2부(RDF·추론)는 답안지가 없다.**

vault 경로는 두 Mac 모두 같다.

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault
```

---

## 현재 위치

**Phase 1~9 완료. 테스트 241개 통과. Phase 10~20 계획 수립.**

**3부의 구현이 끝났다.** 남은 것은 [`phase18.md`](phases/phase18.md) Step 5의
**2주 실사용**이고, 그것이 Phase 19·20을 할지와 **디렉토리를 개편할지**를 함께 정한다.

```bash
uv run python -m vault rdf                      # 그래프를 만든다
uv run python -m vault validate                 # 계약을 검사한다 (--audit 로 warning 까지)
uv run python -m vault ask lineage "<문서>"      # 이 판단 뒤의 근거 사슬
uv run python -m vault ask evidence "<문서>"     # 바로 앞의 근거
uv run python -m vault ask affected "<문서>"     # 이걸 고치면 뭐가 영향받나
uv run python -m vault ask together             # 같은 근거를 공유하는 것들
uv run python -m vault ask crossing             # 삶과 일 사이를 오간 사슬
uv run python -m vault ask review               # 무효화된 근거에 선 것
```

> **2주 동안 눈여겨볼 것 하나.** `ask crossing`이 지금 **0건**이다. 의미 관계를
> 가진 문서 148개 중 **개인 대역이 4개**뿐이라, C09·C15(개인 경험이 기술 판단에)가
> 답할 데이터를 못 가졌다. 라벨링이 기술 쪽에만 붙었다는 뜻이고, 그걸 메울지가
> 실사용에서 나올 판단이다.

`.vault.ttl` 은 28,436 트리플이다 — 섹션 324 · `v:Insight` 121 · `v:Question` 56 ·
의미 관계 159. 회귀 확인은 `tools/measure_phase15` (gold 33/33) ·
`measure_phase16` (SHACL) · `measure_phase17` (규칙) · `measure_phase18` (질문).

> **2026-08-31 · vault 쪽 전 디렉토리 정합화 완료** — 정본은 vault 의
> `000 Index/Dots/전 디렉토리 정합화 — 마스터 플랜.md`. Phase 15 에 주는 것 둘:
> ① type 교정 35건(`_Compile Log` 18 reflection→log · `Incident Response` 17
> project-doc→case)으로 **type 분포 숫자가 움직였다** — gold set 50개 문서의 type 은
> 안 바뀌었으므로 답안 재현에는 영향 없고, 회귀 대조에서 숫자가 다르면 정정으로 기록.
> ② 500 결정 — `By Subquestion/` 문서는 type 을 안 바꾸고 **빌더가 경로에서
> `v:Question` 을 유도한다** (「파생 가능한 사실은 frontmatter 에 안 적는다」).
> 그래프 빌더의 소소한 추가 요구다. 스키마 정본은 v1.16 (case=event 독법 · 필수 필드 프로파일).

| Phase | 내용 | 상태 |
|---|---|---|
| 1~4 | frontmatter · 위키링크 · 스캔 · lint | ✅ |
| 5 | SQLite 그래프 — **1부 종료** | ✅ |
| 6 | RDF 재모델링 | ✅ |
| 7 | SPARQL 질의 · SQLite 비교 | ✅ |
| 8 | RDFS/OWL/SKOS 어휘 설계 | ✅ |
| 9 | 추론 · 최종 판단 | ✅ |
| 10 | 문제 계약 · 역량 질문 30개 | ✅ **완료** — 30/30 판정 |
| 11 | 라벨링 파일럿 — 비용 측정 | 🟡 1차 완료 · **시간·일치율은 Phase 12 Step 4가 잰다** |
| 12 | 의미 작성 계약 · gold set | ✅ **완료** — 50개 · 관계 33건 |
| 13 | 문서와 지식 개체의 분리 | ✅ **완료** — [`semantic-identity.md`](part3/semantic-identity.md) |
| 14 | 핵심 도메인 온톨로지 0.1 | ✅ **완료** |
| 15 | 의미 사실 그래프 빌더 | ✅ **완료** — gold 답안 33/33 재현 |
| 16 | SHACL 의미 계약 | ✅ **완료** — shape 6개 · parity 22=22 |
| 17 | 목적 제한 추론 | ✅ **완료** — 규칙 4개 · 물질화 안 함 |
| 18 | 의미 질의 — **3부 종착점** | ✅ **구현 완료** — `vault ask` 6개 · gold 33/33. **2주 실사용만 남음** |
| 19~20 | 제안·승인 · 제한 운영 | **보류** — Phase 18 실사용 뒤 판단 |

`vault/`에는 파서·검증·SQLite 그래프·RDF·SPARQL·추론 구현이 모두 들어 있다.
최종 결론은 [`../learnings/verdict.md`](../learnings/verdict.md)에 있다.

### 2부에서 확인한 것

같은 질문을 재귀 CTE, SPARQL property path, 추론기로 각각 풀었다. SPARQL은
이행 폐쇄와 역방향 순회를 간결하게 표현했지만, 이 vault에서 SQLite로 답하지
못한 질의는 없었다. OWL RL 물질화는 16.6초가 걸렸고 트리플 수를 2.81배로
늘렸지만, 질적으로 새로운 유용한 사실은 만들지 못했다.

### 이 프로젝트가 무엇인가

파서 재구현 연습이 아니라 **내 vault를 강화하는 작업**이다.
`reference/`와 스키마 정본은 **권위가 아니라 검토 대상**이다.

Phase 4에서 그 간극이 **코드의 우위**로 나타났고(답안지가 못 보는 24건),
Phase 6에서는 **사람이 코드를 이겼다** — 「왜 형제 파일이 `part_of`인가」라는
질문 하나가 답안지에서 물려받아 새 모델까지 실려온 설계 오류를 잡았다.

### 최종 결정

| 판단 | 결정 |
|---|---|
| 상시 운용 | **SQLite 구현을 사용한다** |
| RDF 산출물 | 상호운용과 학습용으로 남긴다 |
| rdflib 상시 운용(v1) | 진행하지 않는다 |
| Oxigraph(v2) | 성능이 아니라 추가 학습 목적이 생길 때 재검토한다 |
| 문서 유형 계층 | Content·Imported·Structural의 3역할 계층만 채택한다 |
| vault·800 TRPG 병합 | 두 코퍼스를 함께 물어야 하는 질의가 생길 때까지 미룬다 |

전체 근거는 [`../learnings/verdict.md`](../learnings/verdict.md)에 있으며,
IRI 결정의 세부 내용은 [`iri-policy.md`](notes/iri-policy.md)에서 확인할 수 있다.

### 여기까지 오면서 확정한 것

| 결정 | 근거 |
|---|---|
| 부재는 `fm_get` → `None`, `fm_list` → `[]` | 리스트는 "비어 있음 = 없음" |
| **RDF에는 NULL이 없다** | 값이 없으면 **트리플을 안 쓴다.** 열린 세계 가정의 시작 |
| 정규화는 **경계에서 한 번만** | 링크 5,341개(21.9%)가 여기 걸려 있다 |
| 「가깝다」 = **소스와 같은 폴더** | 넓히면 1,443개가 틀린 곳으로 간다 |
| **읽을 문서 ≠ 링크 대상** | 합치면 이미지 임베드 582건을 깨진 링크로 잘못 분류한다 |
| lint 제외는 **커밋되는 설정 파일**에 | 무엇을 왜 뺐는지가 감사 대상 |
| `main`은 정수를 돌려주고 `sys.exit`은 파일 끝 한 줄에만 | 프로세스 없이 테스트한다 |
| **바뀔 것을 이음매 하나에 가둔다** | `doc_iri`(정체성) · `resolve` 인자(해석) |
| 「있는가」가 아니라 **「결과가 달라지는가」**를 잰다 | 펜스 혼용 10건, 파싱 차이 0 |

### Phase 6 실측 (2026-08-24)

```
uv run python -m vault lint        # 382 위반
uv run python -m vault build       # SQLite
uv run python -m vault rdf         # .vault.ttl
```

| | SQLite | RDF | |
|---|---:|---:|---|
| 문서 | 3,993 | **3,993** | ✅ |
| `builds_on` / `supersedes` | 415 / 5 | **415 / 5** | ✅ |
| 태그 | 3,352 | **3,352** | ✅ |
| `links_to` | 10,622 | 9,359 | 집합이라 중복 1,162건이 하나로 합쳐진다 |
| `part_of` | 1,020 | 4,758 | 폴더가 리소스가 됐다 |
| **합계** | 엣지 12,057 | **트리플 27,515개** | |

추론 전 데이터 27,529개와 온톨로지 58개를 합친 뒤 OWL RL 추론을 돌리면
77,478개로 늘어난다(2.81배, 16.6초). 이 가운데 `rdfs:Resource`와 `owl:Thing`
14,656개는 실제 질의에 도움이 되지 않는 일반 타입 정보다.

> **`800 TRPG`가 2026-08-23에 vault 밖으로 나갔다** — [`800-trpg-split.md`](notes/800-trpg-split.md).
> Phase 6·9의 실습 대상이 「제외 구역」에서 **「출처가 다른 독립 코퍼스」**로 바뀌었고,
> 문제가 약해진 게 아니라 **RDF가 원래 풀려던 문제**가 됐다.

---

## 다음 시작점 — 3부 Phase 10

2부의 "검색을 위해 온톨로지를 더 쌓지 않는다"는 결론을 유지한다. 3부는 검색 개선이
아니라 문서 안의 주장·사건·결정·원칙과 그 근거를 모델링하여 실제 역량 질문에 답하는
별도 목표다. 범위는 개발 지식에 한정하지 않고 개인 경험·성찰·철학·커리어·생활을
포함한 Vault 전체다. Phase 10은 000~700 대역별 질문과 영역 사이를 잇는 질문을
함께 고정하는 데서 시작한다.

> **시작 전에 정한 것은 [`part3-decisions.md`](part3/decisions.md)에 있다.**
> 라벨링 파일럿을 앞으로 당긴 이유(D1), 종착점을 Phase 18로 둔 이유(D2),
> 900 Archive와 100 Private Log의 참여 방식(D3·D4), 역량 질문을 캐내는 절차(D5),
> 프라이버시 규칙의 축을 바꾼 이유(D6), 그리고 Phase 13·14 선행 관측이 거기 있다.

> **⏳ 지금 막혀 있는 곳 — [`part3-open-decisions.md`](part3/open-decisions.md)**
> Phase 10 산출물은 전부 나왔고 **토마토의 결정 8건을 기다린다.** 그중 1·3·4가
> 없으면 Phase 11로 넘어갈 수 없다.

### Phase 10 산출물

| | |
|---|---|
| [`competency-questions.md`](part3/competency-questions.md) | 역량 질문 30개 · **전수 판정 완료** |
| [`part3-boundary.md`](part3/boundary.md) | 목표·비목표·계층 책임·기준선·**갈림길** |
| [`part3-risks.md`](part3/risks.md) | 위험 15항목. 1군 5개는 이번에 실제로 관측된 것 |
| [`part3-open-decisions.md`](part3/open-decisions.md) | 미결 8건 |

**판정 결과 30개 중 18개가 「그 사실이 적혀 있지 않다」였다.** 그리고 그중 12개는
frontmatter 필드를 늘리면 **기존 SQLite가 그대로 답한다**(실증). 3부의 정당성은
「문서보다 작은 단위가 필요한가」 하나에 걸려 있고, 그것을 재는 것이 Phase 11이다.

진행 순서는 [`README.md`](README.md)의 3부 표와 각 Phase 가이드를 따른다.

1. [`phase10.md`](phases/phase10.md) — 역량 질문·비목표·위험 장부 ✅
2. [`phase11.md`](phases/phase11.md) — **라벨링 파일럿.** 문서 8~10개, 비용 측정
3. [`phase12.md`](phases/phase12.md) — **의미 작성 계약**과 gold set 50개
4. [`phase13.md`](phases/phase13.md) — 문서와 지식 개체 분리, 안정 ID
5. [`phase14.md`](phases/phase14.md) — 핵심 도메인 온톨로지 0.1
6. [`phase15.md`](phases/phase15.md) — asserted/proposed/inferred 그래프
7. [`phase16.md`](phases/phase16.md) — SHACL 의미 계약
8. [`phase17.md`](phases/phase17.md) — 목적 제한 추론과 철회 가능한 운영 규칙
9. [`phase18.md`](phases/phase18.md) — 의미 질의와 근거 설명 — **3부의 종착점**

[`phase19.md`](phases/phase19.md)와 [`phase20.md`](phases/phase20.md)는 보류한다. 문서는 지우지
않는다. Phase 18의 2주 실사용에서 가치가 확인되면 그때 다시 판단한다.

> **그 2주가 재는 축이 둘이다** (2026-08-31 추가). 19·20의 가치와 함께
> **디렉토리 구성을 바꿔야 하는지**를 잰다. vault 정합화 세션이 「스키마가 경로를
> 정한다」로 뒤집지 않기로 하고 재편을 관찰 뒤로 미뤘는데, 그 관찰이 여기다 —
> 실제 질의가 돌아가야 「답이 안 나오는 이유가 경로인가」가 처음으로 갈린다.
> 기록할 항목은 [`phase18.md`](phases/phase18.md) Step 5에 있다.

### Phase 10 전에 하지 않을 것

- 새 클래스와 OWL 공리부터 추가하지 않는다.
- 현재 `v:ConceptDocument`·`v:PrincipleDocument`를 실제 개념·원칙 의미로 바꾸지 않는다.
  (Phase 13에서 개명했다. 접미가 없는 이름은 지식 개체 몫으로 비어 있다.)
- VectorDB 구현을 이 로드맵에 섞지 않는다.
- RDF 저장 엔진을 교체하지 않는다.
- 전체 Vault 자동 의미 추출을 시작하지 않는다.
- 에이전트 쓰기 권한을 붙이지 않는다.

### 병행하지만 별도인 운영 개선

- 생성 계열 명령 이관: [`cli-roadmap.md`](backlog/cli-roadmap.md)
- vault 운영 백로그: [`vault-backlog.md`](backlog/vault-backlog.md)
- 태그 어휘가 언제 늘어도 되는가: [`tag-policy.md`](notes/tag-policy.md)
  (`vault tags --health` · `--judge`. 정본의 「새 축을 만들지 않는다」를 축과 값으로 갈랐다)
- 스키마 정본에 3역할 계층과 최종 결론 반영
- 실제로 두 코퍼스를 함께 물어야 하는 질의가 생기면 RDF 병합 재검토
- VectorDB·임베딩 검색: [`retrieval-architecture.md`](notes/retrieval-architecture.md). 3부에서는
  `chunk_id → artifact IRI → knowledge entity` 연결 계약만 다룬다

---

## 커밋 규칙 (Conventional Commits)

**기본은 하나로 담는다.** 구현 · 테스트 · `learnings/` · 문서 갱신까지 커밋 하나.
Step 하나가 곧 커밋 하나다. 잘게 쪼개면 이력이 오히려 안 읽힌다.

| 시점 | type | 예 |
|---|---|---|
| GREEN (구현·테스트·학습노트 함께) | `feat` | `feat(frontmatter): fm_list — 리스트 블록 파싱` |
| 실측 (스크립트·결과·회고 함께) | `feat(tools)` | `feat(tools): Phase 1 파서 실측` |
| REFACTOR | `refactor` | `refactor(frontmatter): 키 매칭 정규식을 헬퍼로 추출` |
| 기존 동작이 틀렸던 것 | `fix` | `fix(links): 표 안의 \|가 타깃 끝에 역슬래시를 남기던 문제` |
| **코드가 안 바뀐 때만** | `docs` | `docs: Phase 2 가이드 — 위키링크 파서` |

- RED는 커밋하지 않는다 — 실패 상태가 이력에 남으면 `git bisect`를 못 쓴다. GREEN 커밋에 테스트가 같이 들어가므로 명세는 보존된다
- GREEN과 REFACTOR를 **한 커밋에 섞지 않는다.** 섞으면 diff에서 "기능이 바뀐 건가 정리한 건가"를 읽을 수 없다
- 메시지는 **영어로, 제목 한 줄 + 불릿 2~3개.** 길게 쓰지 않는다. 함정과 설계 결정의 상세는 `learnings/`가 맡는다
- `Co-Authored-By` 트레일러는 쓰지 않는다

### scope

| Phase | scope |
|---|---|
| 1 | `frontmatter` |
| 2 | `links` |
| 3 | `scan` |
| 4 | `lint` |
| 5 | `graph` |
| 6 | `rdf` |
| 7 | `sparql` |
| 8 | `vocab` |
| 9 | `inference` |
| 10 | `questions` |
| 11 | `pilot` |
| 12 | `annotation` |
| 13 | `identity` |
| 14 | `domain-vocab` |
| 15 | `semantic-graph` |
| 16 | `shacl` |
| 17 | `rules` |
| 18 | `semantic-query` |
| 19 | `proposal` |
| 20 | `operations` |

---

## 진행 방식 요약

```
RED       테스트를 쓴다 → 실패를 눈으로 확인
GREEN     최소 구현 → 통과 → 커밋
REFACTOR  개선점 검토 (없으면 "없다"고 판단하는 것도 결과) → 있으면 별도 커밋
실측       실제 vault에 돌려 답안지 출력과 대조
```

**단위 테스트가 전부 초록이어도 실제 데이터에서 숫자가 다르면 틀린 것이다.**
