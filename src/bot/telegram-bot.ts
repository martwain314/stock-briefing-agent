import TelegramBot from 'node-telegram-bot-api';
import logger from '../utils/logger';
import { collectAll } from '../collectors';
import { generateBriefing, generateQuickAlert } from '../analyzer/briefing-engine';
import { BriefingResult } from '../types';

// ============================================
// 텔레그램 봇
// ============================================

let bot: TelegramBot;
let chatId: string;
let watchlist: string[];

export function initTelegramBot(
  token: string,
  targetChatId: string,
  watchlistItems: string[]
) {
  bot = new TelegramBot(token, { polling: true });
  chatId = targetChatId;
  watchlist = watchlistItems;

  registerCommands();
  logger.info('텔레그램 봇 초기화 완료');
}

/** 텔레그램 명령어 등록 */
function registerCommands() {
  // /start - 봇 시작
  bot.onText(/\/start/, async (msg) => {
    if (!isAuthorized(msg)) return;
    await sendMessage(
      `🤖 *투자 브리핑 에이전트 활성화*\n\n` +
        `사용 가능한 명령어:\n` +
        `/brief - 즉시 브리핑 받기\n` +
        `/market - 현재 시장 현황\n` +
        `/watchlist - 관심 종목 시세\n` +
        `/add [종목명] - 관심 종목 추가\n` +
        `/remove [종목명] - 관심 종목 제거\n` +
        `/list - 관심 종목 목록\n` +
        `/ask [질문] - AI에게 투자 관련 질문\n` +
        `/help - 도움말`
    );
  });

  // /brief - 즉시 브리핑
  bot.onText(/\/brief/, async (msg) => {
    if (!isAuthorized(msg)) return;
    await sendMessage('📡 데이터 수집 중... 잠시만 기다려주세요.');

    try {
      const data = await collectAll(watchlist);
      const briefing = await generateBriefing(data, 'on-demand');
      await sendBriefing(briefing);
    } catch (error) {
      logger.error('즉시 브리핑 실패', { error });
      await sendMessage('⚠️ 브리핑 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    }
  });

  // /market - 시장 현황
  bot.onText(/\/market/, async (msg) => {
    if (!isAuthorized(msg)) return;
    await sendMessage('📊 시장 데이터 조회 중...');

    try {
      const data = await collectAll(watchlist);
      let message = '📊 *현재 시장 현황*\n\n';

      for (const m of data.markets) {
        const emoji = m.changePercent >= 0 ? '🔴' : '🔵';
        const sign = m.changePercent >= 0 ? '+' : '';
        message += `${emoji} *${m.name}*: ${m.currentPrice.toLocaleString()} (${sign}${m.changePercent}%)\n`;
      }

      if (data.indicators.length > 0) {
        message += '\n💹 *주요 지표*\n';
        for (const ind of data.indicators) {
          message += `  ${ind.name}: ${ind.value} ${ind.change || ''}\n`;
        }
      }

      await sendMessage(message);
    } catch (error) {
      logger.error('시장 현황 조회 실패', { error });
      await sendMessage('⚠️ 시장 데이터 조회 실패');
    }
  });

  // /watchlist - 관심 종목 시세
  bot.onText(/\/watchlist/, async (msg) => {
    if (!isAuthorized(msg)) return;

    try {
      const { collectWatchlist: getWatchlist } = await import('../collectors/market-collector');
      const items = await getWatchlist(watchlist);

      let message = '📋 *관심 종목 현황*\n\n';
      for (const item of items) {
        const emoji = item.changePercent >= 0 ? '📈' : '📉';
        const sign = item.changePercent >= 0 ? '+' : '';
        message += `${emoji} *${item.name}*\n`;
        message += `   ${item.price.toLocaleString()}원 (${sign}${item.changePercent}%)\n\n`;
      }

      await sendMessage(message);
    } catch (error) {
      logger.error('관심종목 조회 실패', { error });
      await sendMessage('⚠️ 관심 종목 조회 실패');
    }
  });

  // /add [종목명] - 관심 종목 추가
  bot.onText(/\/add (.+)/, async (msg, match) => {
    if (!isAuthorized(msg)) return;
    const name = match?.[1]?.trim();
    if (!name) return;

    if (!watchlist.includes(name)) {
      watchlist.push(name);
      await sendMessage(`✅ *${name}*이(가) 관심 종목에 추가되었습니다.\n현재 관심 종목: ${watchlist.join(', ')}`);
    } else {
      await sendMessage(`ℹ️ *${name}*은(는) 이미 관심 종목에 있습니다.`);
    }
  });

  // /remove [종목명] - 관심 종목 제거
  bot.onText(/\/remove (.+)/, async (msg, match) => {
    if (!isAuthorized(msg)) return;
    const name = match?.[1]?.trim();
    if (!name) return;

    const idx = watchlist.indexOf(name);
    if (idx >= 0) {
      watchlist.splice(idx, 1);
      await sendMessage(`🗑️ *${name}*이(가) 관심 종목에서 제거되었습니다.\n현재 관심 종목: ${watchlist.join(', ')}`);
    } else {
      await sendMessage(`ℹ️ *${name}*은(는) 관심 종목에 없습니다.`);
    }
  });

  // /list - 관심 종목 목록
  bot.onText(/\/list/, async (msg) => {
    if (!isAuthorized(msg)) return;
    if (watchlist.length === 0) {
      await sendMessage('📋 관심 종목이 없습니다. /add [종목명]으로 추가하세요.');
    } else {
      await sendMessage(`📋 *관심 종목 목록*\n\n${watchlist.map((w, i) => `${i + 1}. ${w}`).join('\n')}`);
    }
  });

  // /ask [질문] - AI에게 질문
  bot.onText(/\/ask (.+)/, async (msg, match) => {
    if (!isAuthorized(msg)) return;
    const question = match?.[1]?.trim();
    if (!question) return;

    await sendMessage('🤔 분석 중...');

    try {
      const answer = await generateQuickAlert(question, '사용자의 투자 관련 질문');
      await sendMessage(`💡 *AI 답변*\n\n${answer}`);
    } catch (error) {
      logger.error('AI 질문 응답 실패', { error });
      await sendMessage('⚠️ AI 응답 생성 실패');
    }
  });

  // /help - 도움말
  bot.onText(/\/help/, async (msg) => {
    if (!isAuthorized(msg)) return;
    await sendMessage(
      `📖 *도움말*\n\n` +
        `🔹 /brief - 지금 바로 전체 브리핑\n` +
        `🔹 /market - 주요 지수/지표 현황\n` +
        `🔹 /watchlist - 관심 종목 시세\n` +
        `🔹 /add [종목명] - 관심 종목 추가\n` +
        `🔹 /remove [종목명] - 관심 종목 제거\n` +
        `🔹 /list - 관심 종목 목록 보기\n` +
        `🔹 /ask [질문] - AI에게 투자 관련 질문\n\n` +
        `⏰ 자동 브리핑: 평일 오전 8시, 오후 6시\n` +
        `🔔 실시간 모니터링: 30분 간격으로 중요 뉴스 감지`
    );
  });

  logger.info('텔레그램 명령어 등록 완료');
}

/** 인가된 사용자인지 확인 */
function isAuthorized(msg: TelegramBot.Message): boolean {
  const msgChatId = msg.chat.id.toString();
  if (msgChatId !== chatId) {
    logger.warn(`미인가 접근: ${msgChatId}`);
    return false;
  }
  return true;
}

/** 텔레그램 메시지 발송 */
export async function sendMessage(text: string): Promise<void> {
  try {
    // 텔레그램 메시지 길이 제한 (4096자)
    if (text.length > 4000) {
      // 긴 메시지는 분할 전송
      const chunks = splitMessage(text, 4000);
      for (const chunk of chunks) {
        await bot.sendMessage(chatId, chunk, { parse_mode: 'Markdown' });
      }
    } else {
      await bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
    }
  } catch (error) {
    // Markdown 파싱 실패 시 일반 텍스트로 재시도
    try {
      await bot.sendMessage(chatId, text);
    } catch (retryError) {
      logger.error('텔레그램 메시지 전송 실패', { retryError });
    }
  }
}

/** 브리핑 결과를 텔레그램으로 전송 */
export async function sendBriefing(briefing: BriefingResult): Promise<void> {
  const sentimentEmoji =
    briefing.sentiment === 'bullish'
      ? '🟢'
      : briefing.sentiment === 'bearish'
        ? '🔴'
        : '🟡';

  const header =
    briefing.type === 'morning'
      ? '☀️ 오전 장전 브리핑'
      : briefing.type === 'evening'
        ? '🌙 장마감 리뷰'
        : briefing.type === 'alert'
          ? '🚨 긴급 알림'
          : '📋 투자 브리핑';

  const message = `${header} ${sentimentEmoji}\n${'─'.repeat(20)}\n\n${briefing.content}`;

  await sendMessage(message);
  logger.info(`브리핑 전송 완료 (${briefing.type})`);
}

/** 긴 메시지 분할 */
function splitMessage(text: string, maxLength: number): string[] {
  const chunks: string[] = [];
  let current = '';

  const lines = text.split('\n');
  for (const line of lines) {
    if ((current + '\n' + line).length > maxLength) {
      if (current) chunks.push(current);
      current = line;
    } else {
      current = current ? current + '\n' + line : line;
    }
  }
  if (current) chunks.push(current);

  return chunks;
}

export function getBot(): TelegramBot {
  return bot;
}
