# LocalHub API 명세서

이 문서는 현재 `app/main.py`, `app/schemas.py`, `app/responses.py`에 실제 구현된 동작을 기준으로 작성했다.

응답 예시의 장소·게시글 내용과 ID는 데이터 구조를 보여주기 위한 예시다. 카테고리 목록, 고정 문구, 검증 범위, 상태 코드처럼 계약으로 명시한 값은 실제 구현값이다.

## 1. 기본 정보

| 항목 | 값 |
| --- | --- |
| 로컬 Base URL | `http://localhost:8000` |
| API prefix | `/api/v1` |
| 요청·응답 형식 | JSON (`application/json`) |
| 인증 | 없음 |
| Swagger UI | `http://localhost:8000/docs` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

서버 실행:

```powershell
python run.py
```

허용 Origin은 `ALLOWED_ORIGINS` 환경변수에 쉼표로 구분해 설정한다. 기본값은 Vue/Vite 로컬 개발 주소인 `http://localhost:5173,http://127.0.0.1:5173`이다. Render에서는 실제 Vue 배포 Origin을 반드시 지정해야 한다.

## 2. 공통 응답과 규칙

### 2.1 성공 응답

`204 No Content`인 삭제 API와 `/health`를 제외한 성공 응답은 다음 구조다.

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

- `data`는 API에 따라 객체 또는 배열이다.
- `message`는 등록·수정처럼 안내 문구가 있는 API에서 문자열이며, 그 외에는 `null`이다.

### 2.2 실패 응답

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

### 2.3 요청 검증 실패

Pydantic 또는 FastAPI 검증 실패 시 `422 Unprocessable Entity`를 반환한다.

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 값이 올바르지 않습니다.",
    "details": [
      {
        "field": "title",
        "reason": "String should have at least 2 characters"
      }
    ]
  }
}
```

`reason`은 설치된 Pydantic 버전이 생성하는 문자열이므로 프론트엔드에서 문구 자체를 고정값으로 비교하지 않는 것이 좋다.

### 2.4 페이지네이션

```json
{
  "page": 1,
  "size": 20,
  "totalElements": 6518,
  "totalPages": 326,
  "hasPrevious": false,
  "hasNext": true
}
```

- `page`는 1부터 시작한다.
- 결과가 없으면 `totalPages`는 `0`이다.
- 목록 조회 결과가 없어도 오류가 아닌 `200 OK`를 반환한다.

### 2.5 날짜와 Nullable 필드

- 날짜는 타임존 정보가 없는 ISO 8601 문자열이다. 예: `2026-07-15T13:20:00.123456`
- 데이터가 없는 선택 필드는 JSON `null`로 반환될 수 있다.
- 서버가 현재 페이지의 모든 응답에 `Content-Type: application/json`을 명시하지만, 삭제 성공 응답에는 본문이 없다.

## 3. 전체 엔드포인트

| Method | 경로 | 설명 |
| --- | --- | --- |
| GET | `/health` | 서버·DB 상태 확인 |
| GET | `/api/v1/locations/categories` | 지역정보 카테고리 목록 |
| GET | `/api/v1/locations` | 지역정보 목록·검색 |
| GET | `/api/v1/locations/{locationId}` | 지역정보 상세 |
| GET | `/api/v1/posts` | 게시글 목록·검색 |
| POST | `/api/v1/posts` | 게시글 등록 |
| GET | `/api/v1/posts/{postId}` | 게시글 상세 |
| POST | `/api/v1/posts/{postId}/verify-password` | 게시글 비밀번호 확인 |
| PUT | `/api/v1/posts/{postId}` | 게시글 전체 수정 |
| DELETE | `/api/v1/posts/{postId}` | 게시글 삭제 |
| GET | `/api/v1/statistics/locations/categories` | 지역정보 카테고리 통계 |
| GET | `/api/v1/statistics/posts/categories` | 게시글 카테고리 통계 |
| GET | `/api/v1/data-source` | 데이터 출처·라이선스 |
| POST | `/api/v1/chat` | 챗봇 질의 |

## 4. 지역정보 API

### 4.1 카테고리 목록

```http
GET /api/v1/locations/categories
```

지원 카테고리는 아래 8개이며, `count`는 현재 DB 건수다.

| contentTypeId | name |
| --- | --- |
| `12` | `관광지` |
| `14` | `문화시설` |
| `15` | `축제공연행사` |
| `25` | `여행코스` |
| `28` | `레포츠` |
| `32` | `숙박` |
| `38` | `쇼핑` |
| `39` | `음식점` |

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": [
    { "contentTypeId": "12", "name": "관광지", "count": 783 },
    { "contentTypeId": "39", "name": "음식점", "count": 0 }
  ],
  "message": null
}
```

