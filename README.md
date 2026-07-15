# LocalHub Backend

서울 관광정보, 커뮤니티 게시판, 통계, AI 지역 안내 챗봇을 제공하는 FastAPI 백엔드입니다. 로컬과 Render 배포 환경 모두 SQLite를 사용합니다.

전체 요청·응답 계약은 [API_DOCS.md](./API_DOCS.md)를 확인하세요.

## 주요 기능

- 서울 지역정보 목록, 검색, 필터, 상세 조회
- 게시글 등록, 조회, 수정, 삭제
- 게시글별 비밀번호 검증과 PBKDF2-SHA256 해시 저장
- 지역정보·게시글 카테고리 통계
- 질문 핵심어 기반 관련 자료 검색과 OpenAI 챗봇 응답
- 한국관광공사 데이터 출처·라이선스 정보
- Vue/Vite 개발 및 배포 Origin을 위한 CORS 설정
- Render Blueprint 기반 Web Service·SQLite 영속 디스크 배포

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| API | FastAPI |
| ORM | SQLAlchemy 2 |
| 요청 검증 | Pydantic 2 |
| 로컬 DB | SQLite |
| DB | SQLite |
| AI | OpenAI Responses API |
| 서버 | Uvicorn |
| 테스트 | pytest, FastAPI TestClient |
| 배포 | Render Blueprint |

## 프로젝트 구조

```text
LocalHub_BE/
├─ app/
│  ├─ main.py          # FastAPI 앱, 라우트, CORS, 예외 처리, 챗봇 검색
│  ├─ database.py      # SQLite 연결과 DB 세션
│  ├─ models.py        # Location, Post SQLAlchemy 모델
│  ├─ schemas.py       # 요청 Body 검증 모델
│  ├─ responses.py     # 공통 성공·실패·페이지 응답
│  ├─ security.py      # 게시글 비밀번호 해시·검증
│  └─ seed.py          # 서울 관광 JSON 초기 적재
├─ data/서울/          # 한국관광공사 TourAPI 기반 JSON 데이터
├─ tests/              # API, CORS, 챗봇 검색 테스트
├─ .env.example        # 로컬 환경변수 예시
├─ API_DOCS.md         # 프론트엔드용 상세 API 명세
├─ render.yaml         # Render Web Service·SQLite 영속 디스크 Blueprint
├─ requirements.txt
└─ run.py              # 로컬 실행 진입점
```

## 데이터 모델

```text
Location 1 ─── 0..N Post
```

### Location

한국관광공사 원본 콘텐츠 ID, 카테고리, 장소명, 주소, 좌표, 이미지, 연락처, 원본 생성·수정 시각을 저장합니다.

### Post

카테고리, 제목, 본문, 비밀번호 해시, 선택적인 지역정보 연결, 생성·수정 시각을 저장합니다. 사용자 계정 인증은 없으며 게시글마다 입력한 비밀번호로 수정·삭제합니다.

## 최초 실행과 데이터 적재

애플리케이션 시작 시 다음 작업을 수행합니다.

1. SQLAlchemy `create_all()`로 없는 테이블을 생성합니다.
2. `locations` 테이블이 비어 있으면 `data/서울/*.json`을 읽습니다.
3. 모든 지역정보를 하나의 트랜잭션으로 적재합니다.

현재 저장소에는 7개 카테고리, 총 6,518건의 원본 데이터가 있습니다.

| contentTypeId | 카테고리 | 건수 |
| --- | --- | ---: |
| 12 | 관광지 | 783 |
| 14 | 문화시설 | 566 |
| 15 | 축제공연행사 | 201 |
| 25 | 여행코스 | 51 |
| 28 | 레포츠 | 126 |
| 32 | 숙박 | 423 |
| 38 | 쇼핑 | 4,368 |

지역정보가 한 건이라도 존재하면 전체 seed를 건너뛰므로 원본 파일을 추가한 뒤 기존 DB에 자동으로 증분 반영되지는 않습니다.

## 로컬 개발

### 1. 가상환경과 의존성

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경변수

```powershell
Copy-Item .env.example .env
```

```env
DATABASE_URL=sqlite:///./localhub.db
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
APP_ENV=development
```

| 변수 | 필수 | 기본값 | 설명 |
| --- | ---: | --- | --- |
| `DATABASE_URL` | X | `sqlite:///./localhub.db` | SQLAlchemy DB URL |
| `ALLOWED_ORIGINS` | X | 로컬 Vite 주소 2개 | 쉼표로 구분한 허용 Origin |
| `OPENAI_API_KEY` | 챗봇 사용 시 O | 없음 | OpenAI API 키 |
| `OPENAI_MODEL` | X | `gpt-5-mini` | 챗봇 응답 모델 |
| `APP_ENV` | X | `development` | `development`일 때 `run.py` reload 활성화 |
| `PORT` | X | `8000` | `run.py` 서버 포트 |

