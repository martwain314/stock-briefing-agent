import Anthropic from '@anthropic-ai/sdk';
import { CollectedData, BriefingResult } from '../types';
import logger from '../utils/logger';

// ============================================
// AI 브리핑 엔진 (Claude API)
// ============================================

let client: Anthropic;

export function initAnalyzer(apiKey: string) {
  client = new Anthropic({ apiKey });
  logger.info('Claude AI 분석 엔진 초기화 완료');
}

/** 수집된 데이터를 기반으로 브리핑 생성 */
export async function generateBriefing(
  data: CollectedData,
  type: BriefingResult['type']
): Promise<BriefingResult> {
  if (!client) throw new Error('분석 엔진이 초기화되지 않았습니다');

  const now = new Date();
  const timeLabel =
    type === 'morning'
      ? '오전 장전 브리핑'
      : type === 'evening'
        ? '장마감 리뷰'
        : type === 'alert'
          ? '긴급 알림'
          : '요약 브리핑';

  const dataContext = formatDataForPrompt(data);

  const systemPrompt = `당신은 개인 투자자를 위한 전문 투자 브리핑 비서입니다.
  
역할:
- 수집된 경제/정치/시장 데이터를 분석하여 투자에 영향을 미치는 핵심 인사이트를 제공합니다
- ETF와 개별 주식 투자자 관점에서 실용적인 정보를 전달합니다
- 한국어로 간결하고 명확하게 브리핑합니다

브리핑 원칙:
1. 핵심 먼저: 가장 중요한 정보를 맨 앞에
2. 투자 영향도 중심: "이 뉴스가 시장에 어떤 영향을 주는가"를 항상 분석
3. 섹터/업종 연결: 뉴스가 어떤 섹터/ETF에 영향을 주는지 연결
4. 감성 편향 배제: 사실 기반 중립적 분석, 과도한 낙관/비관 금지
5. 실행 가능한 인사이트: 단순 정보 나열이 아닌, "그래서 어떻게 해야 하는가"

출력 형식 (텔레그램 메시지):
- 이모지를 활용하여 가독성 확보
- 섹션별로 구분하여 읽기 쉽게
- 핵심 포인트는 불릿으로 정리
- 너무 길지 않게 (텔레그램 메시지 1개에 들어갈 분량)`;

  const userPrompt = `현재 시간: ${now.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}
브리핑 유형: ${timeLabel}

===== 수집된 데이터 =====
${dataContext}
===========================

위 데이터를 기반으로 ${timeLabel}을 작성해주세요.

다음 구조로 브리핑을 작성하세요:

1. 📊 시장 현황 (주요 지수 및 변동)
2. 📰 오늘의 핵심 뉴스 (투자 영향도 높은 뉴스 3-5개, 각각 시장 영향 분석 포함)
3. 🌍 글로벌 이슈 (해외 시장 및 국제 정세 중 투자 관련)
4. 🏛️ 정치/정책 동향 (시장에 영향 줄 수 있는 정치적 이슈)
5. 💡 투자 인사이트 (위 정보를 종합한 실행 가능한 제안)
6. 📋 관심 종목 현황 (관심 종목 시세 요약)

마지막에 전체 시장 심리를 한 줄로 요약해주세요 (예: "전반적으로 관망세, 반도체 섹터 주목 필요").`;

  try {
    logger.info(`AI 브리핑 생성 중... (${timeLabel})`);

    const response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 2000,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    });

    const content =
      response.content[0].type === 'text' ? response.content[0].text : '';

    // 하이라이트 추출 (핵심 포인트들)
    const highlights = extractHighlights(content);

    // 전반적 심리 판단
    const sentiment = detectSentiment(content);

    logger.info(`AI 브리핑 생성 완료 (${content.length}자)`);

    return {
      type,
      content,
      highlights,
      sentiment,
      generatedAt: new Date().toISOString(),
    };
  } catch (error) {
    logger.error('AI 브리핑 생성 실패', { error });
    throw error;
  }
}