응답 배열에는 항상 8개 카테고리가 모두 포함된다. DB에 데이터가 없는 카테고리의 `count`는 `0`이다.

### 4.2 지역정보 목록·검색

```http
GET /api/v1/locations
```

Query Parameters:

| 이름 | 타입 | 필수 | 기본값 | 검증·동작 |
| --- | --- | ---: | --- | --- |
| `page` | integer | X | `1` | `1` 이상 |
| `size` | integer | X | `20` | `1`~`100` |
| `category` | string | X | 없음 | 위 8개 카테고리명 중 하나 |
| `keyword` | string | X | 없음 | 최대 100자, 제목 또는 주소 부분 일치 |
| `sigunguCode` | string | X | 없음 | 정확히 일치 |
| `hasImage` | boolean | X | 없음 | `true`: `imageUrl` 있음, `false`: 없음 |
| `sort` | string | X | `title` | `title`, `title_desc`, `latest` |

정렬:

- `title`: 제목 오름차순
- `title_desc`: 제목 내림차순
- `latest`: 원본 데이터의 `sourceModifiedAt` 내림차순

필터를 여러 개 전달하면 모두 만족하는 데이터만 조회한다. `keyword`는 문장 분석 없이 전달값 전체를 SQL 부분 일치 검색에 사용한다.

```http
GET /api/v1/locations?page=1&size=20&category=관광지&keyword=서울&hasImage=true&sort=title
```

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "contentId": "126508",
        "contentTypeId": "12",
        "categoryName": "관광지",
        "title": "경복궁",
        "address": "서울특별시 종로구 사직로 161",
        "longitude": 126.976993,
        "latitude": 37.578822,
        "thumbnailUrl": "https://example.com/thumbnail.jpg"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "totalElements": 1,
      "totalPages": 1,
      "hasPrevious": false,
      "hasNext": false
    }
  },
  "message": null
}
```

지원하지 않는 카테고리 `400 Bad Request`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_LOCATION_CATEGORY",
    "message": "지원하지 않는 지역정보 카테고리입니다.",
    "details": { "category": "카페" }
  }
}
```

### 4.3 지역정보 상세

```http
GET /api/v1/locations/{locationId}
```

`locationId`는 정수형 DB ID다.

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "contentId": "126508",
    "contentTypeId": "12",
    "categoryName": "관광지",
    "title": "경복궁",
    "address": "서울특별시 종로구 사직로 161",
    "longitude": 126.976993,
    "latitude": 37.578822,
    "thumbnailUrl": "https://example.com/thumbnail.jpg",
    "addressDetail": null,
    "zipcode": "03045",
    "telephone": "02-3700-3900",
    "sigunguCode": "23",
    "imageUrl": "https://example.com/image.jpg",
    "copyrightCode": "Type3",
    "sourceCreatedAt": "20020404000000",
    "sourceModifiedAt": "20250618095520"
  },
  "message": null
}
```

없는 ID `404 Not Found`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LOCATION_NOT_FOUND",
    "message": "지역정보를 찾을 수 없습니다.",
    "details": { "locationId": 999999 }
  }
}
```

## 5. 게시글 API

게시글 카테고리는 서버에서 허용 목록을 제한하지 않는다. 길이가 1~30자인 임의 문자열을 사용할 수 있다. 인증 계정은 없으며 게시글별 비밀번호로 수정·삭제한다.

### 5.1 게시글 목록·검색

```http
GET /api/v1/posts
```

| 이름 | 타입 | 필수 | 기본값 | 검증·동작 |
| --- | --- | ---: | --- | --- |
| `page` | integer | X | `1` | `1` 이상 |
| `size` | integer | X | `10` | `1`~`50` |
| `category` | string | X | 없음 | 최대 30자, 정확히 일치 |
| `keyword` | string | X | 없음 | 최대 100자 |
| `searchType` | string | X | `all` | `title`, `content`, `all` |
| `sort` | string | X | `latest` | `latest`, `oldest` |

- `title`: 제목 부분 일치
- `content`: 본문 부분 일치
- `all`: 제목 또는 본문 부분 일치
- `latest`: `createdAt` 내림차순
- `oldest`: `createdAt` 오름차순

`keyword`가 없으면 `searchType`은 결과에 영향을 주지 않는다.

