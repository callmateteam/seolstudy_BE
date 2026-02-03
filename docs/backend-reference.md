# 설스터디(SeolStudy) 백엔드 설계 레퍼런스 문서

> 이 문서는 구현 전 과정에서 참조하는 **단일 진실 공급원(Single Source of Truth)**이다.
> 모든 코드 작성, API 설계, DB 모델링 시 이 문서의 규칙을 따른다.

---

## 1. 프로젝트 개요

**설스터디**: 자체 콘텐츠 기반 수능 국영수 학습 코칭 플랫폼
- 멘토(대학생)가 멘티(수험생)에게 일일 학습 플래너 제공
- AI 학습 밀도 분석 + 멘토 피드백으로 학습 관리
- 핵심 루프: 과제 제출 → AI 밀도 분석 → 멘토 피드백

### 확정된 MVP 범위
| 항목 | 결정 | 근거 |
|---|---|---|
| 회원가입 | 회원가입 + 온보딩 포함 | 기본설계 기준 |
| 성장 리포트 | MVP에서 **제외** | PRD에서 '뺄 거' 표시 |
| 학부모 | 별도 역할로 로그인 | PRD 기준 |
| AI 밀도 분석 | MVP에 **포함** | 핵심 루프의 필수 요소 |
| 보완 학습지 추천 | MVP에 포함 | 코칭센터 내 기능 |

### Tech Stack
| 구분 | 기술 |
|---|---|
| 프레임워크 | Python FastAPI |
| DB | PostgreSQL |
| ORM | Prisma (prisma-client-py) |
| 인증 | JWT (access + refresh token) |
| 문서화 | Swagger (FastAPI 자동 생성) |
| 파일 저장 | AWS S3 |
| OCR | AWS Textract (학습 밀도 분석용) |
| 비동기 | FastAPI BackgroundTasks |
| 패스워드 | bcrypt 해싱 |

---

## 2. 코드 규칙 및 컨벤션

### 2.1 프로젝트 구조
```
seolstudy/
├── main.py                    # FastAPI 앱 진입점
├── prisma/
│   └── schema.prisma          # DB 스키마 정의
├── app/
│   ├── core/
│   │   ├── config.py          # 환경변수, 설정값
│   │   ├── security.py        # JWT 생성/검증, 비밀번호 해싱
│   │   ├── deps.py            # 의존성 주입 (get_current_user 등)
│   │   └── permissions.py     # 역할 기반 권한 체크 데코레이터
│   ├── routers/               # API 엔드포인트 (컨트롤러)
│   │   ├── auth.py
│   │   ├── onboarding.py
│   │   ├── planner.py
│   │   ├── tasks.py
│   │   ├── submissions.py
│   │   ├── uploads.py
│   │   ├── analysis.py
│   │   ├── judgments.py
│   │   ├── feedback.py
│   │   ├── mentor_dashboard.py
│   │   ├── coaching.py
│   │   ├── materials.py
│   │   ├── parent.py
│   │   └── settings.py
│   ├── schemas/               # Pydantic request/response 모델
│   │   ├── auth.py
│   │   ├── task.py
│   │   ├── submission.py
│   │   ├── analysis.py
│   │   ├── feedback.py
│   │   ├── material.py
│   │   └── common.py          # 공통 응답 모델
│   └── services/              # 비즈니스 로직
│       ├── auth_service.py
│       ├── task_service.py
│       ├── submission_service.py
│       ├── analysis_service.py
│       ├── feedback_service.py
│       ├── coaching_service.py
│       ├── s3_service.py         # AWS S3 업로드/다운로드/presigned URL
│       ├── textract_service.py   # AWS Textract OCR 호출 + 결과 파싱 (DRAWING 모드)
│       ├── text_analysis_service.py  # 텍스트 기반 밀도 분석 (TEXT 모드)
│       └── file_service.py
├── requirements.txt
├── .env
└── .env.example
```

