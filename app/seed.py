import json
import os
from itertools import cycle
from pathlib import Path

from sqlalchemy import func, select

from .models import Location, Post
from .security import hash_password

CATEGORY_NAMES = {"12": "관광지", "14": "문화시설", "15": "축제공연행사", "25": "여행코스",
                  "28": "레포츠", "32": "숙박", "38": "쇼핑"}
DUMMY_POST_CATEGORIES = (
    "관광지", "문화시설", "축제", "여행코스", "레포츠", "숙박",
    "쇼핑", "맛집", "여행후기", "정보공유", "질문",
)
DUMMY_POST_CONTENTS = (
    "{location}에 직접 방문해 본 경험을 공유합니다. 교통편과 운영 시간을 미리 확인하면 더욱 편하게 둘러볼 수 있습니다.",
    "{location} 방문을 계획하는 분들을 위한 정보입니다. 방문 전 공식 안내와 현장 상황을 함께 확인해 주세요.",
    "{location}에 가보신 분이 있다면 추천 관람 동선과 알아두면 좋은 팁을 공유해 주세요.",
)
DUMMY_POST_COUNT = 30


def _nullable(value):
    return value if value not in (None, "") else None


def _float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def seed_locations(db):
    if db.scalar(select(func.count(Location.id))):
        return
    data_dir = Path(__file__).resolve().parents[1] / "data" / "서울"
    rows = []
    for path in sorted(data_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        category = payload["contentType"]
        for item in payload["items"]:
            rows.append(Location(
                content_id=item["contentid"], content_type_id=item["contenttypeid"], category_name=category,
                title=item["title"], address=_nullable(item.get("addr1")),
                address_detail=_nullable(item.get("addr2")), zipcode=_nullable(item.get("zipcode")),
                telephone=_nullable(item.get("tel")), longitude=_float(item.get("mapx")),
                latitude=_float(item.get("mapy")), sigungu_code=_nullable(item.get("sigungucode")),
                image_url=_nullable(item.get("firstimage")), thumbnail_url=_nullable(item.get("firstimage2")),
                copyright_code=_nullable(item.get("cpyrhtDivCd")),
                source_created_at=_nullable(item.get("createdtime")), source_modified_at=_nullable(item.get("modifiedtime"))))
    db.add_all(rows)
    db.commit()


def seed_dummy_posts(db, count=DUMMY_POST_COUNT):
    """Create demo posts once when the posts table is empty."""
    if db.scalar(select(func.count(Post.id))):
        return 0

    locations = db.scalars(select(Location).order_by(Location.id).limit(count)).all()
    if not locations:
        return 0

    password_hash = hash_password(os.getenv("DUMMY_POST_PASSWORD", "dummy1234"))
    category_cycle = cycle(DUMMY_POST_CATEGORIES)
    rows = []
    for index in range(count):
        location = locations[index % len(locations)]
        category = next(category_cycle)
        rows.append(Post(
            category=category,
            title=f"[더미] {location.title} {category} #{index + 1}",
            content=DUMMY_POST_CONTENTS[index % len(DUMMY_POST_CONTENTS)].format(
                location=location.title
            ),
            password_hash=password_hash,
            location_id=location.id,
        ))

    db.add_all(rows)
    db.commit()
    return len(rows)
