---
name: code-reviewer
description: "**CODE REVIEWER**: '리뷰해', '검토해', '봐줘', '피드백', '확인해', '체크해', '코드 품질', '분석해', '이거 괜찮아?' 요청 시 자동 발동. Write/Edit 도구 사용 직후 자동 적용. Quality Gate, Code Smell, 복잡도 분석, 통합 점수 산출."
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Code Reviewer Skill

> **Version**: 1.0.0
> **Purpose**: AI 자체 코드 리뷰 체크리스트 및 품질 게이트
> **Target**: 모든 코드 생성/수정 시 자동 적용

---

## Document Loading Strategy

**전체 문서를 로드하지 않습니다!** 상황에 따라 필요한 문서만 로드:

```yaml
Document_Loading_Strategy:
  Step_1_Detect_Language:
    - 파일 확장자로 언어 감지
    - 언어별 네이밍 규칙, 관용구가 다름

  Step_2_Load_Required_Docs:
    Universal_Always_Load:
      - "core/quality-gates.md"        # Quality Gate (항상)
      - "core/code-smells.md"          # Code Smell 탐지 (항상)
      - "core/complexity.md"           # 복잡도 계산 (항상)

    Language_Specific_Load:
      TypeScript: "languages/typescript-review.md"   # TS 관용구, any 검사
      Python: "languages/python-review.md"           # PEP8, Pythonic
      Go: "languages/go-review.md"                   # Go 관용구, errcheck
      Rust: "languages/rust-review.md"               # Rust 관용구, unsafe
      Java: "languages/java-review.md"               # Java 관용구
      CSharp: "languages/csharp-review.md"           # C# 관용구
      Kotlin: "languages/kotlin-review.md"           # Kotlin 관용구
      Ruby: "languages/ruby-review.md"               # Ruby 관용구

    Context_Specific_Load:
      Naming: "patterns/naming-conventions.md"
      Scoring: "patterns/scoring-system.md"
      Checklist: "quick-reference/checklist.md"
      Integration: "quick-reference/integration.md"
```

---

## Base Knowledge (다른 스킬 참조)

> 이 스킬은 다른 전문 스킬들의 결과를 **통합하여 점수를 산출**합니다.

| 영역 | 참조 스킬 | 참조 내용 |
|------|----------|----------|
| **코드 품질** | `clean-code-mastery/core/principles.md` | SOLID, Clean Code |
| **보안 검사** | `security-shield` | OWASP Top 10, 취약점 |
| **테스트 품질** | `tdd-guardian` | TDD, Fake Test |
| **아키텍처** | `monorepo-architect` | 의존성 방향 |
| **API 설계** | `api-first-design` | REST, Swagger |

---

## Review Process Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Self-Review Process                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. 코드 생성/수정 완료                                         │
│          ↓                                                      │
│   2. Quick Check (문법, 타입, 네이밍)                            │
│          ↓                                                      │
│   3. Quality Gate Check (복잡도, 중복, 의존성)                   │
│          ↓                                                      │
│   4. Security Check (취약점, 시크릿)                             │
│          ↓                                                      │
│   5. Test Coverage Check                                        │
│          ↓                                                      │
│   6. 점수 산출 및 피드백                                         │
│      - 70점 미만: 수정 필요                                      │
│      - 70-85점: 권고 사항 제시                                   │
│      - 85점 이상: 승인                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

```yaml
Review_Levels:
  Quick: "단일 함수 (5초)"
  Standard: "파일 레벨 (10초)"
  Deep: "멀티 파일 (30초)"

Quality_Gates:
  Blocking:
    - "TypeScript Strict 통과"
    - "보안 취약점 없음"
    - "하드코딩 시크릿 없음"
  Warning:
    - "복잡도 ≤ 10"
    - "파일 길이 ≤ 300줄"
    - "테스트 커버리지 ≥ 80%"

Score_Weights:
  Code_Quality: 25%
  Security: 25%
  Test_Coverage: 20%
  Documentation: 15%
  Naming_Style: 15%

Grade_Threshold:
  A: 90+ (즉시 머지)
  B: 80-89 (마이너 수정 후)
  C: 70-79 (조건부 승인)
  D: 60-69 (대폭 수정)
  F: <60 (재작성)
```

---

## Module Files

| File | Description |
|------|-------------|
| `core/quality-gates.md` | Quality Gate 정의, 검사 함수 |
| `core/code-smells.md` | Code Smell 카테고리, 탐지 패턴 |
| `core/complexity.md` | Cyclomatic/Cognitive 복잡도 계산 |
| `patterns/naming-conventions.md` | 네이밍 규칙, 검증 |
| `patterns/scoring-system.md` | 점수 계산, 등급 기준 |
| `quick-reference/checklist.md` | 리뷰 체크리스트 템플릿 |
| `quick-reference/integration.md` | 다른 스킬 연동 |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-09