### 2.2 네이밍 컨벤션
| 대상 | 규칙 | 예시 |
|---|---|---|
| 파일명 | snake_case | `mentor_dashboard.py` |
| 클래스 | PascalCase | `TaskCreateRequest` |
| 함수/변수 | snake_case | `get_tasks_by_date()` |
| 상수 | UPPER_SNAKE | `MAX_IMAGE_SIZE_MB = 5` |
| API 경로 | kebab-case (하이픈 X, 슬래시+명사) | `/api/tasks/{taskId}/submissions` |
| DB 테이블 | PascalCase (Prisma) | `Task`, `AiAnalysis` |
| DB 필드 | camelCase (Prisma) | `menteeId`, `signalLight` |
| Enum | UPPER_SNAKE | `GREEN`, `YELLOW`, `RED` |

### 2.3 코딩 규칙

**일반 규칙:**
- 모든 함수에 type hint 필수
- 비즈니스 로직은 반드시 `services/`에 작성. `routers/`는 요청/응답 처리만
- 하드코딩 금지. 상수는 `config.py` 또는 enum으로 관리
- 매직 넘버 금지. 의미 있는 상수명 사용
- 한 함수는 하나의 책임만 가짐 (SRP)
- 함수 길이 50줄 이하 권장. 초과 시 분리

**FastAPI 규칙:**
- 라우터별 prefix 사용: `router = APIRouter(prefix="/api/tasks", tags=["Tasks"])`
- 모든 엔드포인트에 response_model 명시
- 에러는 HTTPException으로 처리. 커스텀 에러코드 사용
- 의존성 주입으로 인증/권한 처리: `Depends(get_current_user)`

**Prisma 규칙:**
- `prisma generate` 후 생성된 클라이언트 사용
- 트랜잭션이 필요한 경우 `prisma.tx()` 사용
- N+1 방지: `include`로 관계 데이터 함께 조회
- 날짜 필드는 항상 UTC로 저장, 응답 시 ISO 8601 형식

### 2.4 API 응답 표준

**성공 응답:**
```json
{
  "success": true,
  "data": { ... },
  "message": "optional message"
}
```

**리스트 응답 (페이지네이션 있을 때):**
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "해당 할 일을 찾을 수 없습니다"
  }
}
```

**HTTP 상태 코드 규칙:**
| 코드 | 용도 |
|---|---|
| 200 | 조회/수정 성공 |
| 201 | 생성 성공 |
| 204 | 삭제 성공 (body 없음) |
| 400 | 잘못된 요청 (유효성 검증 실패) |
| 401 | 인증 실패 (토큰 없음/만료) |
| 403 | 권한 없음 (역할 불일치) |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복 이메일 등) |
| 422 | Pydantic 유효성 검증 실패 |
| 500 | 서버 내부 오류 |

### 2.5 에러 코드 체계
```
AUTH_001: 잘못된 이메일/비밀번호
AUTH_002: 토큰 만료
AUTH_003: 유효하지 않은 토큰
AUTH_004: 이미 존재하는 이메일
PERM_001: 권한 없음 (역할)
PERM_002: 권한 없음 (데이터 소유권)
TASK_001: 할 일을 찾을 수 없음
TASK_002: 잠긴 할 일 수정 시도
TASK_003: 담당하지 않는 멘티의 할 일
SUBMIT_001: 이미지 업로드 실패
SUBMIT_002: 지원하지 않는 파일 형식
SUBMIT_003: 파일 크기 초과
ANALYSIS_001: 분석 아직 진행 중
ANALYSIS_002: 분석 실패
ANALYSIS_003: 제출물 없음
JUDGE_001: 사유 입력 필수
JUDGE_002: 이미 확정된 판정
FEEDBACK_001: 판정 미확정 상태
```

### 2.6 보안 규칙
- 비밀번호: bcrypt로 해싱 (절대 평문 저장 금지)
- JWT: access token (30분), refresh token (7일)
- SQL Injection: Prisma가 자동 방어하지만, raw query 사용 금지
- 파일 업로드: 확장자 화이트리스트 (jpg, jpeg, png, pdf)
- 파일 크기 제한: 이미지 5MB, PDF 20MB
- CORS: 프론트엔드 도메인만 허용
- 멘티는 자신의 데이터만 조회 가능
- 멘토는 담당 멘티 데이터만 조회 가능
- 학부모는 연결된 자녀 데이터만 조회 가능
- AWS 자격증명: 환경변수로 관리 (`.env`), 코드에 하드코딩 금지
- S3 버킷 접근: IAM 역할 기반, presigned URL로 프론트 직접 다운로드

---

## 3. DB 모델 (Prisma Schema)

### 3.1 Enum 정의
```prisma
enum Role {
  MENTEE
  MENTOR
  PARENT
}

