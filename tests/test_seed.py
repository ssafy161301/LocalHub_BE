from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Location, Post
from app.seed import DUMMY_POST_CATEGORIES, seed_dummy_posts
from app.security import verify_password


def test_seed_dummy_posts_creates_30_once():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(Location(
            content_id="seed-location",
            content_type_id="12",
            category_name="관광지",
            title="시드 테스트 장소",
        ))
        db.commit()

        assert seed_dummy_posts(db) == 30
        assert db.scalar(select(func.count(Post.id))) == 30
        first = db.scalar(select(Post).order_by(Post.id))
        assert first.title == "[더미] 시드 테스트 장소 관광지 #1"
        assert verify_password("dummy1234", first.password_hash)
        categories = set(db.scalars(select(Post.category)).all())
        assert categories == set(DUMMY_POST_CATEGORIES)
        assert "동행구함" not in categories

        assert seed_dummy_posts(db) == 0
        assert db.scalar(select(func.count(Post.id))) == 30
