import dotenv from 'dotenv';
dotenv.config();

import { collectAll } from '../collectors';
import { initAnalyzer, generateBriefing } from '../analyzer/briefing-engine';
import logger from '../utils/logger';

// ============================================
// 즉시 브리핑 CLI 명령어
// 사용법: npm run brief
// ============================================

async function briefNow() {
  console.log('📡 데이터 수집 중...\n');

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error('❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.');
    process.exit(1);
  }

  const watchlist = (process.env.WATCHLIST || 'KODEX 200,TIGER 나스닥100')
    .split(',')
    .map((s) => s.trim());

  initAnalyzer(apiKey);

  try {
    const data = await collectAll(watchlist);

    console.log(`✅ 수집 완료: 뉴스 ${data.news.length}건, 지수 ${data.markets.length}개, 종목 ${data.watchlist.length}개\n`);
    console.log('🤖 AI 브리핑 생성 중...\n');

    const briefing = await generateBriefing(data, 'on-demand');

    console.log('═'.repeat(50));
    console.log(briefing.content);
    console.log('═'.repeat(50));
    console.log(`\n심리: ${briefing.sentiment} | 생성: ${briefing.generatedAt}`);
  } catch (error) {
    logger.error('브리핑 생성 실패', { error });
    console.error('❌ 브리핑 생성 실패:', error);
  }

  process.exit(0);
}

briefNow();
