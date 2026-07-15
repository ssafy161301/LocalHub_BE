from fastapi.testclient import TestClient

from app.main import app


def test_cors_preflight_for_vue_dev_server():
    with TestClient(app) as client:
        response = client.options("/api/v1/locations", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_does_not_allow_unknown_origin():
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "https://unknown.example"})
        assert "access-control-allow-origin" not in response.headers


def test_locations_and_crud():
    with TestClient(app) as client:
        assert client.get("/health").json()["database"] == "connected"
        categories = client.get("/api/v1/locations/categories").json()["data"]
        assert len(categories) == 7
        assert sum(item["count"] for item in categories) == 6518
        assert all(item["contentTypeId"] != "39" for item in categories)

        search = client.get("/api/v1/locations", params={"keyword": "서울숲"}).json()
        assert search["success"] and search["data"]["items"]
        location_id = search["data"]["items"][0]["id"]

        created = client.post("/api/v1/posts", json={"category": "여행후기", "title": "테스트 게시글",
            "content": "테스트 본문입니다", "password": "1234", "locationId": location_id})
        assert created.status_code == 201
        post_id = created.json()["data"]["id"]
        assert "password" not in created.text

        wrong = client.post(f"/api/v1/posts/{post_id}/verify-password", json={"password": "9999"})
        assert wrong.status_code == 403 and wrong.json()["error"]["code"] == "INVALID_POST_PASSWORD"
        assert client.post(f"/api/v1/posts/{post_id}/verify-password", json={"password": "1234"}).status_code == 200
        assert client.put(f"/api/v1/posts/{post_id}", json={"category": "여행후기", "title": "수정된 게시글",
            "content": "수정된 본문입니다", "password": "1234", "locationId": None}).status_code == 200
        assert client.request("DELETE", f"/api/v1/posts/{post_id}", json={"password": "1234"}).status_code == 204


def test_validation_and_not_found_shape():
    with TestClient(app) as client:
        invalid = client.get("/api/v1/locations", params={"category": "카페"})
        assert invalid.status_code == 400
        assert invalid.json() == {"success": False, "data": None, "error": {
            "code": "INVALID_LOCATION_CATEGORY", "message": "지원하지 않는 지역정보 카테고리입니다.",
            "details": {"category": "카페"}}}
        missing = client.get("/api/v1/posts/999999")
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "POST_NOT_FOUND"
