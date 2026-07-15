import os
import re
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Location, Post
from .responses import fail, pagination, success
from .schemas import ChatBody, PasswordBody, PostCreate
from .security import hash_password, verify_password
from .seed import CATEGORY_NAMES, seed_locations


logger = logging.getLogger(__name__)


CHAT_STOP_WORDS = {
    "가볼", "갈", "곳", "관련", "만한", "뭐", "무엇", "어디", "어떤", "여기", "저기",
    "알려줘", "알려주세요", "추천", "추천해줘", "추천해주세요", "찾아줘", "찾아주세요",
    "해줘", "해주세요", "있어", "있나요", "있는", "좋은",
}
CHAT_SUFFIXES = (
    "에서는", "으로는", "에게서", "부터는", "까지는", "이라도", "라도",
    "에서", "으로", "에게", "한테", "부터", "까지", "처럼", "보다",
    "에는", "으로", "하고", "이며", "이나", "거나", "인데", "할",
    "은", "는", "이", "가", "을", "를", "과", "와", "의", "에", "로", "도", "만",
)


def chat_keywords(message: str) -> list[str]:
    """Extract useful DB search terms from a natural-language chat message."""
    result = []
    for raw in re.findall(r"[0-9A-Za-z가-힣]+", message.lower()):
        word = raw
        for suffix in CHAT_SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 2:
                word = word[:-len(suffix)]
                break
        if len(word) >= 2 and word not in CHAT_STOP_WORDS and word not in result:
            result.append(word)
    return result[:10]


def search_chat_sources(db: Session, message: str, limit: int = 10):
    """Find and rank sources that match at least one normalized keyword."""
    keywords = chat_keywords(message)
    if not keywords:
        return [], [], []

    location_conditions = []
    post_conditions = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        location_conditions.extend((
            Location.title.ilike(pattern),
            Location.address.ilike(pattern),
            Location.category_name.ilike(pattern),
        ))
        post_conditions.extend((
            Post.title.ilike(pattern),
            Post.content.ilike(pattern),
            Post.category.ilike(pattern),
        ))

    location_candidates = db.scalars(
        select(Location).where(or_(*location_conditions)).limit(100)
    ).all()
    post_candidates = db.scalars(
        select(Post).where(or_(*post_conditions)).limit(100)
    ).all()

    def location_score(item: Location):
        title = item.title.lower()
        address = (item.address or "").lower()
        category = item.category_name.lower()
        return sum(4 * (k in title) + 2 * (k in address) + 3 * (k in category) for k in keywords)

    def post_score(item: Post):
        title = item.title.lower()
        content = item.content.lower()
        category = item.category.lower()
        return sum(4 * (k in title) + (k in content) + 3 * (k in category) for k in keywords)

    locations = sorted(location_candidates, key=location_score, reverse=True)[:limit]
    posts = sorted(post_candidates, key=post_score, reverse=True)[:limit]
    return keywords, locations, posts


def loc_summary(x: Location):
    return {"id": x.id, "contentId": x.content_id, "contentTypeId": x.content_type_id,
            "categoryName": x.category_name, "title": x.title, "address": x.address,
            "longitude": x.longitude, "latitude": x.latitude, "thumbnailUrl": x.thumbnail_url}


def loc_detail(x: Location):
    return {**loc_summary(x), "addressDetail": x.address_detail, "zipcode": x.zipcode,
            "telephone": x.telephone, "sigunguCode": x.sigungu_code, "imageUrl": x.image_url,
            "copyrightCode": x.copyright_code, "sourceCreatedAt": x.source_created_at,
            "sourceModifiedAt": x.source_modified_at}


def post_location(x: Location | None, detailed=False):
    if not x:
        return None
    value = {"id": x.id, "title": x.title, "categoryName": x.category_name}
    if detailed:
        value.update({"contentId": x.content_id, "address": x.address, "longitude": x.longitude,
                      "latitude": x.latitude, "thumbnailUrl": x.thumbnail_url})
    return value


def post_detail(x: Post):
    return {"id": x.id, "category": x.category, "title": x.title, "content": x.content,
            "location": post_location(x.location, True), "createdAt": x.created_at.isoformat(),
            "updatedAt": x.updated_at.isoformat()}


def post_saved(x: Post):
    return {"id": x.id, "category": x.category, "title": x.title, "content": x.content,
            "locationId": x.location_id, "createdAt": x.created_at.isoformat(),
            "updatedAt": x.updated_at.isoformat()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_locations(db)
    yield


app = FastAPI(title="LocalHub API", version="1.0.0", lifespan=lifespan)

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(v) for v in e["loc"] if v != "body"), "reason": e["msg"]}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={"success": False, "data": None,
        "error": {"code": "VALIDATION_ERROR", "message": "요청 값이 올바르지 않습니다.", "details": details}})


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {
        "code": "HTTP_ERROR", "message": str(exc.detail), "details": None}
    return JSONResponse(status_code=exc.status_code,
                        content={"success": False, "data": None, "error": detail})


