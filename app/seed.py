import json
from pathlib import Path

from sqlalchemy import func, select

from .models import Location

CATEGORY_NAMES = {"12": "관광지", "14": "문화시설", "15": "축제공연행사", "25": "여행코스",
                  "28": "레포츠", "32": "숙박", "38": "쇼핑", "39": "음식점"}


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
