import axios from 'axios';
import * as cheerio from 'cheerio';
import RssParser from 'rss-parser';
import { NewsArticle, NewsCategory } from '../types';
import logger from '../utils/logger';

const rssParser = new RssParser();

// ============================================
// 뉴스 수집기
// ============================================

/** 네이버 경제 뉴스 헤드라인 크롤링 */
async function fetchNaverEconomyNews(): Promise<NewsArticle[]> {
  try {
    const url = 'https://news.naver.com/section/101'; // 경제 섹션
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      timeout: 10000,
    });

    const $ = cheerio.load(data);
    const articles: NewsArticle[] = [];

    // 헤드라인 뉴스 추출
    $('div.sa_text').each((_, el) => {
      const titleEl = $(el).find('a.sa_text_title');
      const title = titleEl.find('strong').text().trim();
      const href = titleEl.attr('href') || '';
      const summary = $(el).find('div.sa_text_lede').text().trim();

      if (title) {
        articles.push({
          title,
          summary: summary.slice(0, 200),
          url: href,
          source: '네이버 경제',
          publishedAt: new Date().toISOString(),
          category: categorizeNews(title + ' ' + summary),
        });
      }
    });

    logger.info(`네이버 경제 뉴스 ${articles.length}건 수집`);
    return articles.slice(0, 15);
  } catch (error) {
    logger.error('네이버 뉴스 수집 실패', { error });
    return [];
  }
}

/** 네이버 정치 뉴스 헤드라인 크롤링 */
async function fetchNaverPoliticsNews(): Promise<NewsArticle[]> {
  try {
    const url = 'https://news.naver.com/section/100'; // 정치 섹션
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      timeout: 10000,
    });

    const $ = cheerio.load(data);
    const articles: NewsArticle[] = [];

    $('div.sa_text').each((_, el) => {
      const titleEl = $(el).find('a.sa_text_title');
      const title = titleEl.find('strong').text().trim();
      const href = titleEl.attr('href') || '';
      const summary = $(el).find('div.sa_text_lede').text().trim();

      if (title) {
        articles.push({
          title,
          summary: summary.slice(0, 200),
          url: href,
          source: '네이버 정치',
          publishedAt: new Date().toISOString(),
          category: 'politics',
        });
      }
    });

    logger.info(`네이버 정치 뉴스 ${articles.length}건 수집`);
    return articles.slice(0, 10);
  } catch (error) {
    logger.error('네이버 정치 뉴스 수집 실패', { error });
    return [];
  }
}

/** RSS 피드에서 글로벌 경제 뉴스 수집 */
async function fetchRssNews(): Promise<NewsArticle[]> {
  const feeds = [
    {
      url: 'https://feeds.bbci.co.uk/news/business/rss.xml',
      source: 'BBC Business',
      category: 'global' as NewsCategory,
    },
    {
      url: 'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
      source: 'NYT Economy',
      category: 'global' as NewsCategory,
    },
    {
      url: 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147',
      source: 'CNBC',
      category: 'global' as NewsCategory,
    },
  ];

  const articles: NewsArticle[] = [];

  for (const feed of feeds) {
    try {
      const parsed = await rssParser.parseURL(feed.url);
      const items = (parsed.items || []).slice(0, 5);

      for (const item of items) {
        articles.push({
          title: item.title || '',
          summary: (item.contentSnippet || item.content || '').slice(0, 200),
          url: item.link || '',
          source: feed.source,
          publishedAt: item.isoDate || new Date().toISOString(),
          category: feed.category,
        });
      }

      logger.debug(`${feed.source}에서 ${items.length}건 수집`);
    } catch (error) {
      logger.warn(`RSS 수집 실패: ${feed.source}`, { error });
    }
  }

  return articles;
}

/** 뉴스 제목+내용으로 카테고리 자동 분류 */
function categorizeNews(text: string): NewsCategory {
  const lower = text.toLowerCase();

  if (/금리|기준금리|한은|연준|fed|통화정책|인플레/.test(lower)) return 'policy';
  if (/국회|대통령|정부|총리|외교|북한|선거/.test(lower)) return 'politics';
  if (/반도체|ai|배터리|자동차|it|테크|기술/.test(lower)) return 'industry';
  if (/코스피|코스닥|나스닥|s&p|dow|증시|주가/.test(lower)) return 'market';
  if (/미국|중국|일본|유럽|글로벌|세계/.test(lower)) return 'global';
  if (/트렌드|mz|소비|유행|핫/.test(lower)) return 'trend';
  return 'economy';
}

/** 전체 뉴스 수집 (메인 함수) */
export async function collectAllNews(): Promise<NewsArticle[]> {
  logger.info('뉴스 수집 시작...');

  const [economyNews, politicsNews, rssNews] = await Promise.all([
    fetchNaverEconomyNews(),
    fetchNaverPoliticsNews(),
    fetchRssNews(),
  ]);

  const allNews = [...economyNews, ...politicsNews, ...rssNews];

  // 중복 제거 (제목 기준)
  const seen = new Set<string>();
  const unique = allNews.filter((article) => {
    const key = article.title.slice(0, 30);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  logger.info(`총 ${unique.length}건 뉴스 수집 완료`);
  return unique;
}
