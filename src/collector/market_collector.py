"""
시장 데이터 수집 모듈

국내/해외 주요 지수, 환율, 경제 지표, 관심 종목 시세 수집
상태를 가지지 않으므로 모듈 함수로 구성
"""

import asyncio
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from src.common.types import EconomicIndicator, MarketData, WatchlistItem

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def _parse_change(text: str) -> tuple[float, float]:
    """변동폭 문자열에서 금액과 퍼센트를 파싱

    Args:
        text: 변동폭 문자열 (예: "▲ 15.30 +0.58%")

    Returns:
        (변동 금액, 변동 퍼센트) 튜플
    """
    import re

    numbers = re.findall(r"[\d,.]+", text)
    if not numbers:
        return 0.0, 0.0

    amount = float(numbers[0].replace(",", "")) if numbers else 0.0
    percent = float(numbers[1].replace(",", "")) if len(numbers) > 1 else 0.0

    is_negative = any(kw in text for kw in ["하락", "-", "▼"])
    if is_negative:
        amount = -amount
        percent = -percent

    return amount, percent


async def collect_market_indices() -> list[MarketData]:
    """국내 주요 지수(KOSPI, KOSDAQ)를 수집

    Returns:
        국내 주요 지수 데이터 목록
    """
    markets: list[MarketData] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://finance.naver.com/sise/",
                headers=_HEADERS,
            )
            response.raise_for_status()

        # 네이버 금융은 EUC-KR 인코딩
        content = response.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(content, "html.parser")

        # KOSPI
        kospi_now = soup.select_one("#KOSPI_now")
        kospi_change = soup.select_one("#KOSPI_change")
        if kospi_now:
            change_text = kospi_change.get_text(strip=True) if kospi_change else ""
            amount, percent = _parse_change(change_text)
            markets.append(
                MarketData(
                    name="KOSPI",
                    current_price=float(
                        kospi_now.get_text(strip=True).replace(",", "") or 0
                    ),
                    change_percent=percent,
                    change_amount=amount,
                    updated_at=datetime.now().isoformat(),
                )
            )

        # KOSDAQ
        kosdaq_now = soup.select_one("#KOSDAQ_now")
        kosdaq_change = soup.select_one("#KOSDAQ_change")
        if kosdaq_now:
            change_text = kosdaq_change.get_text(strip=True) if kosdaq_change else ""
            amount, percent = _parse_change(change_text)
            markets.append(
                MarketData(
                    name="KOSDAQ",
                    current_price=float(
                        kosdaq_now.get_text(strip=True).replace(",", "") or 0
                    ),
                    change_percent=percent,
                    change_amount=amount,
                    updated_at=datetime.now().isoformat(),
                )
            )

        logger.info(f"국내 지수 {len(markets)}개 수집")
    except Exception as e:
        logger.error(f"국내 지수 수집 실패: {e}")

    return markets


async def collect_global_indices() -> list[MarketData]:
    """해외 주요 지수를 수집

    Returns:
        해외 주요 지수 데이터 목록
    """
    markets: list[MarketData] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://finance.naver.com/world/",
                headers=_HEADERS,
            )
            response.raise_for_status()

        content = response.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(content, "html.parser")

        for tbody_class in ["America", "Asia", "Europe"]:
            tbody = soup.select_one(f"tbody.{tbody_class}")
            if not tbody:
                continue
            for row in tbody.select("tr"):
                cols = row.select("td")
                name_el = row.select_one("a")
                if not name_el or len(cols) < 4:
                    continue

                name = name_el.get_text(strip=True)
                price_text = cols[1].get_text(strip=True)
                change_text = cols[2].get_text(strip=True)
                percent_text = cols[3].get_text(strip=True)

                if name and price_text:
                    markets.append(
                        MarketData(
                            name=name,
                            current_price=float(price_text.replace(",", "") or 0),
                            change_amount=float(change_text.replace(",", "") or 0),
                            change_percent=float(
                                percent_text.replace("%", "").replace(",", "") or 0
                            ),
                            updated_at=datetime.now().isoformat(),
                        )
                    )

        logger.info(f"해외 지수 {len(markets)}개 수집")
    except Exception as e:
        logger.error(f"해외 지수 수집 실패: {e}")

    return markets[:10]