`.env`는 앱 시작 시 자동으로 읽고 Git에서 제외합니다. 실제 API 키를 `.env.example`이나 소스 코드에 저장하지 마세요.

### 3. 실행

```powershell
python run.py
```

또는 Render와 같은 방식으로 실행할 수 있습니다.

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

접속 주소:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

## API 구성

| 영역 | 엔드포인트 |
| --- | --- |
| 상태 | `GET /health` |
| 지역정보 | `GET /api/v1/locations`, `GET /api/v1/locations/{locationId}` |
| 카테고리 | `GET /api/v1/locations/categories` |
| 게시글 | `GET·POST /api/v1/posts`, `GET·PUT·DELETE /api/v1/posts/{postId}` |
| 비밀번호 | `POST /api/v1/posts/{postId}/verify-password` |
| 통계 | `GET /api/v1/statistics/locations/categories`, `GET /api/v1/statistics/posts/categories` |
| 데이터 출처 | `GET /api/v1/data-source` |
| 챗봇 | `POST /api/v1/chat` |

일반 성공 응답:

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

일반 실패 응답:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "오류 메시지",
    "details": null
  }
}
```

`DELETE /api/v1/posts/{postId}` 성공 응답은 `204 No Content`이며 `/health`는 별도 응답 형식을 사용합니다.

## 챗봇 동작

```text
사용자 message
  → 핵심어 추출·조사와 요청 표현 제거
  → Location과 Post에서 부분 일치 후보 검색
  → 제목·카테고리·주소·본문 일치 가중치로 정렬
  → 상위 장소 10개 + 게시글 10개를 참고자료로 구성
  → OpenAI Responses API 호출
  → answer + references 반환
```

- 대화 `history`는 DB에 저장하지 않습니다.
- Vue가 최근 대화를 최대 20개까지 요청에 포함해야 합니다.
- `history`는 모델 문맥에만 사용하고 DB 검색은 현재 `message`를 기준으로 합니다.
- API 키가 없거나 OpenAI 호출이 실패하면 `502 CHAT_PROVIDER_ERROR`입니다.
- 검색 결과가 없어도 OpenAI를 호출하고, 모델은 참고자료가 없다고 안내하도록 지시받습니다.
- 답변은 Markdown이 아닌 일반 텍스트이며, 서버가 과도한 빈 줄과 줄 끝 공백을 정리합니다.
- Vue의 답변 요소에는 `white-space: pre-line`을 적용해야 줄바꿈이 화면에 반영됩니다.
- `강남갈만한 곳 추천좀`처럼 자주 쓰는 요청 표현을 붙여 입력해도 핵심어 `강남`을 분리해 검색합니다.
- 정확 검색 결과가 없으면 한글 자모 유사도 기반 검색을 수행해 `강낭`처럼 가까운 오타도 관련 후보와 연결합니다.

## CORS와 Vue 연결

기본적으로 다음 개발 Origin을 허용합니다.

```text
http://localhost:5173
http://127.0.0.1:5173
```

배포 환경에서는 `ALLOWED_ORIGINS`에 Vue 사이트의 정확한 Origin을 설정합니다.

```env
ALLOWED_ORIGINS=https://localhub-web.onrender.com,https://www.example.com
```

주의사항:

- Origin 끝에 `/`를 붙이지 않습니다.
- 여러 주소는 쉼표로 구분합니다.
- `*` 와일드카드는 사용하지 않습니다.
- 현재 쿠키 기반 인증을 사용하지 않아 CORS credential은 비활성화되어 있습니다.
- 허용 Method는 `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`입니다.
- 허용 Header는 `Content-Type`, `Authorization`입니다.

Axios 예시:

```js
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
})
```

DELETE 요청은 비밀번호를 Axios의 `data` 옵션에 담습니다.

```js
await api.delete(`/api/v1/posts/${postId}`, {
  data: { password }
})
```

## 테스트

```powershell
python -m pytest -q
```

현재 테스트 범위:

- 서버와 DB health check
- 지역정보 카테고리·검색
- 게시글 등록·비밀번호 검증·수정·삭제
- 공통 검증 및 오류 응답
- Vue 개발 Origin CORS preflight
- 미허용 Origin 차단
- 챗봇 핵심어 정규화, OR 검색, 관련도 정렬

## Render 배포

저장소 루트의 `render.yaml`은 다음 리소스를 정의합니다.

- `localhub-api`: Python Web Service
- `localhub-sqlite-data`: `/var/data`에 마운트되는 1GB 영속 디스크
- 빌드: `pip install -r requirements.txt`
- 시작: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- DB 파일: `/var/data/localhub.db`

### 배포 순서

1. 저장소를 GitHub에 push합니다.
2. Render Dashboard에서 **New > Blueprint**를 선택합니다.
3. 저장소를 연결하고 `render.yaml`을 적용합니다.
4. Blueprint 생성 과정에서 비밀 환경변수를 입력합니다.
5. 첫 배포가 끝나면 `/health`와 `/docs`를 확인합니다.

필수 배포 환경변수:

| 변수 | Render 설정값 |
| --- | --- |
| `ALLOWED_ORIGINS` | 실제 Vue 배포 Origin, 예: `https://localhub-web.onrender.com` |
| `OPENAI_API_KEY` | 실제 OpenAI API 키 |

