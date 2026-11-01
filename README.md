# BookOasis WikiDocs Reader

BookOasis에서 [WikiDocs](https://wikidocs.net)의 공개 문서를 도서 형태로 조회하고 읽을 수 있도록 연결하는 **metadata plugin**입니다.

저장소 자체가 플러그인의 루트이며, BookOasis Stable의 metadata provider 계약에 맞춰 동작합니다.

## 목적

WikiDocs의 공개 문서를 BookOasis의 도서/페이지 모델로 변환하여 다음과 같은 독서 경험을 제공합니다.

- 공개 문서 목록에서 책을 선택
- 책의 목차를 확인하고 페이지 단위로 이동
- WikiDocs 원문을 안전하게 정제하여 본문 표시
- 이전/다음 페이지와 키보드로 연속해서 읽기
- 독서 진행 상태와 본문 스크롤 위치를 BookOasis Core와 연동

이 플러그인은 **공개 문서 읽기와 BookOasis 연동**을 담당합니다. WikiDocs의 문서 작성·편집 기능이나 인증이 필요한 비공개 문서를 제공하는 것이 목적은 아닙니다.

## 주요 기능

### 공개 도서 목록

- WikiDocs 공개 문서 목록 조회
- 공개 문서 검색
- 정렬 기준 선택
  - 최신
  - 추천
  - 인기
- 정렬 기준은 **서버에 저장하지 않고 브라우저에만 보관**합니다.
- 목록의 제목을 더블클릭하여 정렬 선택 UI를 표시/숨길 수 있습니다.

### 도서 읽기

- WikiDocs 책 정보 및 목차 조회
- 페이지 본문 HTML 표시
- 이전/다음 페이지 이동
- 현재 페이지와 독서 진행 상태 관리
- 페이지별 본문 스크롤 위치 기억
- 모달을 닫았다 다시 열거나 이전/다음 페이지로 이동해도 페이지별 스크롤 위치를 복원
- 자동 스크롤 지원

### 데스크톱 키보드 조작

모달 독서 화면에서 다음 키를 사용할 수 있습니다.

| 키 | 동작 |
|---|---|
| `←` | 이전 페이지 |
| `→` | 다음 페이지 |
| `↑` | 본문을 위로 스크롤 |
| `↓` | 본문을 아래로 스크롤 |
| `Page Up` | 한 화면 위로 스크롤 |
| `Page Down` | 한 화면 아래로 스크롤 |
| `Home` | 본문 최상단으로 이동 |
| `End` | 본문 최하단으로 이동 |

입력창·셀렉트 등 폼 컨트롤에 포커스가 있는 경우에는 독서 화면의 키보드 단축키가 입력을 방해하지 않습니다.

### 브라우저 로그 진단

일반 화면에서는 진단용 버튼을 노출하지 않습니다. WikiDocs 관련 제목을 더블클릭하면 브라우저 로그를 서버로 전송하는 진단 기능을 표시할 수 있습니다.

## 데이터 및 저장소

플러그인은 BookOasis Core가 제공하는 저장소 계층을 사용합니다.

- 플러그인 저장소에 사용자 독서 데이터베이스를 포함하지 않습니다.
- 독서 진행 상태 및 스크롤 위치는 Core의 DB Gateway를 통해 관리합니다.
- WikiDocs 원격 데이터는 캐시 정책에 따라 캐시됩니다.
- 공개 도서 목록의 정렬 선택은 사용자 브라우저에만 저장하며 서버에는 저장하지 않습니다.

## 원격 데이터 처리

WikiDocs 공개 페이지는 `curl_cffi`를 이용해 가져오며, 공개 페이지에서 필요한 도서·목차·본문 정보를 추출합니다.

본문 HTML은 브라우저에 전달하기 전에 허용된 태그와 속성만 남기는 방식으로 정제합니다. 스크립트, 이벤트 핸들러, 인라인 스타일 및 허용하지 않은 URL 등의 실행 가능한 콘텐츠는 제거합니다.

## BookOasis Stable 설치

Git 저장소 이름과 BookOasis의 plugin ID는 별개의 개념입니다.

- GitHub repository: `nanamix/wikidocs_reader`
- plugin ID: `wikidocs_reader`
- Python provider module: `wikidocs_reader.py`

BookOasis Stable은 **plugin ID를 기준으로 metadata plugin을 발견하고 설치**합니다. 따라서 Stable에서의 플러그인 경로는 다음과 같습니다.

```text
plugins/metadata/wikidocs_reader/
```

저장소 자체는 이미 이 디렉터리의 내용이므로 저장소 안에 다시 `plugins/metadata/wikidocs_reader/`를 중첩하지 않습니다.

## 저장소 구조

```text
wikidocs_reader/
├── wikidocs_reader.py   # metadata provider 및 도메인/서비스 구현
├── __init__.py
├── index.html           # 플러그인 UI
├── script.js            # UI 및 독서 동작
├── style.css
├── requirements.txt
├── pyproject.toml
├── VERSION
└── tests/               # 자동화 테스트
```

## 개발 및 테스트

Python 의존성은 `requirements.txt`를 기준으로 관리하며, 개발 환경에서는 `uv`를 사용할 수 있습니다.

전체 Python 테스트:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/shared/wikidocs_reader:/shared/bookoasis_stable \
.venv/bin/python -m pytest -q
```

JavaScript 문법 검사:

```bash
node --check script.js
```

변경사항 검사:

```bash
git diff --check
```

`tests/conftest.py`는 저장소 루트의 `wikidocs_reader.py`와 저장소 디렉터리 이름이 같은 환경에서 발생할 수 있는 Python import 이름 충돌을 방지하고, 테스트가 실제 provider 모듈을 대상으로 실행되도록 합니다.

## 업데이트

플러그인은 BookOasis Stable의 metadata plugin 업데이트 메커니즘을 통해 갱신됩니다. 업데이트 시 Stable은 plugin ID와 manifest 정보를 기준으로 플러그인 파일을 가져옵니다.

현재 GitHub 원격 저장소:

```text
https://github.com/nanamix/wikidocs_reader
```

## 범위

이 프로젝트가 책임지는 범위는 다음과 같습니다.

1. WikiDocs 공개 콘텐츠 수집
2. BookOasis metadata 모델로 변환
3. 공개 도서 목록과 검색/정렬 UI 제공
4. 페이지 기반 독서 UI 제공
5. 독서 진행 및 스크롤 위치를 Core와 연동
6. 원격 HTML 콘텐츠의 안전한 정제

BookOasis Core의 인증·사용자 관리·영속 저장소 자체를 대체하지 않으며, WikiDocs의 콘텐츠를 직접 수정하지 않습니다.
