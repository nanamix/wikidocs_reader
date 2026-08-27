# bookoasis-wikidocs

BookOasis `plugins/metadata/wikidocs_reader`용 독립 플러그인 프로젝트입니다.

WikiDocs의 공개 책을 BookOasis 안에서 검색하고, 사용자별 서재/독서 위치/완독 상태를 별도 SQLite DB에 저장합니다.

## 구조

- `plugins/metadata/wikidocs_reader/` — 실제 BookOasis 플러그인
- `application/` — 유스케이스
- `domain/` — 도메인 모델/포트
- `infrastructure/` — 플러그인 전용 SQLite/캐시/Repository
- `wikidocs/` — WikiDocs HTTP/HTML adapter
- `presentation/context.py` — BookOasis Session의 현재 사용자 ID를 읽는 얇은 adapter
- `index.html`, `style.css`, `script.js` — Category-Level Plugin UI

## BookOasis 통합 방식

별도 Flask 서버나 별도 프로세스를 만들지 않습니다.

BookOasis가 `plugins/metadata/wikidocs_reader`를 프로세스 내부에서 동적으로 로드하고 `category_tab`으로 WikiDocs 메뉴를 제공합니다.

플러그인 UI의 읽기/쓰기 RPC는 Core가 제공하는 표준 `run_context_menu_action` 계약을 사용합니다. Core 코드나 Core DB를 수정하지 않습니다.

UI → Core 공통 Plugin Action Endpoint → `WikidocsReaderMetadataProvider.run_context_menu_action()` → 플러그인 전용 SQLite

## 데이터 격리

- Core DB 테이블을 생성하지 않습니다.
- Core DB를 직접 조회하지 않습니다.
- 사용자 ID는 클라이언트 입력을 사용하지 않고 Core 로그인 Session에서 가져옵니다.
- 독서 데이터는 `plugins/metadata/wikidocs_reader/data/wikidocs.sqlite3`에 저장됩니다.
- 플러그인 삭제 시 이 DB도 함께 삭제할 수 있습니다.

## 기능

- WikiDocs 공개 책 검색
- 책 추가 및 사용자별 책 목록
- 목차/페이지 조회
- 마지막 페이지 저장
- 페이지 내부 스크롤 위치 저장
- 사용자별 진척도
- 완독/미완독 초기화
- 이어 읽기
- 검색 결과 캐시(TTL + 크기 제한)

## 개발/테스트

프로젝트 자체 테스트는 `.venv/bin/pytest -q tests`로 실행합니다.
실제 BookOasis에 설치된 플러그인은 `/shared/bookoasis_stable/plugins/metadata/wikidocs_reader`입니다.
