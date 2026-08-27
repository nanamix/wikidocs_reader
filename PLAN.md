# BookOasis WikiDocs Plugin 기획서

## 1. 프로젝트 개요

- **프로젝트명:** `bookoasis-wikidocs`
- **형태:** BookOasis 독립 플러그인
- **기반 프로젝트:** `BookOasis_stable`
- **목표:** BookOasis 안에서 WikiDocs(`https://wikidocs.net`)의 공개 책을 검색하고 읽으며, 로그인한 각 사용자의 독서 목록·진척도·마지막 읽은 위치를 개별적으로 관리한다.

### 핵심 원칙

1. BookOasis Core를 수정하지 않는다.
2. 독립 플러그인으로 개발하고 별도 프로젝트/버전으로 관리한다.
3. BookOasis Core가 제공하는 사용자 인증/컨텍스트와 필요한 참조 정보만 사용한다. Core DB를 플러그인이 직접 조회하지 않는다.
4. WikiDocs의 공개 콘텐츠는 사용자 간 공유할 수 있지만 독서 데이터는 반드시 사용자별로 격리한다.
5. 클라이언트가 전달하는 `user_id`를 신뢰하지 않고 BookOasis의 로그인 Session에서 현재 사용자를 식별한다.

---

## 2. 사용자 목표

사용자는 BookOasis에서 WikiDocs의 공개 책을 찾아 다음과 같이 사용할 수 있어야 한다.

- 공개 책을 검색한다.
- 책 정보를 확인한다.
- 책의 목차를 확인한다.
- 책을 페이지 단위로 읽는다.
- 마지막으로 읽은 위치에서 이어 읽는다.
- 내가 읽고 있는/읽은 WikiDocs 책을 확인한다.
- 책의 진척도를 확인한다.
- 책을 **읽음 완료(완독)** 상태로 표시할 수 있다.
- 읽음 완료된 책을 **읽지 않음 상태로 초기화**할 수 있다.

---

## 3. MVP 범위

### 포함

1. WikiDocs 공개 책 검색
2. 검색 결과 표시
3. 책 상세 정보
4. 책 목차 표시
5. 페이지 본문 읽기
6. 이전/다음 페이지 이동
7. 마지막 읽은 페이지 저장
8. 페이지 내부 읽기 위치 저장
9. 사용자별 최근 읽은 책
10. 사용자별 책 진척도
11. 읽음 완료 처리
12. 읽지 않음 상태로 초기화
13. 이어 읽기
14. BookOasis UI/테마와 일관된 독립 플러그인 UI

### MVP에서 제외

- WikiDocs 계정 로그인
- WikiDocs 비공개 책
- WikiDocs 책 편집
- 책 복사/출판
- EPUB/PDF 등으로 책 다운로드 및 변환
- WikiDocs 댓글/소셜 기능
- WikiDocs 하이라이트/노트 동기화
- 추천/소셜 기능
- 불필요한 BookOasis Core 수정

---

## 4. 플러그인 UI 구조

BookOasis의 `category_tab`을 활용하여 독립적인 **WikiDocs** 메뉴를 제공한다.

```text
WikiDocs
│
├── 최근 읽은 책
│
├── 읽고 있는 책
│
├── 책 검색
│
└── 설정
```

### 메인 화면

```text
WikiDocs
────────────────────────────

최근 읽은 책

[책 표지]  책 제목
          진척도
          마지막 읽은 위치
          [계속 읽기]

읽고 있는 책

[책 A]  72%
[책 B]  31%

[책 검색]
```

### 검색 화면

검색어를 입력하여 WikiDocs 공개 책을 조회한다.

검색 결과에는 가능한 범위에서 다음 정보를 표시한다.

- 책 제목
- 저자
- 설명
- 표지
- 책 ID
- 페이지 수
- 공개 여부
- 최종 갱신 정보

### 책 상세 화면

```text
[책 표지]

책 제목
저자
설명

[이어 읽기]
[처음부터 읽기]
[읽음 완료 / 읽지 않음으로 변경]

목차
├── 장
│   ├── 페이지
│   └── 페이지
└── 장
```

### 읽기 화면

```text
← 목차       책 제목       ☰
────────────────────────────

페이지 제목

페이지 본문

────────────────────────────
이전              다음
```

읽기 중 페이지 변경 및 스크롤 위치를 자동 저장한다.