enum Subject {
  KOREAN    // 국어
  ENGLISH   // 영어
  MATH      // 수학
}

enum Grade {
  HIGH1     // 고1
  HIGH2     // 고2
  HIGH3     // 고3
  N_REPEAT  // N수
}

enum TaskStatus {
  PENDING      // 미완료
  SUBMITTED    // 제출됨
  ANALYZING    // AI 분석 중
  COMPLETED    // 완료 (신호등 결과 있음)
  FAILED       // 분석 실패
}

enum SignalLight {
  GREEN    // 밀도 높음
  YELLOW   // 부분적
  RED      // 풀이 흔적 없음
}

enum MaterialType {
  COLUMN   // 설스터디 칼럼
  PDF      // PDF 학습지
}

enum AnalysisStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
}

enum CreatedBy {
  MENTOR
  MENTEE
}

enum SubmissionType {
  TEXT      // 텍스트 직접 입력 (키보드)
  DRAWING   // 그리기/손글씨 (이미지 → OCR 분석)
}
```

### 3.2 테이블 정의

```prisma
model User {
  id            String   @id @default(uuid())
  email         String   @unique
  passwordHash  String
  role          Role
  name          String
  phone         String?
  profileImage  String?
  nickname      String?
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  menteeProfile  MenteeProfile?
  mentorProfile  MentorProfile?
  parentProfile  ParentProfile?
}

model MenteeProfile {
  id              String   @id @default(uuid())
  userId          String   @unique
  user            User     @relation(fields: [userId], references: [id])
  grade           Grade
  subjects        Subject[]
  currentGrades   Json     // { "KOREAN": 3, "ENGLISH": 2, "MATH": 4 }
  targetGrades    Json     // { "KOREAN": 1, "ENGLISH": 1, "MATH": 2 }
  onboardingDone  Boolean  @default(false)
  createdAt       DateTime @default(now())

  mentors         MentorMentee[]
  tasks           Task[]
  submissions     TaskSubmission[]
  feedbacks       Feedback[]
  comments        DailyComment[]
  parentLink      ParentProfile[]
}

model MentorProfile {
  id                 String   @id @default(uuid())
  userId             String   @unique
  user               User     @relation(fields: [userId], references: [id])
  university         String
  department         String
  subjects           Subject[]
  coachingExperience Boolean  @default(false)
  onboardingDone     Boolean  @default(false)
  createdAt          DateTime @default(now())

  mentees     MentorMentee[]
  judgments   MentorJudgment[]
  feedbacks   Feedback[]
}

model ParentProfile {
  id        String   @id @default(uuid())
  userId    String   @unique
  user      User     @relation(fields: [userId], references: [id])
  menteeId  String
  mentee    MenteeProfile @relation(fields: [menteeId], references: [id])
  createdAt DateTime @default(now())
}

model MentorMentee {
  id        String        @id @default(uuid())
  mentorId  String
  mentor    MentorProfile @relation(fields: [mentorId], references: [id])
  menteeId  String
  mentee    MenteeProfile @relation(fields: [menteeId], references: [id])
  createdAt DateTime      @default(now())

  @@unique([mentorId, menteeId])
}

model Task {
  id               String       @id @default(uuid())
  menteeId         String
  mentee           MenteeProfile @relation(fields: [menteeId], references: [id])
  createdByMentorId String?
  date             DateTime     // 과제 날짜 (DATE만 사용)
  title            String
  goal             String?
  subject          Subject
  abilityTag       String?      // "문해력", "논리력" 등
  materialType     MaterialType?
  materialId       String?      // Material 테이블 참조
  materialUrl      String?      // PDF 직접 업로드 시 URL
  isLocked         Boolean      @default(false) // 멘토 생성 시 true
  status           TaskStatus   @default(PENDING)
  studyTimeMinutes Int?
  createdBy        CreatedBy
  displayOrder     Int          @default(0)
  createdAt        DateTime     @default(now())
  updatedAt        DateTime     @updatedAt

  submissions      TaskSubmission[]
  feedbackItems    FeedbackItem[]
}

