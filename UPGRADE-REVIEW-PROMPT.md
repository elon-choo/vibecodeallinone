# Claude Code Power Pack v2.0.0 — 업그레이드 검토 프롬프트

> **용도**: 새 세션에서 이 파일을 읽고 체계적으로 업그레이드/정리 작업 진행
> **작성일**: 2026-03-01
> **프로젝트**: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

---

## 1. 현재 상태 (완료됨)

### Git 히스토리
```
5463014 Add external review prompt kit (5 prompts for multi-AI review)
2ab36d4 Initial release: Claude Code Power Pack v2.0.0
```

### 이전 세션에서 완료한 작업 (미커밋, 23파일 변경 + 5파일 신규)

| # | 작업 | 변경 파일 수 |
|---|------|------------|
| 1 | password123 제거 (env var 참조로 교체) | hooks 7개 + kg-mcp 4개 |
| 2 | CHANGELOG.md 생성 (Keep a Changelog) | 1 신규 |
| 3 | GitHub Actions CI (.github/workflows/ci.yml) | 1 신규 |
| 4 | bare `except:` → 구체적 예외 (8곳, 4파일) | 4 수정 |
| 5 | 테스트 추가 (pytest 40 passed) | 4 신규 |
| 6 | SKILL.md frontmatter 정규화 (license 추가, graph-loader FM 추가) | 10 수정 |
| 7 | 테스트 템플릿 password123 → Test1234! | 2 수정 |

### 쓰레기 파일
- `2\r` (루트에 있는 32바이트 파일, 삭제 필요)

---

## 2. 즉시 처리 필요 (커밋 전)

### 2-1. 쓰레기 파일 삭제
```bash
rm "$(ls | grep '^2')"
```

### 2-2. .gitignore 보강
현재 `.pytest_cache/`가 없음. 추가 필요:
```
.pytest_cache/
tests/__pycache__/
```

### 2-3. 미커밋 변경사항 커밋
```bash
git add -A && git commit -m "v2.0.0 release prep: CI, tests, security hardening, frontmatter normalization"
```

### 2-4. GitHub Push + Release
```bash
git push origin main
gh release create v2.0.0 --title "v2.0.0" --notes-file CHANGELOG.md
```

---

## 3. 품질 업그레이드 — 검토 항목

### 3-1. SKILL.md description 언어 불일치 (HIGH)
현재 12개 중 9개가 한국어, 3개가 영어:

| 언어 | Skills |
|------|--------|
| EN | clean-code-mastery, graph-loader, vibe-coding-orchestrator |
| KO | arch-visualizer, code-reviewer, code-smell-detector, codebase-graph, impact-analyzer, naming-convention-guard, security-shield, smart-context, tdd-guardian |

**결정 필요**: 오픈소스이므로 전체 영어로 통일할지?
- Claude Code는 description 기반으로 skill 매칭하므로 키워드가 중요
- 영어로 통일하되, 한국어 trigger keywords는 본문에 유지하는 방안 추천

### 3-2. allowed-tools 포맷 불일치 (MEDIUM)
3개는 `string` 형식, 9개는 `list` 형식:
- STR: clean-code-mastery, graph-loader, vibe-coding-orchestrator
- LIST: 나머지 9개

**추천**: Claude Code 공식 Agent Skills 스펙에 맞는 포맷으로 통일

### 3-3. frontmatter 스키마 불일치 (MEDIUM)
- clean-code-mastery와 vibe-coding-orchestrator만 `compatibility`와 `metadata` 필드 있음
- 나머지 10개는 최소 필드(name, description, license, allowed-tools)만
- **추천**: 전체에 `metadata.version`, `metadata.author` 추가