---

## 5. 사용자별 데이터 분리

BookOasis는 여러 사용자가 로그인하여 사용하는 서비스이므로 플러그인도 멀티유저를 전제로 설계한다.

### 사용자 식별

플러그인은 별도의 사용자 계정 시스템을 만들지 않는다.

BookOasis Core의 로그인 Session에서 현재 사용자를 식별한다.

개념적으로:

```python
from flask import session

user_id = session.get("user_id")
```

실제 구현에서는 BookOasis Core가 사용하는 현재 사용자 식별 패턴을 다시 확인하고 그 규약을 따른다.

### 보안 원칙

클라이언트가 다음과 같이 `user_id`를 전달하더라도 신뢰하지 않는다.

```json
{
  "user_id": 123,
  "book_id": 456
}
```

대신 요청 서버 측에서 현재 로그인 사용자의 Session을 확인하여 사용자 ID를 결정한다.

```text
HTTP 요청
   ↓
BookOasis 로그인 Session
   ↓
session['user_id']
   ↓
Plugin API
   ↓
현재 사용자 데이터만 조회/수정
```

모든 사용자 데이터 조회/수정에는 현재 사용자 식별자가 반드시 적용되어야 한다.

---

## 6. 데이터 모델

BookOasis Core DB와 완전히 분리된 독립 데이터베이스를 사용한다. 플러그인 전용 데이터베이스에는 WikiDocs 데이터와 사용자 독서 데이터를 저장한다. Core DB에는 플러그인 테이블을 생성하지 않는다.

### 공유 데이터

WikiDocs 공개 콘텐츠의 메타데이터와 페이지 구조는 사용자 간 공유 가능하다.

#### `books`

```text
id
wikidocs_book_id
title
author
description
cover_url
page_count
url
synced_at
created_at
```

#### `pages`

```text
id
wikidocs_page_id
book_id
parent_id
title
order
synced_at
```

### 사용자 데이터

사용자의 독서 데이터는 반드시 `user_id`를 포함한다.

#### `user_books`

```text
id
user_id
book_id
added_at
updated_at
```

필요한 경우 책을 사용자의 목록에 추가했는지, 최근 읽은 책인지 등의 정보를 이 관계에서 관리한다.

동일 사용자의 동일 책에 대한 중복 관계를 방지한다.

```text
UNIQUE(user_id, book_id)
```

#### `reading_progress`

BookOasis Core의 화면/기능에서 사용하는 용어를 참고하되, 독서 상태와 데이터는 플러그인 DB에서 독립적으로 관리한다.

```text
id
user_id
book_id
page_id
position
is_completed
last_read_at
completed_at
```

동일 사용자의 동일 책에 대한 현재 독서 위치는 하나만 유지한다.

```text
UNIQUE(user_id, book_id)
```

---

## 7. 독서 상태 및 용어

플러그인이 독자적인 `READING`, `COMPLETED`, `UNREAD` 등의 상태 enum을 만들지 않는다.

BookOasis Core에서 사용하는 개념과 용어를 우선한다.

### 주요 개념

- **진척도**
- **읽음 완료 / 완독**
- **읽지 않음으로 변경**
- **최근 읽은 도서**
- **독서 기록**
- **마지막 읽은 위치**

BookOasis Core의 실제 API/DB/화면에서 사용하는 표현이 확인되면 그 표현을 플러그인의 UI와 문서에도 그대로 반영한다.

### 읽음 완료

책을 읽음 완료로 표시한다.

```text
is_completed = 1
진척도 = 100%
```

단, 실제 Core의 완료 처리 semantics를 개발 단계에서 다시 확인하여 Core와 동일한 의미로 구현한다.

### 읽지 않음으로 변경

사용자가 완료된 책을 다시 처음부터 읽고 싶을 때 읽지 않음 상태로 초기화한다.

기본 기획은 다음과 같다.

```text
is_completed = 0
진척도 = 0%
마지막 읽은 페이지 초기화
페이지 내부 위치 초기화
```

초기화 범위는 플러그인 자체 데이터 모델을 기준으로 결정한다. Core의 독서 상태 API를 호출하거나 조작하지 않는다.

---

## 8. 진척도

기본 진척도는 책의 실제 콘텐츠 페이지 기준으로 계산한다.

예:

```text
전체 콘텐츠 페이지: 80
읽은 콘텐츠 페이지: 42
진척도: 52.5%
```