model TaskSubmission {
  id               String         @id @default(uuid())
  taskId           String
  task             Task           @relation(fields: [taskId], references: [id])
  menteeId         String
  mentee           MenteeProfile  @relation(fields: [menteeId], references: [id])
  submissionType   SubmissionType // TEXT or DRAWING
  textContent      String?        // TEXT 모드: 멘티가 입력한 텍스트 풀이
  images           String[]       // DRAWING 모드: 그리기 이미지 URL 배열 (S3)
  selfScoreCorrect Int?
  selfScoreTotal   Int?
  wrongQuestions   Int[]          // 틀린 문항 번호
  submittedAt      DateTime       @default(now())

  analysis         AiAnalysis?
}

model AiAnalysis {
  id            String         @id @default(uuid())
  submissionId  String         @unique
  submission    TaskSubmission @relation(fields: [submissionId], references: [id])
  status        AnalysisStatus @default(PENDING)
  signalLight   SignalLight?
  densityScore  Int?           // 0~100
  writingRatio  Float?         // 필기량 비율 %
  traceTypes    Json?          // { "formula": 45, "underline": 20, "memo": 7.5 }
  pageHeatmap   Json?          // [{ "page": 1, "density": 90 }]
  summary       String?
  retryCount    Int            @default(0)
  createdAt     DateTime       @default(now())
  updatedAt     DateTime       @updatedAt

  judgment      MentorJudgment?
}

model MentorJudgment {
  id                String       @id @default(uuid())
  analysisId        String       @unique
  analysis          AiAnalysis   @relation(fields: [analysisId], references: [id])
  mentorId          String
  mentor            MentorProfile @relation(fields: [mentorId], references: [id])
  originalSignalLight SignalLight // AI 원본
  originalScore     Int          // AI 원본 점수
  finalSignalLight  SignalLight  // 최종 확정값
  finalScore        Int          // 최종 확정 점수
  reason            String?      // 수정 시 사유 (수정 시 필수)
  isModified        Boolean      @default(false)
  confirmedAt       DateTime     @default(now())
}

model Feedback {
  id              String        @id @default(uuid())
  menteeId        String
  mentee          MenteeProfile @relation(fields: [menteeId], references: [id])
  mentorId        String
  mentor          MentorProfile @relation(fields: [mentorId], references: [id])
  date            DateTime      // 피드백 대상 날짜
  summary         String?       // 요약 (멘티에게 강조 표시)
  isHighlighted   Boolean       @default(false)
  generalComment  String?       // 총평
  sentAt          DateTime      @default(now())
  createdAt       DateTime      @default(now())

  items           FeedbackItem[]
}

model FeedbackItem {
  id          String   @id @default(uuid())
  feedbackId  String
  feedback    Feedback @relation(fields: [feedbackId], references: [id])
  taskId      String
  task        Task     @relation(fields: [taskId], references: [id])
  detail      String   // 할일별 상세 피드백
}

model DailyComment {
  id        String        @id @default(uuid())
  menteeId  String
  mentee    MenteeProfile @relation(fields: [menteeId], references: [id])
  date      DateTime
  content   String
  createdAt DateTime      @default(now())
}