```http
GET /api/v1/posts?page=1&size=10&category=여행후기&keyword=서울숲&searchType=all&sort=latest
```

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 15,
        "category": "여행후기",
        "title": "서울숲 방문 후기",
        "contentPreview": "서울숲에 다녀온 후기입니다.",
        "location": {
          "id": 45,
          "title": "서울숲",
          "categoryName": "관광지"
        },
        "createdAt": "2026-07-15T13:20:00",
        "updatedAt": "2026-07-15T13:20:00"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 10,
      "totalElements": 1,
      "totalPages": 1,
      "hasPrevious": false,
      "hasNext": false
    }
  },
  "message": null
}
```

`contentPreview`는 본문 앞 100자이며, 원문이 100자를 초과하면 `...`가 붙는다. 연결 장소가 없으면 `location`은 `null`이다.

### 5.2 게시글 상세

```http
GET /api/v1/posts/{postId}
```

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": 15,
    "category": "여행후기",
    "title": "서울숲 방문 후기",
    "content": "서울숲에 다녀온 후기입니다.",
    "location": {
      "id": 45,
      "title": "서울숲",
      "categoryName": "관광지",
      "contentId": "129643",
      "address": "서울특별시 성동구 뚝섬로 273",
      "longitude": 127.037617,
      "latitude": 37.544388,
      "thumbnailUrl": null
    },
    "createdAt": "2026-07-15T13:20:00",
    "updatedAt": "2026-07-15T13:20:00"
  },
  "message": null
}
```

연결 장소가 없으면 `location`은 `null`이다.

없는 게시글 `404 Not Found`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "POST_NOT_FOUND",
    "message": "게시글을 찾을 수 없습니다.",
    "details": { "postId": 999999 }
  }
}
```

### 5.3 게시글 등록

```http
POST /api/v1/posts
Content-Type: application/json
```

Request Body:

```json
{
  "category": "여행후기",
  "title": "서울숲 방문 후기",
  "content": "서울숲에 다녀온 후기입니다.",
  "password": "1234",
  "locationId": 45
}
```

| 필드 | 타입 | 필수 | 검증 |
| --- | --- | ---: | --- |
| `category` | string | O | 1~30자 |
| `title` | string | O | 2~200자 |
| `content` | string | O | 2~5000자 |
| `password` | string | O | 4~20자 |
| `locationId` | integer 또는 null | X | 존재하는 지역정보 ID, 생략 시 `null` |

성공 응답 `201 Created`:

```json
{
  "success": true,
  "data": {
    "id": 15,
    "category": "여행후기",
    "title": "서울숲 방문 후기",
    "content": "서울숲에 다녀온 후기입니다.",
    "locationId": 45,
    "createdAt": "2026-07-15T13:20:00",
    "updatedAt": "2026-07-15T13:20:00"
  },
  "message": "게시글이 등록되었습니다."
}
```

비밀번호는 PBKDF2-SHA256으로 해시해 저장하며 응답에 포함하지 않는다. 없는 `locationId`를 보내면 `404 LOCATION_NOT_FOUND`와 `{"locationId": 요청값}` details를 반환한다.

### 5.4 비밀번호 확인

```http
POST /api/v1/posts/{postId}/verify-password
Content-Type: application/json
```

```json
{ "password": "1234" }
```

`password`는 필수이며 4~20자다.

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": { "verified": true },
  "message": "비밀번호가 확인되었습니다."
}
```

