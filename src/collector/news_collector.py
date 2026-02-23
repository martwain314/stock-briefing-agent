"""
뉴스 수집 모듈

네이버 경제/정치 뉴스 크롤링 및 글로벌 RSS 피드 수집
상태를 가지지 않으므로 모듈 함수로 구성
"""

import asyncio
from datetime import datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from src.common.types import NewsArticle

# 뉴스 카테고리 분류용 키워드 매핑
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "policy": ["금리", "기준금리", "한은", "연준", "fed", "통화정책", "인플레"],
    "politics": ["국회", "대통령", "정부", "총리", "외교", "북한", "선거"],
    "industry": ["반도체", "ai", "배터리", "자동차", "it", "테크", "기술"],
    "market": ["코스피", "코스닥", "나스닥", "s&p", "dow", "증시", "주가"],
    "global": ["미국", "중국", "일본", "유럽", "글로벌", "세계"],
    "trend": ["트렌드", "mz", "소비", "유행"],
}

# 글로벌 RSS 피드 소스
_RSS_FEEDS = [
    {
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "source": "BBC Business",
        "category": "global",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
        "source": "NYT Economy",
        "category": "global",
    },
    {
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
        "source": "CNBC",
        "category": "global",
    },
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def _categorize_news(text: str) -> str:
    """뉴스 제목+내용으로 카테고리를 자동 분류

    Args:
        text: 분류할 텍스트 (제목 + 요약)

    Returns:
        뉴스 카테고리 문자열
    """
    lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "economy"


async def _fetch_naver_section_news(
    section_id: str, section_name: str, default_category: str
) -> list[NewsArticle]:
    """네이버 뉴스 특정 섹션의 헤드라인을 크롤링

    Args:
        section_id: 네이버 뉴스 섹션 ID (100=정치, 101=경제)
        section_name: 섹션 표시 이름
        default_category: 분류 실패 시 기본 카테고리

    Returns:
        수집된 뉴스 기사 목록
    """
    url = f"https://news.naver.com/section/{section_id}"
    articles: list[NewsArticle] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=_HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for item in soup.select("div.sa_text"):
            title_el = item.select_one("a.sa_text_title")
            if not title_el:
                continue

            strong = title_el.select_one("strong")
            title = strong.get_text(strip=True) if strong else ""
            href = title_el.get("href", "")
            lede = item.select_one("div.sa_text_lede")
            summary = lede.get_text(strip=True)[:200] if lede else ""

            if title:
                category = (
                    default_category
                    if default_category == "politics"
                    else _categorize_news(f"{title} {summary}")
                )
                articles.append(
                    NewsArticle(
                        title=title,
                        summary=summary,
                        url=str(href),
                        source=f"네이버 {section_name}",
                        published_at=datetime.now().isoformat(),
                        category=category,
                    )
                )

        logger.info(f"네이버 {section_name} 뉴스 {len(articles)}건 수집")
    except Exception as e:
        logger.error(f"네이버 {section_name} 뉴스 수집 실패: {e}")

    return articles[:15]


async def _fetch_rss_news() -> list[NewsArticle]:
    """RSS 피드에서 글로벌 경제 뉴스를 수집

    Returns:
        수집된 글로벌 뉴스 기사 목록
    """
    articles: list[NewsArticle] = []

    for feed_config in _RSS_FEEDS:
        try:
            parsed = await asyncio.to_thread(feedparser.parse, feed_config["url"])
            entries = parsed.entries[:5]

            for entry in entries:
                articles.append(
                    NewsArticle(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", "")[:200],
                        url=entry.get("link", ""),
                        source=feed_config["source"],
                        published_at=entry.get("published", datetime.now().isoformat()),
                        category=feed_config["category"],
                    )
                )

            logger.debug(f"{feed_config['source']}에서 {len(entries)}건 수집")
        except Exception as e:
            logger.warning(f"RSS 수집 실패: {feed_config['source']} - {e}")

    return articles


async def collect_all_news() -> list[NewsArticle]:
    """전체 뉴스를 수집하고 중복을 제거

    네이버 경제/정치 뉴스와 글로벌 RSS 피드를 병렬로 수집합니다.

    Returns:
        중복 제거된 전체 뉴스 기사 목록
    """
    logger.info("뉴스 수집 시작...")

    economy_news, politics_news, rss_news = await asyncio.gather(
        _fetch_naver_section_news("101", "경제", "economy"),
        _fetch_naver_section_news("100", "정치", "politics"),
        _fetch_rss_news(),
    )

    all_news = [*economy_news, *politics_news, *rss_news]

    # 중복 제거 (제목 앞 30자 기준)
    seen: set[str] = set()
    unique: list[NewsArticle] = []
    for article in all_news:
        key = article.title[:30]
        if key not in seen:
            seen.add(key)
            unique.append(article)

    logger.info(f"총 {len(unique)}건 뉴스 수집 완료")
    return unique
