import dotenv from 'dotenv';
dotenv.config();

import { AppConfig } from './types';
import { initAnalyzer } from './analyzer/briefing-engine';
import { initTelegramBot, sendMessage } from './bot/telegram-bot';
import { startScheduledBriefings, startRealtimeMonitor } from './scheduler';
import logger from './utils/logger';

// ============================================
// Stock Briefing Agent - 메인 엔트리포인트
// ============================================

function loadConfig(): AppConfig {
  const required = ['ANTHROPIC_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'];
  for (const key of required) {
    if (!process.env[key]) {
      throw new Error(`필수 환경 변수 ${key}가 설정되지 않았습니다. .env 파일을 확인하세요.`);
    }
  }

  return {
    anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
    telegramBotToken: process.env.TELEGRAM_BOT_TOKEN!,
    telegramChatId: process.env.TELEGRAM_CHAT_ID!,
    morningBriefCron: process.env.MORNING_BRIEF_CRON || '0 8 * * 1-5',
    eveningBriefCron: process.env.EVENING_BRIEF_CRON || '0 18 * * 1-5',
    monitorIntervalMinutes: parseInt(process.env.MONITOR_INTERVAL_MINUTES || '30', 10),
    watchlist: (process.env.WATCHLIST || 'KODEX 200,TIGER 나스닥100')
      .split(',')
      .map((s) => s.trim()),
    logLevel: process.env.LOG_LEVEL || 'info',
  };
}

async function main() {
  console.log(`
  ╔══════════════════════════════════════════╗
  ║   📊 Stock Briefing Agent v1.0.0        ║
  ║   AI 투자 브리핑 텔레그램 봇             ║
  ╚══════════════════════════════════════════╝
  `);

  try {
    // 1. 설정 로드
    const config = loadConfig();
    logger.info('설정 로드 완료');
    logger.info(`관심 종목: ${config.watchlist.join(', ')}`);

    // 2. AI 분석 엔진 초기화
    initAnalyzer(config.anthropicApiKey);

    // 3. 텔레그램 봇 초기화
    initTelegramBot(config.telegramBotToken, config.telegramChatId, config.watchlist);

    // 4. 정기 브리핑 스케줄 시작
    startScheduledBriefings(
      config.morningBriefCron,
      config.eveningBriefCron,
      config.watchlist
    );

    // 5. 실시간 모니터링 시작
    startRealtimeMonitor(config.monitorIntervalMinutes);

    // 6. 시작 알림 전송
    await sendMessage(
      `🤖 *투자 브리핑 에이전트 시작*\n\n` +
        `⏰ 오전 브리핑: 평일 ${config.morningBriefCron}\n` +
        `⏰ 저녁 브리핑: 평일 ${config.eveningBriefCron}\n` +
        `🔔 실시간 모니터링: ${config.monitorIntervalMinutes}분 간격\n` +
        `📋 관심 종목: ${config.watchlist.join(', ')}\n\n` +
        `/brief 명령어로 즉시 브리핑을 받을 수 있습니다.`
    );

    logger.info('🚀 Stock Briefing Agent 시작 완료!');

    // 프로세스 종료 처리
    process.on('SIGINT', async () => {
      logger.info('종료 신호 수신...');
      await sendMessage('🔴 투자 브리핑 에이전트가 종료됩니다.');
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logger.info('종료 신호 수신...');
      await sendMessage('🔴 투자 브리핑 에이전트가 종료됩니다.');
      process.exit(0);
    });
  } catch (error) {
    logger.error('에이전트 시작 실패', { error });
    process.exit(1);
  }
}

main();