불일치 `403 Forbidden`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_POST_PASSWORD",
    "message": "비밀번호가 일치하지 않습니다.",
    "details": null
  }
}
```

이 확인 결과는 토큰을 발급하지 않는다. 수정·삭제 요청에서도 비밀번호를 다시 보내야 한다.

### 5.5 게시글 수정

```http
PUT /api/v1/posts/{postId}
Content-Type: application/json
```

등록과 동일한 `PostCreate` 본문을 사용하며 모든 필드를 다시 보낸다. 부분 수정 `PATCH`는 구현되어 있지 않다.

```json
{
  "category": "정보공유",
  "title": "수정된 제목",
  "content": "수정된 본문입니다.",
  "password": "1234",
  "locationId": null
}
```

성공 시 `200 OK`로 등록 응답과 동일한 데이터 모양을 반환하며 메시지는 `게시글이 수정되었습니다.`이다.

가능한 업무 오류:

- 게시글 없음: `404 POST_NOT_FOUND`
- 비밀번호 불일치: `403 INVALID_POST_PASSWORD`
- 연결할 지역정보 없음: `404 LOCATION_NOT_FOUND`

### 5.6 게시글 삭제

```http
DELETE /api/v1/posts/{postId}
Content-Type: application/json
```

```json
{ "password": "1234" }
```

성공 응답은 `204 No Content`이며 JSON 본문이 없다. Axios에서는 다음처럼 본문을 `data` 옵션에 넣어야 한다.

```js
await api.delete(`/api/v1/posts/${postId}`, {
  data: { password }
})
```

게시글 없음은 `404 POST_NOT_FOUND`, 비밀번호 불일치는 `403 INVALID_POST_PASSWORD`다.

## 6. 챗봇 API

### 6.1 챗봇 질의

```http
POST /api/v1/chat
Content-Type: application/json
```

Request Body:

```json
{
  "message": "강남에서 데이트할 만한 곳 추천해줘",
  "history": [
    { "role": "user", "content": "서울 여행지를 찾고 있어" },
    { "role": "assistant", "content": "어느 지역을 원하시나요?" }
  ]
}
```

| 필드 | 타입 | 필수 | 검증 |
| --- | --- | ---: | --- |
| `message` | string | O | 1~1000자 |
| `history` | array | X | 기본 `[]`, 최대 20개 |
| `history[].role` | string | O | `user` 또는 `assistant` |
| `history[].content` | string | O | 1~2000자 |

실제 처리 흐름:

1. 현재 `message`에서 한글·영문·숫자 단어를 추출한다.
2. 일부 조사와 요청 표현을 제거하고 중복을 제거한 뒤 최대 10개 핵심어를 만든다.
3. 핵심어 중 하나라도 부분 일치하는 장소와 게시글 후보를 각각 최대 100개 조회한다.
4. 장소는 제목·카테고리·주소, 게시글은 제목·카테고리·본문 일치에 가중치를 주어 정렬한다.
5. 상위 장소 10개와 게시글 10개를 OpenAI 참고자료로 전달한다.
6. `history`와 현재 메시지를 OpenAI Responses API에 전달한다.
7. 모델 답변과 검색된 참고자료를 함께 반환한다.

검색 필드:

- 장소: `title`, `address`, `categoryName`
- 게시글: `title`, `content`, `category`

`history`는 모델의 대화 문맥으로만 사용하며 DB 검색어에는 포함하지 않는다. 서버에도 저장하지 않으므로 Vue에서 관리해 매 요청에 전달해야 한다. 기본 모델은 `gpt-5-mini`이며 `OPENAI_MODEL` 환경변수로 변경할 수 있다.

성공 응답 `200 OK`:

```json
{
  "success": true,
  "data": {
    "answer": "검색된 참고자료를 바탕으로 한 답변입니다.",
    "references": {
      "locations": [
        {
          "id": 45,
          "contentId": "129643",
          "categoryName": "관광지",
          "title": "서울숲",
          "address": "서울특별시 성동구 뚝섬로 273",
          "thumbnailUrl": null
        }
      ],
      "posts": [
        {
          "id": 15,
          "category": "여행후기",
          "title": "서울숲 방문 후기"
        }
      ]
    }
  },
  "message": null
}
```

챗봇의 장소 reference에는 목록 응답과 달리 `contentTypeId`, `longitude`, `latitude`가 포함되지 않는다. 검색 결과가 없더라도 OpenAI 호출은 수행하며 성공하면 빈 reference 배열과 모델 답변을 `200`으로 반환한다.

API 키 누락 또는 OpenAI 처리 실패 `502 Bad Gateway`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CHAT_PROVIDER_ERROR",
    "message": "채팅 응답을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    "details": null
  }
}
```