목차용 노드 등 실제 콘텐츠가 아닌 항목을 진척도 계산에 포함할지는 WikiDocs의 실제 페이지 구조를 조사한 후 확정한다.

최종적으로 사용자에게는 BookOasis Core의 표현과 일관된 방식으로 진척도를 표시한다.

---

## 9. 마지막 읽은 위치

단순히 마지막 페이지뿐 아니라 페이지 내부 위치까지 저장한다.

```text
book_id
page_id
position
```

예:

```json
{
  "book_id": 123,
  "page_id": 456,
  "position": 0.68
}
```

`position`은 페이지 내부 스크롤 위치를 표현하는 값으로 설계한다.

사용자가 다시 책을 열면:

```text
책
 ↓
마지막 페이지
 ↓
마지막 페이지 내부 위치
```

를 복원한다.

---

## 10. 읽음 완료/초기화 UX

책 상세 및 적절한 책 메뉴에서 현재 상태에 따라 다음 액션을 제공한다.

### 미완료 책

```text
[읽음 완료]
```

### 읽음 완료 책

```text
[읽지 않음으로 변경]
```

읽지 않음으로 변경하는 경우 사용자가 다시 처음부터 읽을 수 있도록 진척도 및 읽기 위치를 초기화하는 것을 기본 동작으로 한다.

---

## 11. WikiDocs 연동

WikiDocs 공개 콘텐츠를 외부 데이터 소스로 사용한다.

필수적으로 실제 WikiDocs 동작을 조사하여 다음 계약을 확정한다.

1. 공개 책 검색
2. 책 상세 정보
3. 책 목차/페이지 구조
4. 개별 페이지 본문
5. 필요한 경우 이미지/정적 리소스

### 중요한 제약

현재 확인한 WikiDocs 공식 API 문서의 `GET /napi/books/`는 본인이 작성한 책 목록 용도이므로 공개 책 검색 API라고 가정하지 않는다.

따라서 구현 전에 실제 공개 웹/API 구조를 검증한다.

---

## 12. 캐시 전략

WikiDocs의 공개 데이터는 BookOasis Plugin API가 제공하는 캐시 기능을 활용할 수 있다.

예상 캐시 대상:

```text
검색 결과
책 정보
목차
페이지 본문
```

초기 예상 TTL:

```text
검색 결과: 5~10분
책 정보: 30분
목차: 30분
페이지 본문: 10~30분
```

실제 TTL은 WikiDocs의 응답 특성과 요청 제한을 확인한 뒤 조정한다.

독서 진척도와 마지막 읽은 위치는 캐시하지 않고 영속 저장한다.

---

## 13. 독립 데이터베이스 및 BookOasis Plugin API 활용

독립 플러그인은 BookOasis가 제공하는 플러그인 기능을 우선 사용한다. 단, 영속 데이터는 Core DB가 아닌 플러그인 전용 독립 데이터베이스에 저장한다.

예상 활용 기능:

- `BaseMetadataProvider`
- `category_tab`
- 플러그인 자체 UI
- 캐시 API
- 현재 사용자 Session
- 필요한 Context Menu Hook
- 필요 시 Dashboard Hook

Metadata Provider의 필수 계약(`search()`, `apply()`)은 BookOasis Core의 플러그인 계약에 맞춰 구현한다.

서비스형 UI의 실제 기능은 `category_tab` 및 플러그인 API/서버 라우트를 중심으로 구성한다.

---

## 14. 독립 데이터베이스 원칙

플러그인은 BookOasis Core DB와 데이터베이스 수준에서 분리한다.

```text
BookOasis Core DB
    │
    └── Core 데이터만 관리

WikiDocs Plugin DB
    │
    ├── WikiDocs 책/페이지 캐시 및 메타데이터
    ├── 사용자별 책 목록
    └── 사용자별 독서 진척도/위치/완료 상태
```

### 분리 목적

- Core DB와의 IO 경합 최소화
- WikiDocs 플러그인 DB 장애가 Core DB 장애로 전파되는 것을 방지
- 플러그인 데이터의 독립적인 백업/복구 가능성 확보
- 플러그인 제거 시 WikiDocs 데이터베이스만 별도로 삭제 가능
- Core DB 스키마에 플러그인 의존성을 만들지 않음

### 데이터베이스 위치/형식