async def collect_economic_indicators() -> list[EconomicIndicator]:
    """환율/유가 등 주요 경제 지표를 수집

    Returns:
        경제 지표 데이터 목록
    """
    indicators: list[EconomicIndicator] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://finance.naver.com/marketindex/",
                headers=_HEADERS,
            )
            response.raise_for_status()

        content = response.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(content, "html.parser")

        for item in soup.select("div.market_data ul li"):
            name_el = item.select_one("a .h_lst span")
            value_el = item.select_one(".value")
            change_el = item.select_one(".change")

            name = name_el.get_text(strip=True) if name_el else ""
            value = value_el.get_text(strip=True) if value_el else ""
            change = change_el.get_text(strip=True) if change_el else ""

            if name and value:
                indicators.append(
                    EconomicIndicator(name=name, value=value, change=change)
                )

        # fallback: 대표 지표 영역
        if not indicators:
            for item in soup.select("div.head_info"):
                name_el = item.select_one("h3.lst_nm") or item.select_one(".h_lst span")
                value_el = item.select_one(".value")
                change_el = item.select_one(".change")

                name = name_el.get_text(strip=True) if name_el else ""
                value = value_el.get_text(strip=True) if value_el else ""
                change = change_el.get_text(strip=True) if change_el else ""

                if name and value:
                    indicators.append(
                        EconomicIndicator(name=name, value=value, change=change)
                    )

        logger.info(f"경제 지표 {len(indicators)}개 수집")
    except Exception as e:
        logger.error(f"경제 지표 수집 실패: {e}")

    return indicators


async def collect_watchlist(watchlist: list[str]) -> list[WatchlistItem]:
    """관심 종목 시세를 조회

    네이버 금융 검색 API로 종목 코드를 찾고 시세를 수집합니다.

    Args:
        watchlist: 관심 종목명 리스트

    Returns:
        관심 종목 시세 데이터 목록
    """
    items: list[WatchlistItem] = []

    async with httpx.AsyncClient(timeout=10) as client:
        for name in watchlist:
            try:
                # 종목 코드 검색
                search_url = (
                    f"https://ac.finance.naver.com/ac?"
                    f"q={name}&q_enc=euc-kr&st=111&frm=stock"
                    f"&r_format=json&r_enc=euc-kr&r_unicode=0&t_koreng=1&r_lt=111"
                )
                search_response = await client.get(search_url)
                search_data = search_response.json()

                code = ""
                if search_data.get("items") and search_data["items"][0]:
                    code = search_data["items"][0][0][0]

                if not code:
                    logger.warning(f"종목 코드를 찾을 수 없음: {name}")
                    continue

                # 시세 조회
                price_url = f"https://finance.naver.com/item/main.naver?code={code}"
                price_response = await client.get(price_url, headers=_HEADERS)
                price_content = price_response.content.decode(
                    "euc-kr", errors="replace"
                )
                soup = BeautifulSoup(price_content, "html.parser")

                price_el = soup.select_one("p.no_today .blind")
                change_el = soup.select_one("p.no_exday .blind")

                price_text = price_el.get_text(strip=True) if price_el else "0"
                change_text = change_el.get_text(strip=True) if change_el else "0"

                price = float(price_text.replace(",", "") or 0)
                change_amount = float(change_text.replace(",", "") or 0)
                change_percent = (
                    round((change_amount / (price - change_amount)) * 100, 2)
                    if price > 0 and price != change_amount
                    else 0.0
                )

                items.append(
                    WatchlistItem(
                        name=name,
                        code=code,
                        price=price,
                        change_percent=change_percent,
                        change_amount=change_amount,
                    )
                )
                logger.debug(f"{name}({code}): {price:,.0f}원")

            except Exception as e:
                logger.warning(f"관심종목 시세 조회 실패: {name} - {e}")

    logger.info(f"관심 종목 {len(items)}/{len(watchlist)}개 시세 수집")
    return items


async def collect_all_market_data(
    watchlist: list[str],
) -> tuple[list[MarketData], list[EconomicIndicator], list[WatchlistItem]]:
    """시장 관련 전체 데이터를 병렬로 수집

    Args:
        watchlist: 관심 종목명 리스트

    Returns:
        (시장 지수 목록, 경제 지표 목록, 관심 종목 시세 목록) 튜플
    """
    domestic, global_indices, indicators, watchlist_items = await asyncio.gather(
        collect_market_indices(),
        collect_global_indices(),
        collect_economic_indicators(),
        collect_watchlist(watchlist),
    )

    all_markets = [*domestic, *global_indices]
    return all_markets, indicators, watchlist_items