@app.exception_handler(Exception)
async def exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error", exc_info=exc)
    return JSONResponse(status_code=500, content={"success": False, "data": None,
        "error": {"code": "INTERNAL_SERVER_ERROR", "message": "서버 오류가 발생했습니다.", "details": None}})


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        status, database, code = "ok", "connected", 200
    except Exception:
        status, database, code = "error", "disconnected", 503
    return JSONResponse(status_code=code, content={"status": status, "service": "localhub-api",
                        "database": database, "timestamp": datetime.now().isoformat()})


@app.get("/api/v1/locations/categories")
def location_categories(db: Session = Depends(get_db)):
    rows = db.execute(select(Location.content_type_id, Location.category_name, func.count()).group_by(
        Location.content_type_id, Location.category_name).order_by(Location.content_type_id)).all()
    counts = {content_type_id: count for content_type_id, _, count in rows}
    return success([{"contentTypeId": content_type_id, "name": name, "count": counts.get(content_type_id, 0)}
                    for content_type_id, name in CATEGORY_NAMES.items()])


@app.get("/api/v1/locations")
def locations(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
              category: str | None = None, keyword: str | None = Query(None, max_length=100),
              sigunguCode: str | None = None, hasImage: bool | None = None,
              sort: str = Query("title", pattern="^(title|title_desc|latest)$"), db: Session = Depends(get_db)):
    if category and category not in CATEGORY_NAMES.values():
        fail(400, "INVALID_LOCATION_CATEGORY", "지원하지 않는 지역정보 카테고리입니다.", {"category": category})
    stmt = select(Location)
    if category: stmt = stmt.where(Location.category_name == category)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(Location.title.ilike(pattern), Location.address.ilike(pattern)))
    if sigunguCode: stmt = stmt.where(Location.sigungu_code == sigunguCode)
    if hasImage is not None: stmt = stmt.where(Location.image_url.is_not(None) if hasImage else Location.image_url.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = Location.title.asc() if sort == "title" else Location.title.desc() if sort == "title_desc" else Location.source_modified_at.desc()
    items = db.scalars(stmt.order_by(order).offset((page - 1) * size).limit(size)).all()
    return success({"items": [loc_summary(x) for x in items], "pagination": pagination(page, size, total)})


@app.get("/api/v1/locations/{locationId}")
def location(locationId: int, db: Session = Depends(get_db)):
    item = db.get(Location, locationId)
    if not item: fail(404, "LOCATION_NOT_FOUND", "지역정보를 찾을 수 없습니다.", {"locationId": locationId})
    return success(loc_detail(item))


@app.get("/api/v1/posts")
def posts(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50), category: str | None = Query(None, max_length=30),
          keyword: str | None = Query(None, max_length=100), searchType: str = Query("all", pattern="^(title|content|all)$"),
          sort: str = Query("latest", pattern="^(latest|oldest)$"), db: Session = Depends(get_db)):
    stmt = select(Post)
    if category: stmt = stmt.where(Post.category == category)
    if keyword:
        p = f"%{keyword}%"
        stmt = stmt.where(Post.title.ilike(p) if searchType == "title" else Post.content.ilike(p) if searchType == "content" else or_(Post.title.ilike(p), Post.content.ilike(p)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Post.created_at.desc() if sort == "latest" else Post.created_at.asc()).offset((page-1)*size).limit(size)).all()
    result = [{"id": x.id, "category": x.category, "title": x.title,
               "contentPreview": x.content[:100] + ("..." if len(x.content) > 100 else ""),
               "location": post_location(x.location), "createdAt": x.created_at.isoformat(), "updatedAt": x.updated_at.isoformat()} for x in items]
    return success({"items": result, "pagination": pagination(page, size, total)})


@app.post("/api/v1/posts", status_code=201)
def create_post(body: PostCreate, db: Session = Depends(get_db)):
    if body.locationId is not None and not db.get(Location, body.locationId):
        fail(404, "LOCATION_NOT_FOUND", "연결할 지역정보를 찾을 수 없습니다.", {"locationId": body.locationId})
    item = Post(category=body.category, title=body.title, content=body.content,
                password_hash=hash_password(body.password), location_id=body.locationId)
    db.add(item); db.commit(); db.refresh(item)
    return success(post_saved(item), "게시글이 등록되었습니다.")


@app.get("/api/v1/posts/{postId}")
def get_post(postId: int, db: Session = Depends(get_db)):
    item = db.get(Post, postId)
    if not item: fail(404, "POST_NOT_FOUND", "게시글을 찾을 수 없습니다.", {"postId": postId})
    return success(post_detail(item))


def require_post(postId: int, db: Session):
    item = db.get(Post, postId)
    if not item: fail(404, "POST_NOT_FOUND", "게시글을 찾을 수 없습니다.", {"postId": postId})
    return item