model Material {
  id          String       @id @default(uuid())
  title       String
  type        MaterialType
  subject     Subject
  abilityTags String[]     // ["문해력", "논리력"]
  difficulty  Int?         // 1~5
  contentUrl  String       // 칼럼 HTML or PDF URL
  createdAt   DateTime     @default(now())
}
```

---

## 4. API 엔드포인트 전체 명세 (총 55개)

### Phase 1: Auth + Onboarding (7개)

#### Auth (4개)
| Method | Endpoint | 설명 | 권한 | Request | Response |
|---|---|---|---|---|---|
| POST | `/api/auth/signup` | 회원가입 | Public | `{email, password, name, phone, role}` | `{user, accessToken, refreshToken}` |
| POST | `/api/auth/login` | 로그인 | Public | `{email, password}` | `{user, accessToken, refreshToken}` |
| POST | `/api/auth/logout` | 로그아웃 | All | - | `204` |
| GET | `/api/auth/me` | 내 정보 | All | - | `{user, profile}` |

#### Onboarding (3개)
| Method | Endpoint | 설명 | 권한 | Request |
|---|---|---|---|---|
| PUT | `/api/onboarding/mentee` | 멘티 온보딩 | MENTEE | `{grade, subjects, currentGrades, targetGrades}` |
| PUT | `/api/onboarding/mentor` | 멘토 온보딩 | MENTOR | `{university, department, subjects, coachingExperience}` |
| PUT | `/api/onboarding/parent` | 학부모 온보딩 | PARENT | `{inviteCode}` (자녀 연결) |

---

### Phase 2: 멘티 기능 (31개)

#### Planner (6개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/planner?date=2026-02-03` | 날짜별 플래너 (할일+피드백+코멘트) | MENTEE |
| GET | `/api/planner/completion-rate?date=` | 해당일 완수율 | MENTEE |
| GET | `/api/planner/weekly?weekOf=` | 주간 캘린더 (일별 완수율/상태) | MENTEE |
| POST | `/api/planner/comments` | 코멘트/질문 등록 | MENTEE |
| GET | `/api/planner/comments?date=` | 코멘트 조회 | MENTEE, MENTOR |
| GET | `/api/planner/yesterday-feedback` | 어제자 피드백 요약 | MENTEE |

#### Tasks (6개)
| Method | Endpoint | 설명 | 권한 | 비고 |
|---|---|---|---|---|
| GET | `/api/tasks?menteeId=&date=` | 할 일 목록 | MENTEE, MENTOR | 멘티는 본인만, 멘토는 담당 멘티 |
| POST | `/api/tasks` | 할 일 생성 | MENTEE, MENTOR | 멘토 생성 시 isLocked=true |
| GET | `/api/tasks/{taskId}` | 할 일 상세 (학습지 정보 포함) | MENTEE, MENTOR | |
| PUT | `/api/tasks/{taskId}` | 할 일 수정 | MENTEE(본인, unlocked), MENTOR | isLocked 체크 |
| DELETE | `/api/tasks/{taskId}` | 할 일 삭제 | MENTEE(본인, unlocked), MENTOR | |
| PATCH | `/api/tasks/{taskId}/study-time` | 공부 시간 기록 | MENTEE | `{minutes: 45}` |

#### Submissions (3개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| POST | `/api/tasks/{taskId}/submissions` | 과제 제출 (multipart) | MENTEE |
| GET | `/api/tasks/{taskId}/submissions` | 제출 내역 조회 | MENTEE, MENTOR |
| PUT | `/api/submissions/{id}/self-score` | 자기 채점 | MENTEE |

#### Uploads (3개)
| Method | Endpoint | 설명 | 권한 | 제한 |
|---|---|---|---|---|
| POST | `/api/uploads/image` | 이미지 업로드 (S3) | MENTEE, MENTOR | JPG/PNG, 5MB |
| POST | `/api/uploads/pdf` | PDF 업로드 (S3) | MENTOR | PDF, 20MB |
| POST | `/api/uploads/validate-image` | 이미지 품질 검증 | MENTEE | 흐림/어두움 감지 |

#### AI Analysis (4개)
| Method | Endpoint | 설명 | 권한 | 비고 |
|---|---|---|---|---|
| POST | `/api/analysis/{submissionId}/trigger` | AI 분석 시작 | System | 제출 시 자동 호출 (BackgroundTask) |
| GET | `/api/analysis/{submissionId}` | 분석 결과 | MENTEE, MENTOR | 멘티는 확정값만 |
| GET | `/api/analysis/{submissionId}/status` | 분석 상태 | MENTEE | 폴링용 (5초 간격) |
| POST | `/api/analysis/{submissionId}/retry` | 재시도 | MENTEE | 실패 시 수동 재시도 |