초기 구현은 운영 환경에서 별도 파일/DB 인스턴스로 분리 가능한 구조를 사용한다. 구체적인 DB 엔진(SQLite/PostgreSQL 등)과 경로는 BookOasis의 배포 환경 및 운영 요구사항을 조사한 뒤 확정한다. 중요한 것은 **Core DB와 물리적으로 분리된 독립 저장소**라는 원칙이다.

플러그인 DB의 연결/마이그레이션 생명주기도 플러그인이 관리한다. Core DB migration에는 WikiDocs 관련 변경을 추가하지 않는다.

---

## 15. 프로젝트 구조

프로젝트 이름을 프로젝트 루트 디렉터리 이름으로 사용한다.

```text
bookoasis-wikidocs/
│
├── PLAN.md
├── README.md
├── LICENSE
├── VERSION
│
└── plugins/
    └── metadata/
        └── wikidocs_reader/
            ├── __init__.py
            ├── wikidocs_reader.py
            ├── VERSION
            │
            ├── index.html
            ├── style.css
            ├── script.js
            │
            ├── settings.html
            ├── settings.css
            ├── settings.js
            │
            └── data/
```

실제 Plugin ID는 BookOasis의 기존 플러그인 명명 규칙을 확인한 후 확정한다. 프로젝트명은 `bookoasis-wikidocs`로 고정한다.

---

## 16. 개발 원칙

### Core 참조 전용

BookOasis Core는 플러그인 실행에 필요한 참조 정보와 사용자 컨텍스트를 제공하는 대상으로만 사용한다. 플러그인은 Core DB를 직접 조회하지 않으며 Core의 데이터를 변경하지 않는다. Core에 존재하는 용어와 UI 표현은 필요할 경우 참고한다.

특히 다음을 우선 확인한다.

- 사용자 인증/현재 사용자 컨텍스트
- 사용자 ID
- UI 용어
- 플러그인에서 참조해야 하는 기타 Core 제공 정보

### 독립성

BookOasis Core 소스에 기능을 추가하거나 수정하지 않는다.

필요한 기능이 Plugin API로 제공되는지 먼저 확인하고, 부족한 경우 플러그인 내부에서 해결한다.

### Core 데이터 접근 제한

플러그인 코드는 Core 데이터베이스에 직접 연결하거나 조회하지 않는다. Core의 DB Gateway도 사용하지 않는다. 필요한 Core 정보는 Plugin API/실행 컨텍스트를 통해 제공되는 값만 참조한다.

Core의 데이터 조작 API를 호출해 플러그인 독서 상태를 저장하거나 변경하지 않는다. 독서 상태의 생성/조회/수정/삭제는 모두 플러그인 DB에서 처리한다.

### 멀티유저 안전성

사용자 데이터에 대한 모든 서버 측 연산은 현재 로그인 사용자를 기준으로 한다.

다른 사용자의 데이터를 직접 지정할 수 있는 API를 만들지 않는다.

### 외부 콘텐츠

WikiDocs의 공개 콘텐츠만 대상으로 한다. WikiDocs 로그인 정보나 비공개 콘텐츠 접근을 MVP에서 구현하지 않는다.

---

## 17. 개발 전 선행 조사

코딩 전에 다음 사항을 실제로 확인한다.

### BookOasis

- 현재 플러그인 API의 실제 사용 패턴
- `session['user_id']` 접근 방법
- 현재 사용자 식별 helper 존재 여부
- `user_progress` semantics
- `/api/media/progress` 동작
- `/api/media/unread` 동작
- `user_reading_log` 동작
- 진척도/완독 관련 UI 용어
- Plugin DB Gateway의 멀티유저 환경 동작

### WikiDocs

- 공개 책 검색 방식
- 공개 책 상세 페이지 구조
- 목차 데이터 구조
- 페이지 본문 획득 방식
- 이미지/정적 리소스 처리
- 요청 제한/차단 정책
- 공식 API로 처리 가능한 범위

---

## 18. MVP 완료 조건

다음 시나리오가 모두 동작하면 MVP 완료로 본다.

### 사용자 A

1. BookOasis 로그인
2. WikiDocs 메뉴 진입
3. 공개 책 검색
4. 책 선택
5. 목차 확인
6. 책 읽기
7. 페이지/스크롤 위치 자동 저장
8. 플러그인 재접속
9. 이전 위치에서 이어 읽기
10. 책을 읽음 완료로 표시
11. 읽음 완료 상태 확인
12. 읽지 않음으로 변경
13. 진척도와 위치가 초기화됨을 확인