OpenAI `RateLimitError` 발생 `429 Too Many Requests`:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CHAT_RATE_LIMIT_EXCEEDED",
    "message": "채팅 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
    "details": { "retryAfterSeconds": 30 }
  }
}
```

`retryAfterSeconds`는 서버가 고정해서 반환하는 안내값이며 HTTP `Retry-After` 헤더는 설정하지 않는다.

## 7. 통계 API

### 7.1 지역정보 카테고리 통계

```http
GET /api/v1/statistics/locations/categories
```

```json
{
  "success": true,
  "data": {
    "chartType": "bar",
    "title": "서울 지역정보 카테고리별 현황",
    "labels": ["관광지", "문화시설", "축제공연행사", "여행코스", "레포츠", "숙박", "쇼핑", "음식점"],
    "datasets": [
      { "label": "데이터 수", "data": [783, 566, 201, 51, 126, 423, 4368, 0] }
    ],
    "total": 6518
  },
  "message": null
}
```

라벨 순서는 위와 같이 고정되고 데이터가 없는 카테고리는 `0`이다. 숫자는 현재 저장소 데이터 기준 예시이며 DB 내용에 따라 달라진다.

### 7.2 게시글 카테고리 통계

```http
GET /api/v1/statistics/posts/categories
```

```json
{
  "success": true,
  "data": {
    "chartType": "doughnut",
    "title": "게시판 카테고리별 게시글 현황",
    "labels": ["여행후기", "질문"],
    "datasets": [
      { "label": "게시글 수", "data": [12, 5] }
    ],
    "total": 17
  },
  "message": null
}
```

게시글 카테고리는 건수 내림차순이다. 게시글이 없으면 `labels`와 `data`는 빈 배열이고 `total`은 `0`이다.

## 8. 데이터 출처 API

```http
GET /api/v1/data-source
```

```json
{
  "success": true,
  "data": {
    "provider": "한국관광공사",
    "datasetName": "국문 관광정보 서비스 (TourAPI 4.0)",
    "region": "서울",
    "totalCount": 6518,
    "sourceUrl": "https://www.data.go.kr/data/15101578/openapi.do",
    "license": {
      "name": "공공누리 제3유형",
      "attributionRequired": true,
      "commercialUseAllowed": true,
      "modificationAllowed": false
    },
    "attributionText": "이 서비스는 한국관광공사 Tour API(TourAPI 4.0)의 데이터를 활용하였습니다."
  },
  "message": null
}
```

`totalCount`만 현재 DB에서 계산하며 나머지는 서버 코드에 고정된 값이다.

## 9. 상태 확인 API

```http
GET /health
```

이 API는 공통 응답 wrapper를 사용하지 않는다.

DB 연결 성공 `200 OK`:

```json
{
  "status": "ok",
  "service": "localhub-api",
  "database": "connected",
  "timestamp": "2026-07-15T13:20:00.123456"
}
```

DB 연결 실패 `503 Service Unavailable`:

```json
{
  "status": "error",
  "service": "localhub-api",
  "database": "disconnected",
  "timestamp": "2026-07-15T13:20:00.123456"
}
```

## 10. 오류 코드

| HTTP | code | 발생 조건 |
| ---: | --- | --- |
| 400 | `INVALID_LOCATION_CATEGORY` | 목록 조회의 지원하지 않는 장소 카테고리 |
| 403 | `INVALID_POST_PASSWORD` | 게시글 비밀번호 불일치 |
| 404 | `LOCATION_NOT_FOUND` | 지역정보 또는 연결할 지역정보 없음 |
| 404 | `POST_NOT_FOUND` | 게시글 없음 |
| 422 | `VALIDATION_ERROR` | Body, Query, Path 검증 실패 |
| 429 | `CHAT_RATE_LIMIT_EXCEEDED` | OpenAI SDK가 `RateLimitError` 발생 |
| 500 | `INTERNAL_SERVER_ERROR` | 처리되지 않은 서버 예외 |
| 502 | `CHAT_PROVIDER_ERROR` | API 키 누락 또는 OpenAI 처리 실패 |

라우트가 없거나 지원하지 않는 HTTP Method처럼 FastAPI가 문자열 `detail`을 가진 `HTTPException`을 발생시키는 경우에는 해당 HTTP 상태와 함께 `HTTP_ERROR` 코드가 반환될 수 있다.

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "HTTP_ERROR",
    "message": "Not Found",
    "details": null
  }
}
```

## 11. Vue 연동 참고

Axios 인스턴스 예시:

```js
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
})
```

성공 데이터 접근:

```js
const response = await api.get('/api/v1/locations')
const items = response.data.data.items
```

오류 데이터 접근:

```js
try {
  await api.get('/api/v1/locations', { params: { category: '카페' } })
} catch (error) {
  const apiError = error.response?.data?.error
  console.log(apiError?.code, apiError?.message, apiError?.details)
}
```

프론트엔드 구현 시 특히 다음을 주의한다.

- 삭제 성공 `204`에서는 `response.data`가 비어 있다.
- DELETE 비밀번호는 Axios 설정 객체의 `data`에 담는다.
- 챗봇 `history`는 서버가 저장하지 않으므로 프론트엔드 상태로 관리한다.
- `location`, 이미지 URL, 주소, 좌표 등은 `null`일 수 있다.
- 게시글의 `password`를 로컬 스토리지에 저장하지 않는다.
- 서버는 현재 인증, 요청 취소, 챗봇 스트리밍을 제공하지 않는다.
- 배포된 Vue Origin이 `ALLOWED_ORIGINS`에 정확히 등록되어 있어야 브라우저 요청이 허용된다.