@app.post("/api/v1/posts/{postId}/verify-password")
def verify_post(postId: int, body: PasswordBody, db: Session = Depends(get_db)):
    item = require_post(postId, db)
    if not verify_password(body.password, item.password_hash): fail(403, "INVALID_POST_PASSWORD", "비밀번호가 일치하지 않습니다.")
    return success({"verified": True}, "비밀번호가 확인되었습니다.")


@app.put("/api/v1/posts/{postId}")
def update_post(postId: int, body: PostCreate, db: Session = Depends(get_db)):
    item = require_post(postId, db)
    if not verify_password(body.password, item.password_hash): fail(403, "INVALID_POST_PASSWORD", "비밀번호가 일치하지 않습니다.")
    if body.locationId is not None and not db.get(Location, body.locationId):
        fail(404, "LOCATION_NOT_FOUND", "연결할 지역정보를 찾을 수 없습니다.", {"locationId": body.locationId})
    item.category, item.title, item.content, item.location_id = body.category, body.title, body.content, body.locationId
    item.updated_at = datetime.now(); db.commit(); db.refresh(item)
    return success(post_saved(item), "게시글이 수정되었습니다.")


@app.delete("/api/v1/posts/{postId}", status_code=204)
def delete_post(postId: int, body: PasswordBody, db: Session = Depends(get_db)):
    item = require_post(postId, db)
    if not verify_password(body.password, item.password_hash): fail(403, "INVALID_POST_PASSWORD", "비밀번호가 일치하지 않습니다.")
    db.delete(item); db.commit()
    return Response(status_code=204)


@app.get("/api/v1/statistics/locations/categories")
def location_statistics(db: Session = Depends(get_db)):
    rows = db.execute(select(Location.category_name, func.count()).group_by(Location.category_name).order_by(Location.category_name)).all()
    counts = dict(rows)
    labels = list(CATEGORY_NAMES.values())
    values = [counts.get(name, 0) for name in labels]
    return success({"chartType": "bar", "title": "서울 지역정보 카테고리별 현황", "labels": labels,
                    "datasets": [{"label": "데이터 수", "data": values}], "total": sum(values)})


@app.get("/api/v1/statistics/posts/categories")
def post_statistics(db: Session = Depends(get_db)):
    rows = db.execute(select(Post.category, func.count().label("count")).group_by(Post.category).order_by(text("count DESC"))).all()
    values = [c for _, c in rows]
    return success({"chartType": "doughnut", "title": "게시판 카테고리별 게시글 현황", "labels": [n for n, _ in rows],
                    "datasets": [{"label": "게시글 수", "data": values}], "total": sum(values)})


@app.get("/api/v1/data-source")
def data_source(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Location.id))) or 0
    return success({"provider": "한국관광공사", "datasetName": "국문 관광정보 서비스 (TourAPI 4.0)", "region": "서울",
        "totalCount": total, "sourceUrl": "https://www.data.go.kr/data/15101578/openapi.do",
        "license": {"name": "공공누리 제3유형", "attributionRequired": True, "commercialUseAllowed": True, "modificationAllowed": False},
        "attributionText": "이 서비스는 한국관광공사 Tour API(TourAPI 4.0)의 데이터를 활용하였습니다."})


@app.post("/api/v1/chat")
def chat(body: ChatBody, db: Session = Depends(get_db)):
    keywords, locations, posts = search_chat_sources(db, body.message)
    refs = {"locations": [{k: v for k, v in loc_summary(x).items() if k not in ("contentTypeId", "longitude", "latitude")} for x in locations],
            "posts": [{"id": x.id, "category": x.category, "title": x.title} for x in posts]}
    if not os.getenv("OPENAI_API_KEY"):
        fail(502, "CHAT_PROVIDER_ERROR", "채팅 응답을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.")
    context_items = [f"검색 핵심어: {', '.join(keywords)}"] if keywords else []
    context_items += [f"장소: {x.title} / {x.category_name} / {x.address or ''}" for x in locations]
    context_items += [f"게시글: {x.title} / {x.category} / {x.content[:300]}" for x in posts]
    context = "\n".join(context_items) or "검색된 참고 자료 없음"
    try:
        from openai import OpenAI, RateLimitError
        client = OpenAI()
        history = [{"role": x.role, "content": x.content} for x in body.history]
        prompt = "당신은 서울 지역 안내 도우미입니다. 제공된 참고 자료 범위 안에서만 한국어로 답하고, 자료가 없으면 없다고 안내하세요.\n참고 자료:\n" + context
        response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=prompt, input=history + [{"role": "user", "content": body.message}])
        return success({"answer": response.output_text, "references": refs})
    except RateLimitError:
        fail(429, "CHAT_RATE_LIMIT_EXCEEDED", "채팅 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", {"retryAfterSeconds": 30})
    except Exception as exc:
        logger.exception("OpenAI chat request failed", exc_info=exc)
        fail(502, "CHAT_PROVIDER_ERROR", "채팅 응답을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.")