### 사용자 B

동일한 책을 열었을 때 사용자 A의 데이터가 노출되지 않아야 한다.

```text
User A
책 A → 진척도 72% → page 32

User B
책 A → 별도의 독서 상태
```

사용자 A의 읽기 위치, 진척도, 완료 상태가 사용자 B에게 영향을 주어서는 안 된다.

---

## 19. 향후 확장 후보

MVP 이후 필요성이 확인되면 다음 기능을 검토한다.

- WikiDocs 책 즐겨찾기
- 개인 책 목록 정렬/필터
- 독서 통계
- 하이라이트/메모
- 책별 독서 기록
- 검색 고도화
- 페이지 캐시 고도화
- WikiDocs 콘텐츠 변경 감지
- BookOasis Dashboard 위젯

단, 모든 확장은 BookOasis Core의 기존 기능과 중복되지 않는지 먼저 검토한다.

---

## 20. 기획 결정 사항 요약

| 항목 | 결정 |
|---|---|
| 프로젝트명 | `bookoasis-wikidocs` |
| 개발 형태 | 독립 BookOasis Plugin |
| Core 수정 | 하지 않음 |
| 대상 콘텐츠 | WikiDocs 공개 책 |
| 검색 | 구현 |
| 책 상세 | 구현 |
| 목차 | 구현 |
| 온라인 읽기 | 구현 |
| 최근 읽은 책 | 구현 |
| 사용자별 진척도 | 구현 |
| 마지막 읽은 위치 | 구현 |
| 읽음 완료 | 구현 |
| 읽지 않음으로 변경 | 구현 |
| 사용자 인증 | BookOasis Core의 사용자 컨텍스트 참조 |
| 사용자 ID | BookOasis Session의 `user_id` |
| 별도 계정 | 만들지 않음 |
| 공유 데이터 | WikiDocs 책/페이지 메타데이터 |
| 사용자 데이터 | 독서 목록/진척도/위치 등 |
| 사용자 데이터 저장 | Core DB와 물리적으로 분리된 독립 Plugin DB |
| 캐시 | 독립 DB/필요 시 Core Cache 활용 |
| Core 용어 | Core 프로젝트 기준 |
| Core 데이터 모델 | 직접 사용하지 않고 용어/의미만 참고 |
| MVP 외 | 로그인/비공개 책/편집/다운로드 등 |

---

## 8. 실제 BookOasis 통합 결정사항

최종 구현은 BookOasis의 공식 Category-Level Metadata Plugin 계약을 따른다.

### 프로세스 구조

별도 `bookoasis-wikidocs` Flask 서버를 실행하지 않는다. 플러그인은 BookOasis 프로세스 내부에서 동적으로 import된다.

```text
BookOasis :5930
    │
    └── plugins/metadata/wikidocs_reader
          ├── WikidocsReaderMetadataProvider
          ├── Category UI
          └── 독립 SQLite
```

기존에 만들었던 별도 `:5940` Flask 서버, Supervisor `bookoasis-wikidocs` 서비스, `/api/wikidocs/*` Nginx proxy는 폐기했다.

### 플러그인 UI RPC

BookOasis Core는 임의의 플러그인 Blueprint를 자동 등록하지 않는다. 따라서 Core 수정 없이 사용자별 CRUD를 제공하기 위해 공식 `run_context_menu_action` 계약을 RPC transport로 사용한다.

```text
Browser
  ↓ POST /api/media/context-menu/book/plugins/action
Core
  ↓ MetadataFactory.get_provider_by_id()
WikidocsReaderMetadataProvider.run_context_menu_action()
  ↓
Plugin SQLite
```

`action_id`는 `wikidocs_rpc`로 고정하고 실제 작업은 context의 `op`로 구분한다.

- `search`
- `books`
- `add`
- `detail`
- `page`
- `progress`
- `complete`
- `reset`

### 사용자 식별

RPC context에 `user_id`를 전달하지 않는다. 플러그인 서버 코드는 Core Flask Session에서 현재 `user_id`를 읽는다.

### 데이터베이스

플러그인 전용 SQLite만 사용한다.

