# BookOasis WikiDocs

BookOasis에서 WikiDocs의 공개 문서를 도서 형태로 조회하고 읽을 수 있도록 제공하는 메타데이터 플러그인입니다.

## 목적

이 플러그인의 목적은 WikiDocs에 공개된 문서를 BookOasis의 도서 목록과 독서 화면에서 자연스럽게 이용할 수 있도록 연결하는 것입니다.

WikiDocs의 문서 구조를 BookOasis의 도서·페이지 모델에 맞춰 제공하고, 사용자가 공개 문서를 검색하고 선택하여 페이지 단위로 읽을 수 있도록 합니다.

플러그인은 BookOasis Stable의 메타데이터 플러그인 계약을 따르며, 플러그인 자체 데이터는 Core가 제공하는 DB Gateway를 사용합니다.

## 주요 기능

- WikiDocs 공개 문서 목록 조회
- 공개 문서 검색
- WikiDocs 문서를 BookOasis 도서 형태로 제공
- 문서의 목차와 페이지 탐색
- 도서 본문 HTML 표시
- 이전/다음 페이지 탐색
- 데스크톱 키보드 탐색
  - `←`: 이전 페이지
  - `→`: 다음 페이지
  - `↑` / `↓`: 본문 스크롤
  - `Page Up` / `Page Down`: 한 화면 단위 본문 스크롤
- 독서 진행 상태 및 페이지 위치를 BookOasis Core와 연동
- WikiDocs 데이터 캐시 및 동기화
- 공개 문서 목록 정렬 기준 선택
  - 최신
  - 추천
  - 인기
- 플러그인 업데이트 manifest 제공

## 동작 범위

WikiDocs의 원본 콘텐츠를 BookOasis에서 읽기 위한 연결 계층을 담당합니다. 인증이 필요한 비공개 문서나 WikiDocs 자체의 편집 기능은 이 플러그인의 목적에 포함하지 않습니다.

## BookOasis 연동

이 저장소는 독립적으로 배포되는 BookOasis metadata plugin입니다. 저장소 루트가 플러그인의 루트이며, BookOasis Stable에 설치될 때 다음 위치에서 동작합니다.

```text
plugins/metadata/wikidocs_reader/
```

플러그인 저장소에는 런타임 데이터베이스를 포함하지 않으며, 독서 진행 상태와 캐시 등의 영속 데이터는 BookOasis Core가 제공하는 저장소 계층을 통해 관리합니다.
