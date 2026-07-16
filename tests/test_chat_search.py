from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    analyze_chat_intent, chat, chat_keywords, normalize_chat_answer,
    search_chat_sources,
)
from app.models import Location, Post
from app.schemas import (
    ChatBody, ChatGeneratedAnswer, ChatSearchIntent, HistoryItem,
)


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


def test_chat_search_uses_general_intent_location_and_categories():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Location(content_id="intent-1", content_type_id="14", category_name="문화시설",
                     title="역삼 문화센터", address="서울 강남구 역삼동"),
            Location(content_id="intent-2", content_type_id="38", category_name="쇼핑",
                     title="역삼 상점", address="서울 강남구 역삼동"),
            Location(content_id="intent-3", content_type_id="14", category_name="문화시설",
                     title="실내 전시관", address="서울 종로구"),
        ])
        db.commit()

        intent = ChatSearchIntent(
            intent="recommendation", search_required=True,
            resolved_query="역삼역 근처에서 함께 즐길 문화 장소 추천",
            location_terms=["역삼역", "역삼"], search_terms=["함께", "실내"],
            preferred_categories=["문화시설"], excluded_categories=[],
        )
        _, locations, _ = search_chat_sources(
            db, "역삼역 근처에 갈 곳", intent=intent
        )

        assert locations[0].title == "역삼 문화센터"
        assert "역삼 상점" in [item.title for item in locations]
        assert "실내 전시관" not in [item.title for item in locations]


def test_chat_search_uses_inferred_categories_when_terms_are_not_stored():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Location(content_id="weather-1", content_type_id="14", category_name="문화시설",
                     title="서울 전시관", address="서울 중구"),
            Location(content_id="weather-2", content_type_id="28", category_name="레포츠",
                     title="야외 운동장", address="서울 중구"),
        ])
        db.commit()

        intent = ChatSearchIntent(
            intent="recommendation", search_required=True,
            resolved_query="비 오는 날 아이와 갈 실내 장소 추천",
            location_terms=[], search_terms=["비 오는 날", "아이", "실내"],
            preferred_categories=["문화시설"], excluded_categories=["레포츠"],
        )
        _, locations, _ = search_chat_sources(
            db, "비 오는 날 아이랑 어디 가지?", intent=intent
        )

        assert [item.title for item in locations] == ["서울 전시관"]


def test_chat_search_skips_database_for_smalltalk():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Location(content_id="hello-1", content_type_id="12", category_name="관광지",
                        title="안녕 공원", address="서울"))
        db.commit()
        intent = ChatSearchIntent(
            intent="smalltalk", search_required=False, resolved_query="인사",
            location_terms=[], search_terms=[], preferred_categories=[],
            excluded_categories=[],
        )

        assert search_chat_sources(db, "안녕", intent=intent) == ([], [], [])


def test_intent_analysis_uses_history_and_structured_output(monkeypatch):
    parsed = ChatSearchIntent(
        intent="recommendation", search_required=True,
        resolved_query="강남에서 비 오는 날 갈 실내 장소 추천",
        location_terms=["강남"], search_terms=["비 오는 날", "실내"],
        preferred_categories=["문화시설", "쇼핑"], excluded_categories=[],
    )

    class FakeResponses:
        def parse(self, **kwargs):
            self.kwargs = kwargs
            return type("Response", (), {"output_parsed": parsed})()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    history = [
        HistoryItem(role="user", content="강남에서 갈 곳을 찾고 있어"),
        HistoryItem(role="assistant", content="어떤 상황인가요?"),
    ]
    result = analyze_chat_intent(FakeClient(), "비 오는 날은?", history)

    assert result.resolved_query == parsed.resolved_query
    assert FakeClient.responses.kwargs["model"] == "test-model"
    assert FakeClient.responses.kwargs["text_format"] is ChatSearchIntent
    assert FakeClient.responses.kwargs["input"][-2]["content"] == "어떤 상황인가요?"


def test_chat_returns_only_model_selected_valid_references(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        location = Location(
            content_id="answer-1", content_type_id="12", category_name="관광지",
            title="서울숲", address="서울 성동구",
        )
        db.add(location)
        db.flush()
        post = Post(
            category="여행후기", title="서울숲 산책 후기", content="산책 정보",
            password_hash="test", location_id=location.id,
        )
        db.add(post)
        db.commit()

        intent = ChatSearchIntent(
            intent="recommendation", search_required=True,
            resolved_query="성동구에서 산책할 장소 추천",
            location_terms=["성동구"], search_terms=["서울숲", "산책"],
            preferred_categories=["관광지"], excluded_categories=[],
        )
        answer = ChatGeneratedAnswer(
            answer="1. 서울숲\n산책하기 좋은 관광지입니다.",
            location_ids=[location.id, 999999], post_ids=[post.id, 999999],
        )

        class FakeResponses:
            def parse(self, **kwargs):
                parsed = intent if kwargs["text_format"] is ChatSearchIntent else answer
                return type("Response", (), {"output_parsed": parsed})()

        class FakeClient:
            responses = FakeResponses()

        import openai
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(openai, "OpenAI", lambda: FakeClient())

        result = chat(ChatBody(message="성동구에서 산책할 곳 알려줘"), db)

        assert result["data"]["references"]["locations"][0]["id"] == location.id
        assert result["data"]["references"]["posts"][0]["id"] == post.id
        assert len(result["data"]["references"]["locations"]) == 1
        assert len(result["data"]["references"]["posts"]) == 1