- Core DB 접근 금지
- Core DB 테이블 생성 금지
- 사용자별 데이터는 `user_id`를 포함하여 격리

### 외부 의존성

플러그인 `requirements.txt`에는 WikiDocs 접근에 필요한 `beautifulsoup4`, `curl-cffi`만 둔다. Flask는 BookOasis Core가 제공하므로 플러그인 전용 `libs/`에 별도 설치하지 않는다.

### 현재 검증

- WikiDocs 실검색: `파이썬` 검색 시 20개 공개책 결과 확인
- 플러그인 단위 테스트: 8 passed
- Plugin provider import/contract 확인
- Nginx `:2999` → Core `:5930` 정상
- 별도 WikiDocs `:5940` 프로세스 제거
- Supervisor에서 별도 WikiDocs 서비스 제거
- Core DB 직접 접근 코드 없음

## 14. 메인 페이지 WikiDocs 도서 위젯

BookOasis 메인(Home) 페이지의 기존 Dashboard Plugin Widget 영역에 **WikiDocs 내 책 목록**을 표시한다.

### 동작

- 기존 BookOasis Dashboard Widget contract(`dashboard_widget` + `get_dashboard_data`)를 사용한다.
- 별도 프로세스/별도 API 서버를 생성하지 않는다.
- 로그인한 현재 사용자의 `user_id`만 기준으로 플러그인 독립 DB의 `user_books`/독서 진척 데이터를 조회한다.
- 다른 사용자의 WikiDocs 도서 목록은 절대 노출하지 않는다.
- 각 카드에는 책 제목, 저자, 표지(가능한 경우), 진척도, 마지막 읽은 정보와 WikiDocs 링크를 표시한다.
- 목록이 비어 있으면 위젯은 비어 있는 상태를 자연스럽게 표시한다.
- 기존 Core Dashboard의 공통 카드 렌더러와 스타일을 사용하여 메인 페이지와 시각적으로 일관되게 한다.
- `all_desk_tab`을 사용하지 않아 메인 Dashboard의 일반 위젯 카드 영역에 표시한다.

### 데이터 원칙

WikiDocs 공개 콘텐츠 메타데이터는 플러그인 DB에 저장하며, 사용자별 목록/진척도는 `user_id`로 격리한다. Core DB는 조회하지 않는다.

## 15. WikiDocs 메인 페이지 공개 도서 목록

WikiDocs 플러그인 메인 페이지에 **현재 WikiDocs에 공개되어 있는 책 목록**을 표시한다.

### 요구사항

- 사용자의 개인 독서 목록과 별개로 표시한다.
- WikiDocs 공개 책 목록을 검색 없이 바로 확인할 수 있어야 한다.
- 책 제목, 저자, 표지(가능한 경우), WikiDocs 책 ID를 표시한다.
- 책을 선택하면 기존 책 상세/추가 흐름으로 연결한다.
- 목록 데이터는 공개 콘텐츠이므로 사용자별 데이터와 섞지 않는다.
- WikiDocs 서버에 대한 반복 요청을 줄이기 위해 기존 공개 콘텐츠 캐시 정책을 적용한다.
- 목록 조회 실패 시 기존 검색/내 책 기능을 사용할 수 있도록 graceful degradation한다.
- Core DB에는 저장하지 않는다.

### 표시 정책

- 기본 표시 개수는 20권으로 한다.
- 공개 도서 목록에 이전/다음 페이지네이션을 제공한다.
- 현재 페이지 번호를 표시하고, 이전/다음 버튼의 활성 상태를 실제 응답으로 판단한다.
- 최신/현재 공개 목록을 우선하되 WikiDocs의 실제 목록 API/HTML 구조에 맞춰 구현한다.
- 캐시 TTL은 기존 공개 콘텐츠 목록 정책을 따르며, 현재 기본값은 10분이다.

### 공개 도서 → 내 책 연계

- 공개 도서 카드에서 로그인 사용자는 `내 책에 추가`로 즉시 독서 목록에 추가할 수 있다.
- 추가 직후 BookOasis 내부 reader로 진입한다.
- 이미 내 책에 있는 공개 도서는 `이어 읽기`를 제공한다.
- `WikiDocs에서 보기`는 외부 원문 확인용 보조 링크로 유지한다.
- 독서 위치/스크롤/진행률/완독 상태는 기존 `ReadingService`를 통해 관리한다.
