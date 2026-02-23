import axios from 'axios';
import * as cheerio from 'cheerio';
import { MarketData, EconomicIndicator, WatchlistItem } from '../types';
import logger from '../utils/logger';

// ============================================
// 시장 데이터 수집기
// ============================================

/** 주요 지수 수집 (네이버 증권) */
export async function collectMarketIndices(): Promise<MarketData[]> {
  try {
    const url = 'https://finance.naver.com/sise/';
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      timeout: 10000,
      responseType: 'arraybuffer',
    });

    // 네이버 금융은 EUC-KR 인코딩
    const decoded = new TextDecoder('euc-kr').decode(data);
    const $ = cheerio.load(decoded);

    const markets: MarketData[] = [];

    // KOSPI
    const kospiPrice = $('#KOSPI_now').text().trim();
    const kospiChange = $('#KOSPI_change').text().trim();
    if (kospiPrice) {
      const parsed = parseChange(kospiChange);
      markets.push({
        name: 'KOSPI',
        currentPrice: parseFloat(kospiPrice.replace(/,/g, '')) || 0,
        changePercent: parsed.percent,
        changeAmount: parsed.amount,
        updatedAt: new Date().toISOString(),
      });
    }

    // KOSDAQ
    const kosdaqPrice = $('#KOSDAQ_now').text().trim();
    const kosdaqChange = $('#KOSDAQ_change').text().trim();
    if (kosdaqPrice) {
      const parsed = parseChange(kosdaqChange);
      markets.push({
        name: 'KOSDAQ',
        currentPrice: parseFloat(kosdaqPrice.replace(/,/g, '')) || 0,
        changePercent: parsed.percent,
        changeAmount: parsed.amount,
        updatedAt: new Date().toISOString(),
      });
    }

    logger.info(`국내 지수 ${markets.length}개 수집`);
    return markets;
  } catch (error) {
    logger.error('국내 지수 수집 실패', { error });
    return [];
  }
}

/** 해외 주요 지수 수집 */
export async function collectGlobalIndices(): Promise<MarketData[]> {
  try {
    const url = 'https://finance.naver.com/world/';
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      timeout: 10000,
      responseType: 'arraybuffer',
    });

    const decoded = new TextDecoder('euc-kr').decode(data);
    const $ = cheerio.load(decoded);

    const markets: MarketData[] = [];

    // 주요 글로벌 지수 (네이버 해외증시 페이지에서)
    $('tbody.America tr, tbody.Asia tr, tbody.Europe tr').each((_, el) => {
      const name = $(el).find('a').first().text().trim();
      const priceText = $(el).find('td').eq(1).text().trim();
      const changeText = $(el).find('td').eq(2).text().trim();
      const percentText = $(el).find('td').eq(3).text().trim();

      if (name && priceText) {
        markets.push({
          name,
          currentPrice: parseFloat(priceText.replace(/,/g, '')) || 0,
          changeAmount: parseFloat(changeText.replace(/,/g, '')) || 0,
          changePercent: parseFloat(percentText.replace(/[%,]/g, '')) || 0,
          updatedAt: new Date().toISOString(),
        });
      }
    });

    logger.info(`해외 지수 ${markets.length}개 수집`);
    return markets.slice(0, 10);
  } catch (error) {
    logger.error('해외 지수 수집 실패', { error });
    return [];
  }
}

/** 환율/유가 등 주요 경제 지표 수집 */
export async function collectEconomicIndicators(): Promise<EconomicIndicator[]> {
  try {
    const url = 'https://finance.naver.com/marketindex/';
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      timeout: 10000,
      responseType: 'arraybuffer',
    });

    const decoded = new TextDecoder('euc-kr').decode(data);
    const $ = cheerio.load(decoded);

    const indicators: EconomicIndicator[] = [];

    // 주요 시장 지표 (환율, 유가, 금)
    $('div.market_data ul li').each((_, el) => {
      const name = $(el).find('a .h_lst span').text().trim();
      const value = $(el).find('.value').text().trim();
      const change = $(el).find('.change').text().trim();

      if (name && value) {
        indicators.push({
          name,
          value,
          change,
        });
      }
    });

    // 기본 지표가 없으면 fallback
    if (indicators.length === 0) {
      // 간단한 fallback: 대표적인 지표들
      const items = $('div.head_info');
      items.each((_, el) => {
        const name = $(el).find('h3.lst_nm').text().trim() || $(el).find('.h_lst span').text().trim();
        const value = $(el).find('.value').text().trim();
        const change = $(el).find('.change').text().trim();
        if (name && value) {
          indicators.push({ name, value, change });
        }
      });
    }

    logger.info(`경제 지표 ${indicators.length}개 수집`);
    return indicators;
  } catch (error) {
    logger.error('경제 지표 수집 실패', { error });
    return [];
  }
}

/** 관심 종목 시세 조회 (네이버 금융 검색) */
export async function collectWatchlist(watchlist: string[]): Promise<WatchlistItem[]> {
  const items: WatchlistItem[] = [];

  for (const name of watchlist) {
    try {
      // 네이버 금융 검색 API로 종목 코드 찾기
      const searchUrl = `https://ac.finance.naver.com/ac?q=${encodeURIComponent(name)}&q_enc=euc-kr&st=111&frm=stock&r_format=json&r_enc=euc-kr&r_unicode=0&t_koreng=1&r_lt=111`;
      const { data: searchData } = await axios.get(searchUrl, { timeout: 5000 });

      let code = '';
      if (searchData?.items?.[0]?.[0]?.[0]) {
        code = searchData.items[0][0][0]; // 종목코드 추출
      }

      if (!code) {
        logger.warn(`종목 코드를 찾을 수 없음: ${name}`);
        continue;
      }

      // 종목 시세 조회
      const priceUrl = `https://finance.naver.com/item/main.naver?code=${code}`;
      const { data: priceData } = await axios.get(priceUrl, {
        timeout: 10000,
        responseType: 'arraybuffer',
      });

      const decoded = new TextDecoder('euc-kr').decode(priceData);
      const $ = cheerio.load(decoded);

      const priceText = $('p.no_today .blind').first().text().trim();
      const changeText = $('p.no_exday .blind').first().text().trim();

      const price = parseFloat(priceText.replace(/,/g, '')) || 0;
      const changeAmount = parseFloat(changeText.replace(/,/g, '')) || 0;
      const changePercent = price > 0 ? (changeAmount / (price - changeAmount)) * 100 : 0;

      items.push({
        name,
        code,
        price,
        changePercent: Math.round(changePercent * 100) / 100,
        changeAmount,
      });

      logger.debug(`${name}(${code}): ${price.toLocaleString()}원`);
    } catch (error) {
      logger.warn(`관심종목 시세 조회 실패: ${name}`, { error });
    }
  }

  logger.info(`관심 종목 ${items.length}/${watchlist.length}개 시세 수집`);
  return items;
}

/** 변동폭 문자열 파싱 */
function parseChange(text: string): { amount: number; percent: number } {
  const numbers = text.match(/[\d,.]+/g);
  if (!numbers || numbers.length === 0) return { amount: 0, percent: 0 };

  const amount = parseFloat(numbers[0]?.replace(/,/g, '') || '0');
  const percent = numbers.length > 1 ? parseFloat(numbers[1]?.replace(/,/g, '') || '0') : 0;
  const isNegative = text.includes('하락') || text.includes('-') || text.includes('▼');

  return {
    amount: isNegative ? -amount : amount,
    percent: isNegative ? -percent : percent,
  };
}