#### Materials (4개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/materials?subject=&type=` | 학습지 목록 | ALL |
| GET | `/api/materials/{materialId}` | 학습지 상세 | ALL |
| POST | `/api/materials` | 학습지 등록 | MENTOR |
| GET | `/api/materials/{materialId}/download` | PDF 다운로드 | ALL |

#### Feedback 조회 (3개, 멘티 측)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/feedback?menteeId=&date=` | 날짜별 피드백 | MENTEE, MENTOR |
| GET | `/api/feedback/by-subject?menteeId=&subject=` | 과목별 피드백 (최신순) | MENTEE |
| GET | `/api/feedback/{feedbackId}` | 피드백 상세 (할일별+총평) | MENTEE, MENTOR |

#### Settings 멘티 (2개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/settings/profile` | 프로필 조회 | ALL |
| PUT | `/api/settings/mentee` | 멘티 설정 (목표등급, 과목) | MENTEE |

---

### Phase 3: 멘토 기능 (14개)

#### Mentor Dashboard (4개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/mentor/dashboard` | 대시보드 종합 (멘티목록+대기열) | MENTOR |
| GET | `/api/mentor/mentees` | 담당 멘티 목록 | MENTOR |
| GET | `/api/mentor/mentees/{menteeId}` | 멘티 상세 (플래너+과제현황+피드백이력) | MENTOR |
| GET | `/api/mentor/review-queue` | 검토 대기열 | MENTOR |

**대기열 정렬 로직:**
1. signalLight = RED 우선
2. 경과시간(submittedAt ~ now) 긴 순
3. 최신 제출순

#### Judgment (3개)
| Method | Endpoint | 설명 | 권한 | Request |
|---|---|---|---|---|
| POST | `/api/judgments/{analysisId}/confirm` | AI 판정 확정 | MENTOR | - (AI 값 그대로) |
| POST | `/api/judgments/{analysisId}/modify` | 판정 수정 | MENTOR | `{signalLight, score, reason}` reason 필수 |
| GET | `/api/judgments/{analysisId}` | 판정 결과 | MENTOR | |

#### Coaching Center (4개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/coaching/{submissionId}` | 종합 (인증샷+AI분석+매핑) | MENTOR |
| GET | `/api/coaching/{submissionId}/ai-draft` | AI 피드백 초안 | MENTOR |
| GET | `/api/coaching/{submissionId}/recommendations` | 보완 학습지 추천 | MENTOR |
| POST | `/api/coaching/assign-material` | 학습지 배정 → 멘티 할일 추가 | MENTOR |

#### Feedback 작성 (1개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| POST | `/api/feedback` | 피드백 작성+전송 | MENTOR |

**Request body:**
```json
{
  "menteeId": "uuid",
  "date": "2026-02-03",
  "items": [
    { "taskId": "uuid", "detail": "논리적 추론 과정이 개선됨..." }
  ],
  "summary": "오늘 국어 문해력 눈에 띄게 향상",
  "isHighlighted": true,
  "generalComment": "내일은 수학에 집중하자"
}
```

#### Settings 멘토 (2개)
| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| PUT | `/api/settings/profile` | 프로필 수정 | ALL |
| PUT | `/api/settings/mentor` | 멘토 설정 (담당과목, 멘티관리) | MENTOR |

---

### Phase 4: 학부모 기능 (3개)

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| GET | `/api/parent/dashboard` | 학부모 대시보드 (자녀 현황 종합) | PARENT |
| GET | `/api/parent/mentee-status` | 자녀 학습 현황 (완수율, 주간 밀도 분포) | PARENT |
| GET | `/api/parent/mentor-info` | 담당 멘토 정보 + 최근 피드백 횟수 | PARENT |

---

## 5. 핵심 비즈니스 로직

