import { collectAllNews } from './news-collector';
import {
  collectMarketIndices,
  collectGlobalIndices,
  collectEconomicIndicators,
  collectWatchlist,
} from './market-collector';
import { CollectedData } from '../types';
import logger from '../utils/logger';

// ============================================
// 데이터 수집 오케스트레이터
// ============================================

/** 전체 데이터 수집 (브리핑용) */
export async function collectAll(watchlist: string[]): Promise<CollectedData> {
  logger.info('===== 전체 데이터 수집 시작 =====');
  const startTime = Date.now();

  const [news, domesticMarkets, globalMarkets, indicators, watchlistItems] =
    await Promise.all([
      collectAllNews(),
      collectMarketIndices(),
      collectGlobalIndices(),
      collectEconomicIndicators(),
      collectWatchlist(watchlist),
    ]);

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  logger.info(`===== 데이터 수집 완료 (${elapsed}초) =====`);

  return {
    news,
    markets: [...domesticMarkets, ...globalMarkets],
    watchlist: watchlistItems,
    indicators,
    collectedAt: new Date().toISOString(),
  };
}

export { collectAllNews } from './news-collector';
export {
  collectMarketIndices,
  collectGlobalIndices,
  collectEconomicIndicators,
  collectWatchlist,
} from './market-collector';
