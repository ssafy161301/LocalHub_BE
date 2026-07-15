from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import chat_keywords, normalize_chat_answer, search_chat_sources
from app.models import Location, Post


def test_chat_keywords_normalizes_particles_and_request_words():
    assert chat_keywords("강남에서 데이트할 만한 곳 추천해줘") == ["강남", "데이트"]
    assert chat_keywords("아이와 가볼 관광지를 알려주세요") == ["아이", "관광지"]


def test_chat_keywords_handles_requests_without_spaces():
    assert chat_keywords("강남갈만한 곳 추천좀") == ["강남"]
    assert chat_keywords("강남가볼만한곳추천해줘") == ["강남"]
    assert chat_keywords("홍대에서놀만한곳추천해줘") == ["홍대"]


def test_chat_answer_normalizes_line_endings_and_excess_blank_lines():
    answer = "  추천 장소입니다.  \r\n\r\n\r\n1. 서울숲  \r\n설명입니다.\r\n"

    assert normalize_chat_answer(answer) == "추천 장소입니다.\n\n1. 서울숲\n설명입니다."


def test_chat_search_matches_any_keyword_and_ranks_more_matches():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Location(content_id="chat-1", content_type_id="12", category_name="관광지",
                     title="강남 공원", address="서울 강남구"),
            Location(content_id="chat-2", content_type_id="12", category_name="관광지",
                     title="한강 공원", address="서울 영등포구"),
            Post(category="데이트", title="강남 데이트 후기", content="산책하기 좋은 장소",
                 password_hash="test"),
        ])
        db.commit()

        keywords, locations, posts = search_chat_sources(
            db, "강남에서 데이트할 만한 곳 추천해줘"
        )

        assert keywords == ["강남", "데이트"]
        assert locations[0].title == "강남 공원"
        assert posts[0].title == "강남 데이트 후기"


def test_chat_search_falls_back_to_hangul_typo_similarity():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Location(content_id="typo-1", content_type_id="12", category_name="관광지",
                        title="강남 공원", address="서울 강남구"))
        db.commit()

        keywords, locations, _ = search_chat_sources(db, "강낭갈만한곳 추천좀")

        assert keywords == ["강낭"]
        assert locations[0].title == "강남 공원"