### 3-4. Type Hint 커버리지 (LOW)
- 518개 함수 중 270개(52%)만 return type hint
- **추천**: hooks/*.py와 kg-mcp-server 주요 함수에 type hint 추가

---

## 4. 보안 추가 검토

### 4-1. password123 최종 현황
```
security-shield/patterns/validation.md:130 — 커먼 패스워드 블랙리스트 (정상, 탐지 패턴)
```
→ 실제 크리덴셜 아님. OK.

### 4-2. API key 노출 검토
- `tests/test_config.py` — `"voy-test-key"` 테스트 더미값 (OK)
- `graph-loader/loader.py` — `os.getenv`로 로딩 (OK)
- `kg-mcp-server/pipeline/embedding_pipeline.py` — env var 로딩 (OK)
- `observability/logger.py` — sensitive key 마스킹 로직 있음 (OK)

### 4-3. gitleaks CI 추가 완료
`.github/workflows/ci.yml`에 gitleaks-action 포함됨.

### 4-4. 추가 보안 체크 (선택)
- [ ] `.env.example`에 `your-neo4j-password` — gitleaks가 잡을 수 있음. `.gitleaks.toml` allowlist 필요할 수 있음
- [ ] `graph-loader/loader.py`에서 `NEO4J_PASSWORD` 환경변수 로딩 확인
- [ ] hooks에서 환경변수 미설정 시 graceful degradation 동작 확인

---

## 5. 구조/아키텍처 업그레이드

### 5-1. kg-mcp-server import 경로 문제
`server.py:36`에서 `from mcp_server.config import config` 사용하지만,
실제 디렉토리는 `kg-mcp-server/`임 (`mcp_server`가 아님).
- 설치 시 venv에서 `kg-mcp-server/` → `mcp_server` 심볼릭 or PYTHONPATH 설정 필요
- `install.sh` Tier 2에서 이 부분이 자동 처리되는지 검증 필요

### 5-2. kg-mcp-server/tools/ 비어있음
`tools/__init__.py`만 존재. server.py에서 tools를 직접 등록하는 구조.
- **추천**: 각 tool을 `tools/` 하위 파일로 분리하면 유지보수성 향상
- 현재 server.py가 매우 클 수 있음 (확인 필요)

### 5-3. pipeline/ 모듈 (24개 파일, ~14,800 LOC)
```
adaptive_context.py, auto_test_gen.py, bug_radar.py, cache.py,
code_assist.py, code_describer.py, context_builder.py, dedup_engine.py,
doc_generator.py, embedding_pipeline.py, graph_search.py, hybrid_search.py,
impact_simulator.py, knowledge_transfer.py, llm_judge.py, ontology_evolver.py,
query_router.py, rag_engine.py, shared_memory.py, ts_parser.py,
vector_search.py, weight_learner.py, write_back.py
```
- 코드량이 상당함. 주요 모듈별 단위 테스트 추가 고려
- `__init__.py`에서 public API 정리 필요

### 5-4. pyproject.toml 미존재
- `package.json`만 있고 Python 패키징 설정 없음
- **추천**: `pyproject.toml` 추가 (ruff 설정, pytest 설정, 프로젝트 메타데이터)

---

## 6. 문서 업그레이드

### 6-1. README.md 보완
- [ ] 배지 추가: CI status, license, Python version
- [ ] "Quick Start" 섹션에 실제 스크린샷/GIF 추가 (선택)
- [ ] Troubleshooting 섹션 추가

### 6-2. docs/ 디렉토리
현재 `docs/REVIEW_PROMPT.md`만 존재.
- [ ] `docs/ARCHITECTURE.md` — 시스템 아키텍처 다이어그램
- [ ] `docs/SKILL-AUTHORING.md` — 새 스킬 만드는 가이드 (CONTRIBUTING.md 확장)
- [ ] `docs/KG-SETUP.md` — Neo4j + MCP 서버 상세 설정 가이드

### 6-3. CONTRIBUTING.md 업데이트
- 현재 내용이 기본적. hooks 기여 가이드, KG 관련 기여 가이드 추가

---

## 7. CI/CD 강화

### 7-1. 현재 CI (완료)
- install.sh Tier 1 smoke test
- Python lint (ruff)
- SKILL.md frontmatter 검증
- gitleaks 시크릿 스캔
- pytest

### 7-2. 추가 가능 CI
- [ ] kg-mcp-server requirements.txt install test (pip install 성공 여부)
- [ ] SKILL.md 내용 lint (description 최대 길이, 금지 키워드 등)
- [ ] Markdown lint (markdownlint)
- [ ] hooks Python 3.11+ 호환성 테스트
- [ ] Coverage report (codecov)

---

## 8. 경쟁 분석 / 차별화 조사

오픈소스 릴리스 전 확인할 만한 유사 프로젝트:
- [ ] `aider` — AI coding assistant (이미 대규모)
- [ ] `continue` — VS Code AI extension
- [ ] `cline` — Autonomous AI coding agent
- [ ] `cursor-tools` — Cursor에 플러그인 추가
- [ ] Agent Skills 관련 — Claude Code 공식 skill 생태계 현황

**차별화 포인트 정리**:
- Knowledge Graph 기반 코드 컨텍스트 (unique)
- 12개 skill 통합 orchestration (unique)
- 3-tier 설치 (graceful degradation)
- Cross-tool 호환 (Claude/Codex/Gemini/Cursor/Windsurf)

---

## 9. 추천 작업 우선순위

| 우선순위 | 작업 | 예상 난이도 |
|---------|------|-----------|
| P0 | 쓰레기 파일 삭제 + gitignore 보강 + 커밋 + push | 5분 |
| P0 | GitHub Release v2.0.0 생성 | 2분 |
| P1 | SKILL.md description 영어 통일 | 30분 |
| P1 | allowed-tools 포맷 통일 | 10분 |
| P1 | pyproject.toml 생성 (ruff/pytest 설정 포함) | 15분 |
| P2 | README 배지 + Troubleshooting 추가 | 20분 |
| P2 | .gitleaks.toml allowlist (env.example 오탐 방지) | 5분 |
| P2 | frontmatter에 metadata.version/author 통일 | 20분 |
| P3 | docs/ 아키텍처 문서 | 1시간 |
| P3 | kg-mcp-server 단위 테스트 확장 | 2시간 |
| P3 | Type hint 커버리지 향상 (52% → 80%) | 2시간 |

---

## 10. 새 세션 시작 프롬프트

```
claude-code-power-pack v2.0.0 오픈소스 릴리스 최종 정리.

프로젝트 루트: /Users/elon/Documents/elon_opensource/claude-code-power-pack/

UPGRADE-REVIEW-PROMPT.md를 읽고 다음 순서로 진행:

1. P0: 쓰레기 파일(2\r) 삭제, .gitignore 보강, 미커밋 변경사항 커밋, push
2. P0: GitHub Release v2.0.0 생성 (CHANGELOG.md 기반)
3. P1: SKILL.md description 전체 영어 통일 (한국어 trigger는 본문 유지)
4. P1: allowed-tools 포맷 통일 (string vs list → 하나로)
5. P1: pyproject.toml 생성 (ruff, pytest, 프로젝트 메타데이터)
6. P2: README 배지 추가, .gitleaks.toml 생성
7. 커밋 + push

각 단계 완료 후 변경 파일 목록 보여주고, 최종 grep password123 재검증.
```