`DATABASE_URL=sqlite:////var/data/localhub.db`, `APP_ENV`, `OPENAI_MODEL`은 Blueprint가 설정합니다.

### Render의 SQLite 영속성

Render Web Service의 기본 파일시스템에 SQLite 파일을 두면 재배포나 인스턴스 교체 후 데이터가 사라질 수 있습니다. 따라서 Blueprint는 `/var/data` 영속 디스크를 마운트하고 SQLite DB를 `sqlite:////var/data/localhub.db`에 저장합니다. Uvicorn worker도 하나만 실행하여 여러 프로세스가 같은 SQLite 파일에 동시에 쓰는 구성을 피합니다.

### Render 플랜 주의사항

Render의 영속 디스크는 무료 Web Service에서 사용할 수 없으므로 `render.yaml`은 `starter` 플랜을 지정합니다. 비용 없이 `free` 플랜으로 바꾸면 영속 디스크를 제거해야 하며, 이 경우 SQLite 게시글 데이터는 재배포·재시작 과정에서 유실될 수 있습니다. SQLite 요구사항과 데이터 보존을 모두 만족하려면 현재 영속 디스크 구성을 유지해야 합니다.

### 배포 직후 확인

```text
GET https://<backend-domain>/health
→ status: ok
→ database: connected

GET https://<backend-domain>/api/v1/locations/categories
→ 7개 카테고리
→ 데이터 합계 6518

OPTIONS https://<backend-domain>/api/v1/locations
Origin: <Vue 배포 Origin>
→ Access-Control-Allow-Origin 응답 확인

POST https://<backend-domain>/api/v1/chat
→ OpenAI 키가 유효하면 200
```

## 운영상 알아둘 점

- 이 프로젝트는 Alembic migration을 사용하지 않고 `create_all()`만 사용합니다. 모델 변경이 발생하는 운영 서비스에서는 Alembic 도입이 필요합니다.
- 사용자 인증과 권한 시스템이 없습니다. 게시글 비밀번호를 아는 사용자는 해당 글을 수정·삭제할 수 있습니다.
- 애플리케이션 단위 요청 횟수 제한은 없습니다. 챗봇의 `429`는 OpenAI SDK의 rate limit 오류를 변환한 것입니다.
- 챗봇은 스트리밍 응답을 제공하지 않습니다.
- 예외 상세 내용은 클라이언트에 노출하지 않고 서버 로그에 기록합니다.
- API 요청·응답 예시와 모든 필드 계약은 [API_DOCS.md](./API_DOCS.md)를 기준으로 합니다.

## 배포 전 체크리스트

- [ ] 전체 테스트 통과
- [ ] 실제 비밀값이 Git에 포함되지 않음
- [ ] Render 영속 디스크가 `/var/data`에 마운트됨
- [ ] SQLite DB 경로가 `/var/data/localhub.db`인지 확인
- [ ] `/health`가 `200`과 `database: connected` 반환
- [ ] 최초 지역정보 6,518건 적재 확인
- [ ] `ALLOWED_ORIGINS`에 Vue 배포 Origin 설정
- [ ] `OPENAI_API_KEY` 설정 후 챗봇 호출 확인
- [ ] Vue의 `VITE_API_BASE_URL`을 백엔드 Render URL로 설정
- [ ] 게시글 작성·수정·삭제 브라우저 통합 테스트
- [ ] 장기 운영 시 유료 DB와 백업 정책 검토

## 데이터 출처

- 제공기관: 한국관광공사
- 데이터셋: 국문 관광정보 서비스 (TourAPI 4.0)
- 지역: 서울
- 라이선스: 공공누리 제3유형
- 원본 안내: <https://www.data.go.kr/data/15101578/openapi.do>

서비스 화면에서 출처 표시가 필요하며, 상세 고정 정보는 `GET /api/v1/data-source`로 조회할 수 있습니다.
