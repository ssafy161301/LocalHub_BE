import argparse
import os
from itertools import cycle

import httpx


CATEGORIES = (
    "관광지", "문화시설", "축제", "여행코스", "레포츠", "숙박",
    "쇼핑", "맛집", "여행후기", "정보공유", "질문",
)
DEFAULT_API_URL = "https://localhub-be-xflx.onrender.com"
CONTENT_TEMPLATES = (
    "{location}에 직접 방문해 본 경험을 공유합니다. 교통편과 운영 시간을 미리 확인하면 더욱 편하게 둘러볼 수 있습니다.",
    "{location} 방문을 계획하는 분들을 위한 정보입니다. 방문 전 공식 안내와 현장 상황을 함께 확인해 주세요.",
    "{location}에 가보신 분이 있다면 추천 관람 동선과 알아두면 좋은 팁을 공유해 주세요.",
)


def parse_args():
    parser = argparse.ArgumentParser(description="LocalHub API로 커뮤니티 더미 게시글을 생성합니다.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("LOCALHUB_API_URL", DEFAULT_API_URL),
        help=f"백엔드 Base URL (기본값: {DEFAULT_API_URL})",
    )
    parser.add_argument("--count", type=int, default=30, help="생성할 게시글 수 (기본값: 30)")
    parser.add_argument(
        "--password",
        default=os.getenv("DUMMY_POST_PASSWORD", "dummy1234"),
        help="더미 게시글 공통 비밀번호",
    )
    parser.add_argument("--force", action="store_true", help="동일 제목이 있어도 다시 생성")
    return parser.parse_args()


def require_valid_args(args):
    if not 1 <= args.count <= 100:
        raise SystemExit("--count는 1~100 사이여야 합니다.")
    if not 4 <= len(args.password) <= 20:
        raise SystemExit("--password는 API 검증 규칙에 따라 4~20자여야 합니다.")


def fetch_locations(client: httpx.Client, count: int):
    response = client.get("/api/v1/locations", params={"page": 1, "size": min(count, 100)})
    response.raise_for_status()
    locations = response.json()["data"]["items"]
    if not locations:
        raise RuntimeError("연결할 지역정보가 없습니다. 서버의 초기 데이터 적재 상태를 확인하세요.")
    return locations


def fetch_existing_dummy_titles(client: httpx.Client):
    response = client.get("/api/v1/posts", params={
        "page": 1,
        "size": 50,
        "keyword": "[더미]",
        "searchType": "title",
    })
    response.raise_for_status()
    return {item["title"] for item in response.json()["data"]["items"]}


def build_posts(locations, count: int, password: str):
    posts = []
    category_cycle = cycle(CATEGORIES)
    for index in range(count):
        location = locations[index % len(locations)]
        category = next(category_cycle)
        location_title = location["title"]
        posts.append({
            "category": category,
            "title": f"[더미] {location_title} {category} #{index + 1}",
            "content": CONTENT_TEMPLATES[index % len(CONTENT_TEMPLATES)].format(
                location=location_title
            ),
            "password": password,
            "locationId": location["id"],
        })
    return posts


def main():
    args = parse_args()
    require_valid_args(args)
    base_url = args.base_url.rstrip("/")

    created = 0
    skipped = 0
    with httpx.Client(base_url=base_url, timeout=30) as client:
        health = client.get("/health")
        health.raise_for_status()
        if health.json().get("database") != "connected":
            raise RuntimeError("데이터베이스가 연결되지 않았습니다.")

        locations = fetch_locations(client, args.count)
        existing_titles = set() if args.force else fetch_existing_dummy_titles(client)

        for post in build_posts(locations, args.count, args.password):
            if post["title"] in existing_titles:
                skipped += 1
                print(f"SKIP  {post['title']}")
                continue

            response = client.post("/api/v1/posts", json=post)
            response.raise_for_status()
            saved = response.json()["data"]
            created += 1
            print(f"CREATE id={saved['id']} {saved['title']}")

    print(f"완료: 생성 {created}건, 건너뜀 {skipped}건, 대상 {base_url}")


if __name__ == "__main__":
    main()
