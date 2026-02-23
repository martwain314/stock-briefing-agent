// ============================================
// 공통 타입 정의
// ============================================

/** 뉴스 기사 */
export interface NewsArticle {
  title: string;
  summary: string;
  url: string;
  source: string;
  publishedAt: string;
  category: NewsCategory;
}

export type NewsCategory =
  | 'economy'      // 경제
  | 'politics'     // 정치
  | 'market'       // 시장
  | 'industry'     // 산업/업종
  | 'global'       // 해외
  | 'policy'       // 정책/규제
  | 'trend';       // 트렌드

/** 시장 데이터 */
export interface MarketData {
  name: string;
  currentPrice: number;
  changePercent: number;
  changeAmount: number;
  volume?: number;
  updatedAt: string;
}

/** 관심 종목 시세 */
export interface WatchlistItem {
  name: string;
  code?: string;
  price: number;
  changePercent: number;
  changeAmount: number;
}

/** 주요 경제 지표 */
export interface EconomicIndicator {
  name: string;
  value: string;
  change?: string;
  description?: string;
}

/** 수집된 전체 데이터 */
export interface CollectedData {
  news: NewsArticle[];
  markets: MarketData[];
  watchlist: WatchlistItem[];
  indicators: EconomicIndicator[];
  collectedAt: string;
}

/** AI 브리핑 결과 */
export interface BriefingResult {
  type: 'morning' | 'evening' | 'alert' | 'on-demand';
  content: string;
  highlights: string[];
  sentiment: 'bullish' | 'bearish' | 'neutral';
  generatedAt: string;
}

/** 실시간 알림 */
export interface AlertEvent {
  type: 'breaking_news' | 'price_spike' | 'volume_surge' | 'policy_change';
  title: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  relatedAssets?: string[];
  detectedAt: string;
}

/** 앱 설정 */
export interface AppConfig {
  anthropicApiKey: string;
  telegramBotToken: string;
  telegramChatId: string;
  morningBriefCron: string;
  eveningBriefCron: string;
  monitorIntervalMinutes: number;
  watchlist: string[];
  logLevel: string;
}