/** 실시간 알림용 빠른 분석 */
export async function generateQuickAlert(
  headline: string,
  context: string
): Promise<string> {
  if (!client) throw new Error('분석 엔진이 초기화되지 않았습니다');

  try {
    const response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 500,
      system:
        '투자자를 위한 빠른 뉴스 분석 비서입니다. 핵심만 간결하게 전달하세요. 한국어로 답변하세요.',
      messages: [
        {
          role: 'user',
          content: `속보/중요 뉴스가 감지되었습니다:

제목: ${headline}
맥락: ${context}

다음을 간결하게 분석해주세요:
1. 핵심 내용 (1-2줄)
2. 시장 영향 (상승/하락/중립)
3. 영향 받는 섹터/종목
4. 투자자 대응 제안 (1줄)`,
        },
      ],
    });

    return response.content[0].type === 'text' ? response.content[0].text : '';
  } catch (error) {
    logger.error('빠른 분석 실패', { error });
    return `⚠️ 알림: ${headline}\n(AI 분석 일시적 오류)`;
  }
}

/** 수집된 데이터를 프롬프트용 텍스트로 포맷 */
function formatDataForPrompt(data: CollectedData): string {
  const sections: string[] = [];

  // 시장 지수
  if (data.markets.length > 0) {
    sections.push('[ 시장 지수 ]');
    for (const m of data.markets) {
      const sign = m.changePercent >= 0 ? '+' : '';
      sections.push(
        `  ${m.name}: ${m.currentPrice.toLocaleString()} (${sign}${m.changePercent}%)`
      );
    }
  }

  // 경제 지표
  if (data.indicators.length > 0) {
    sections.push('\n[ 경제 지표 ]');
    for (const ind of data.indicators) {
      sections.push(`  ${ind.name}: ${ind.value} ${ind.change || ''}`);
    }
  }

  // 관심 종목
  if (data.watchlist.length > 0) {
    sections.push('\n[ 관심 종목 ]');
    for (const w of data.watchlist) {
      const sign = w.changePercent >= 0 ? '+' : '';
      sections.push(
        `  ${w.name}: ${w.price.toLocaleString()}원 (${sign}${w.changePercent}%)`
      );
    }
  }

  // 뉴스
  if (data.news.length > 0) {
    sections.push('\n[ 주요 뉴스 ]');
    for (const article of data.news) {
      sections.push(
        `  [${article.category}] ${article.title} (${article.source})`
      );
      if (article.summary) {
        sections.push(`    > ${article.summary}`);
      }
    }
  }

  return sections.join('\n');
}

/** 브리핑에서 핵심 포인트 추출 */
function extractHighlights(content: string): string[] {
  const highlights: string[] = [];
  const lines = content.split('\n');

  for (const line of lines) {
    // 불릿 포인트나 핵심 키워드 포함 라인 추출
    if (
      (line.includes('•') || line.includes('-') || line.includes('▶')) &&
      line.trim().length > 10
    ) {
      highlights.push(line.trim());
    }
  }

  return highlights.slice(0, 5);
}

/** 전반적 시장 심리 감지 */
function detectSentiment(
  content: string
): 'bullish' | 'bearish' | 'neutral' {
  const lower = content.toLowerCase();
  const bullishKeywords = [
    '상승',
    '반등',
    '호재',
    '강세',
    '회복',
    '매수',
    '긍정',
    '성장',
  ];
  const bearishKeywords = [
    '하락',
    '급락',
    '악재',
    '약세',
    '위험',
    '매도',
    '부정',
    '침체',
  ];

  let bullishCount = 0;
  let bearishCount = 0;

  for (const kw of bullishKeywords) {
    bullishCount += (lower.match(new RegExp(kw, 'g')) || []).length;
  }
  for (const kw of bearishKeywords) {
    bearishCount += (lower.match(new RegExp(kw, 'g')) || []).length;
  }

  if (bullishCount > bearishCount * 1.5) return 'bullish';
  if (bearishCount > bullishCount * 1.5) return 'bearish';
  return 'neutral';
}
