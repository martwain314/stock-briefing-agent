import cron from 'node-cron';
import { collectAll } from '../collectors';
import { collectAllNews } from '../collectors/news-collector';
import { generateBriefing, generateQuickAlert } from '../analyzer/briefing-engine';
import { sendBriefing, sendMessage } from '../bot/telegram-bot';
import { NewsArticle } from '../types';
import logger from '../utils/logger';

// ============================================
// 스케줄러 (정기 브리핑 + 실시간 모니터링)
// ============================================

/** 이전에 감지한 뉴스 제목 (중복 방지) */
const seenHeadlines = new Set<string>();

/** 중요 키워드 목록 (실시간 알림 트리거) */
const ALERT_KEYWORDS = [
  // 경제 이벤트
  '금리', '기준금리', '긴급', '폭락', '폭등', '서킷브레이커',
  '사이드카', '상한가', '하한가',
  // 정치/정책
  '계엄', '탄핵', '대통령', '비상', '전쟁',
  // 글로벌
  '연준', 'fed', '트럼프', '관세', '제재',
  // 산업
  '반도체', 'ai', '배터리', '원유',
];

/** 정기 브리핑 스케줄 시작 */
export function startScheduledBriefings(
  morningCron: string,
  eveningCron: string,
  watchlist: string[]
) {
  // 오전 브리핑
  cron.schedule(morningCron, async () => {
    logger.info('📅 오전 정기 브리핑 시작');
    try {
      const data = await collectAll(watchlist);
      const briefing = await generateBriefing(data, 'morning');
      await sendBriefing(briefing);
    } catch (error) {
      logger.error('오전 브리핑 실패', { error });
      await sendMessage('⚠️ 오전 브리핑 생성 실패. 로그를 확인하세요.');
    }
  }, { timezone: 'Asia/Seoul' });

  // 저녁 브리핑
  cron.schedule(eveningCron, async () => {
    logger.info('📅 저녁 정기 브리핑 시작');
    try {
      const data = await collectAll(watchlist);
      const briefing = await generateBriefing(data, 'evening');
      await sendBriefing(briefing);
    } catch (error) {
      logger.error('저녁 브리핑 실패', { error });
      await sendMessage('⚠️ 저녁 브리핑 생성 실패. 로그를 확인하세요.');
    }
  }, { timezone: 'Asia/Seoul' });

  logger.info(`정기 브리핑 스케줄 등록: 오전(${morningCron}), 저녁(${eveningCron})`);
}

/** 실시간 뉴스 모니터링 시작 */
export function startRealtimeMonitor(intervalMinutes: number) {
  // 첫 실행 시 기존 뉴스 제목을 수집 (알림 방지)
  initializeSeenHeadlines();

  const intervalMs = intervalMinutes * 60 * 1000;

  setInterval(async () => {
    try {
      logger.debug('실시간 뉴스 모니터링 중...');
      const news = await collectAllNews();
      await checkForAlerts(news);
    } catch (error) {
      logger.error('실시간 모니터링 오류', { error });
    }
  }, intervalMs);

  logger.info(`실시간 모니터링 시작 (${intervalMinutes}분 간격)`);
}

/** 초기 뉴스 수집 (기존 뉴스 중복 방지) */
async function initializeSeenHeadlines() {
  try {
    const news = await collectAllNews();
    for (const article of news) {
      seenHeadlines.add(article.title);
    }
    logger.info(`기존 뉴스 ${seenHeadlines.size}건 등록 (중복 방지)`);
  } catch (error) {
    logger.warn('초기 뉴스 수집 실패', { error });
  }
}

/** 새 뉴스 중 알림이 필요한 것 체크 */
async function checkForAlerts(news: NewsArticle[]) {
  for (const article of news) {
    // 이미 본 뉴스는 건너뛰기
    if (seenHeadlines.has(article.title)) continue;
    seenHeadlines.add(article.title);

    // seenHeadlines가 너무 커지지 않도록 관리 (최근 500개만 유지)
    if (seenHeadlines.size > 500) {
      const arr = Array.from(seenHeadlines);
      for (let i = 0; i < 100; i++) {
        seenHeadlines.delete(arr[i]);
      }
    }

    // 중요 키워드 매칭 체크
    const titleLower = article.title.toLowerCase();
    const matchedKeywords = ALERT_KEYWORDS.filter((kw) =>
      titleLower.includes(kw.toLowerCase())
    );

    if (matchedKeywords.length >= 1) {
      logger.info(`🚨 중요 뉴스 감지: ${article.title}`);

      try {
        const analysis = await generateQuickAlert(
          article.title,
          `출처: ${article.source}\n요약: ${article.summary}\n카테고리: ${article.category}`
        );

        const alertMessage =
          `🚨 *실시간 알림*\n\n` +
          `📰 *${article.title}*\n` +
          `출처: ${article.source}\n\n` +
          `${analysis}\n\n` +
          `🔗 [기사 원문](${article.url})`;

        await sendMessage(alertMessage);
      } catch (error) {
        // AI 분석 실패해도 기본 알림은 전송
        await sendMessage(
          `🚨 *실시간 알림*\n\n` +
            `📰 *${article.title}*\n` +
            `출처: ${article.source}\n` +
            `키워드: ${matchedKeywords.join(', ')}\n\n` +
            `🔗 [기사 원문](${article.url})`
        );
      }
    }
  }
}