### 5.1 비동기 AI 분석 흐름 (SubmissionType 분기)
```
멘티 제출 (POST /submissions)
  → submissionType 확인
  → Task 상태 → ANALYZING
  → BackgroundTask 시작:

  [DRAWING 모드]
      1) 이미지 AWS S3 업로드 (s3://seolstudy-uploads/{menteeId}/{date}/{uuid}.jpg)
      2) AWS Textract로 OCR 수행 (필기량, 풀이 흔적 감지)
      3) OCR 결과 기반 밀도 분석 로직 실행 (신호등 판정 + 점수 산출)
      4) 결과 DB 저장

  [TEXT 모드]
      1) textContent를 직접 분석 (OCR 불필요)
      2) 텍스트 기반 밀도 분석: 글자 수, 풀이 단계 수, 수식 포함 여부
      3) 결과 DB 저장

  → 프론트: GET /analysis/{id}/status 폴링 (5초 간격)
  → 분석 완료: Task 상태 → COMPLETED, 신호등+점수 저장
  → 분석 실패: 자동 1회 재시도 → 최종 실패 시 Task → FAILED
  → 완료 시: 멘토 대기열에 자동 추가
```

### 5.1.1 DRAWING 모드: AWS Textract OCR 분석
```
[이미지 S3 업로드 완료]
  → Textract AnalyzeDocument API 호출 (S3 객체 참조)
  → 응답에서 추출:
      - WORD/LINE 블록 수 → 필기량 비율(writingRatio) 산출
      - 수식 패턴 감지 → traceTypes.formula
      - 밑줄/메모 감지 → traceTypes.underline, traceTypes.memo
      - 페이지별 블록 분포 → pageHeatmap
  → 밀도 점수 산출 로직:
      - writingRatio × 0.5 + traceVariety × 0.3 + coverage × 0.2
      - 70 이상: GREEN / 40~69: YELLOW / 39 이하: RED
```

### 5.1.2 TEXT 모드: 텍스트 기반 분석
```
[textContent 직접 분석]
  → 분석 항목:
      - 글자 수 / 풀이 단계 수 (줄바꿈 기준)
      - 수식 포함 여부 (정규식 패턴 매칭)
      - 논리 흐름 키워드 감지 ("따라서", "그러므로", "풀이:" 등)
  → writingRatio: (실제 글자 수 / 기대 글자 수) × 100
  → traceTypes: { "formula": 수식 수, "underline": 0, "memo": 키워드 수 }
  → 밀도 점수 산출: 동일 공식 적용
      - 70 이상: GREEN / 40~69: YELLOW / 39 이하: RED
```

### 5.2 멘토 판정 흐름
```
멘토: 코칭센터에서 AI 분석 결과 확인
  → [AI 판정 그대로 확정] or [판정 수정]
  → 수정 시: 사유 입력 필수
  → MentorJudgment 테이블에 원본+최종값 모두 저장
  → 멘티/학부모에게는 최종 확정값만 노출
```

### 5.3 권한 체크 로직
```python
# 멘티: 본인 데이터만 접근
if current_user.role == "MENTEE":
    assert resource.menteeId == current_user.menteeProfile.id

# 멘토: 담당 멘티 데이터만 접근
if current_user.role == "MENTOR":
    assert menteeId in [m.menteeId for m in current_user.mentorProfile.mentees]

# 학부모: 연결된 자녀 데이터만 접근
if current_user.role == "PARENT":
    assert menteeId == current_user.parentProfile.menteeId
```

### 5.4 할 일 잠금 로직
```python
# 할 일 수정/삭제 시
if task.isLocked and current_user.role == "MENTEE":
    raise HTTPException(403, "멘토가 등록한 할 일은 수정할 수 없습니다")
```

---

## 6. 검증 방법
1. `uvicorn main:app --reload` 서버 실행
2. `/docs` Swagger UI에서 전체 API 테스트
3. 핵심 루프 E2E 테스트:
   - 회원가입 → 온보딩 → 로그인
   - 멘토: 할일 등록
   - 멘티: 플래너 조회 → 과제 제출 → AI 분석 상태 확인
   - 멘토: 대기열 확인 → 판정 확정 → 피드백 작성 전송
   - 멘티: 피드백 확인
   - 학부모: 대시보드 조회
