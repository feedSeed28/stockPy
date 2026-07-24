/** Unified frontend stock data providers. */

import axios from "axios";

import { getDataSourceMode, type DataSourceMode } from "@/utils/dataSource";
import {
  fetchBoardListEM,
  fetchBoardMembersEM,
  fetchKlineEM,
  fetchLimitUpEM,
  fetchRealtimeMarket,
  fetchRealtimeQuote,
  type KlineBar as EMKlineBar,
  type LimitUpItem,
  type MarketItem,
} from "./eastmoney";
import {
  fetchBoardMembers,
  fetchBoards,
  fetchKline,
  fetchKlineRange,
  fetchStock,
  fetchTodaySummary,
} from "./stock";
import type {
  BoardInfo,
  BoardMember,
  KlineBar,
  KlineRange,
  PaginatedData,
  StockInfo,
} from "./typings";

export interface MarketOverview {
  items: Record<string, any>[];
  total: number;
  date: string;
  stats: { up: number; down: number; flat: number };
  source: DataSourceMode;
}

export interface LimitUpQuery {
  days: number;
  board_type?: string;
  code_prefixes?: string[];
}

export interface LimitUpResult {
  items: Record<string, any>[];
  source: DataSourceMode;
}

export interface StockDataProvider {
  mode: DataSourceMode;
  getStock(code: string): Promise<StockInfo | null>;
  getTodaySummary(code: string): Promise<Record<string, any> | null>;
  getKline(code: string, params: {
    period?: "daily" | "weekly" | "monthly";
    adjust_type?: "qfq" | "hfq" | "none";
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedData<KlineBar>>;
  getKlineRange(code: string, period?: string, adjust_type?: string): Promise<KlineRange>;
  getMarket(params: { page?: number; page_size?: number; sort_by?: string; order?: string }): Promise<MarketOverview>;
  getBoards(params: { board_type?: string; page?: number; page_size?: number }): Promise<PaginatedData<BoardInfo>>;
  getBoardMembers(board: BoardInfo, page?: number, page_size?: number): Promise<PaginatedData<BoardMember>>;
  getLimitUp(query: LimitUpQuery): Promise<LimitUpResult>;
}

function deriveInfo(code: string) {
  return {
    exchange: code.startsWith("6") ? "SH" : "SZ",
    board_type: code.startsWith("688")
      ? "科创板"
      : code.startsWith("300") || code.startsWith("301")
        ? "创业板"
        : "主板",
  } as const;
}

function mapEMKline(b: EMKlineBar): KlineBar {
  return {
    trade_date: b.date,
    open: b.open,
    close: b.close,
    high: b.high,
    low: b.low,
    volume: b.volume,
    amount: b.amount,
    amplitude: b.amplitude,
    change_pct: b.changePct,
    change_amount: b.changeAmt,
    turnover_rate: b.turnover,
  };
}

function mapEMMarketItem(item: MarketItem): Record<string, any> {
  return {
    code: item.code,
    name: item.name,
    industry: item.industry || "",
    change_pct: item.changePct,
    change_amount: item.changeAmt,
    close: item.price,
    open: item.open,
    high: item.high,
    low: item.low,
    volume: item.volume,
    amount: item.amount,
    turnover_rate: item.turnover,
    amplitude: item.amplitude,
  };
}

async function fetchIndustryMap(codes: string[]): Promise<Record<string, string>> {
  const uniqueCodes = [...new Set(codes.filter(Boolean))];
  if (!uniqueCodes.length) return {};
  try {
    const { data } = await axios.get("/api/v1/stocks/industries", {
      params: { codes: uniqueCodes.slice(0, 500).join(",") },
    });
    return data.code === 200 ? data.data?.map || {} : {};
  } catch {
    return {};
  }
}

async function fetchBackendLimitUp(query: LimitUpQuery): Promise<Record<string, any>[]> {
  const { data } = await axios.get("/api/v1/limit-up/period", {
    params: { days: query.days, board_type: query.board_type, page_size: 500 },
  });
  return data.code === 200 ? data.data?.items || [] : [];
}

async function fetchLimitUpStats(codes: string[]): Promise<Record<string, any>> {
  if (!codes.length) return {};
  try {
    const items = await fetchBackendLimitUp({ days: 1 });
    const map: Record<string, any> = {};
    for (const item of items) {
      if (codes.includes(item.code)) map[item.code] = item;
    }
    return map;
  } catch {
    return {};
  }
}

export const backendProvider: StockDataProvider = {
  mode: "backend",

  getStock: fetchStock,
  getTodaySummary: fetchTodaySummary,
  getKline: fetchKline,
  getKlineRange: fetchKlineRange,

  async getMarket(params) {
    const { data } = await axios.get("/api/v1/market/today", {
      params: {
        page: params.page,
        page_size: params.page_size,
        sort_by: params.sort_by || "change_pct",
        order: params.order || "desc",
      },
    });
    if (data.code !== 200) {
      return { items: [], total: 0, date: "", stats: { up: 0, down: 0, flat: 0 }, source: "backend" };
    }
    const d = data.data;
    return {
      items: d.items || [],
      total: d.total || 0,
      date: d.date || "",
      stats: d.stats || { up: 0, down: 0, flat: 0 },
      source: "backend",
    };
  },

  getBoards: fetchBoards,

  getBoardMembers(board, page = 1, page_size = 100) {
    return fetchBoardMembers(board.id || board.board_code, page, page_size);
  },

  async getLimitUp(query) {
    return { items: await fetchBackendLimitUp(query), source: "backend" };
  },
};

export const directProvider: StockDataProvider = {
  mode: "direct",

  async getStock(code) {
    const [em, dbStock] = await Promise.all([
      fetchRealtimeQuote(code).catch(() => null),
      fetchStock(code).catch(() => null),
    ]);
    if (!em) return dbStock;
    const derived = deriveInfo(code);
    return {
      code: em.code,
      name: em.name,
      exchange: derived.exchange,
      board_type: derived.board_type,
      industry: dbStock?.industry || "",
      is_active: true,
      listed_date: dbStock?.listed_date || null,
    };
  },

  async getTodaySummary(code) {
    const [em, dbToday] = await Promise.all([
      fetchRealtimeQuote(code).catch(() => null),
      fetchTodaySummary(code).catch(() => null),
    ]);
    if (!em) return dbToday;
    return {
      code: em.code,
      trade_date: new Date().toISOString().slice(0, 10),
      open: em.open,
      close: em.price,
      high: em.high,
      low: em.low,
      volume: em.volume,
      amount: em.amount,
      change_pct: em.changePct,
      change_amount: em.changeAmt,
      turnover_rate: em.turnover,
      amplitude: em.amplitude,
      lu_5d: dbToday?.lu_5d ?? 0,
      lu_30d: dbToday?.lu_30d ?? 0,
      lu_year: dbToday?.lu_year ?? 0,
      source: "live",
    };
  },

  async getKline(code, params) {
    const period = params.period || "daily";
    const bars = (await fetchKlineEM(code, period, params.page_size || 500)).map(mapEMKline);
    const filtered = bars.filter((bar) => {
      if (params.start_date && bar.trade_date < params.start_date) return false;
      if (params.end_date && bar.trade_date > params.end_date) return false;
      return true;
    });
    const page = params.page || 1;
    const pageSize = params.page_size || filtered.length || 500;
    const start = (page - 1) * pageSize;
    return {
      items: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      page_size: pageSize,
    };
  },

  async getKlineRange(code, period = "daily") {
    const bars = await fetchKlineEM(code, period, 500);
    if (!bars.length) return { min_date: null, max_date: null };
    return { min_date: bars[0].date, max_date: bars[bars.length - 1].date };
  },

  async getMarket(params) {
    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const result = await fetchRealtimeMarket(page, pageSize);
    if (!result || !result.items.length) return backendProvider.getMarket(params);
    let items = result.items.map(mapEMMarketItem);
    if (items.some((item) => !item.industry)) {
      const industryMap = await fetchIndustryMap(items.map((item) => item.code));
      items = items.map((item) => ({
        ...item,
        industry: item.industry || industryMap[item.code] || "",
      }));
    }
    return {
      items,
      total: result.total,
      date: new Date().toLocaleDateString("zh-CN"),
      stats: {
        up: items.filter((i) => i.change_pct > 0).length,
        down: items.filter((i) => i.change_pct < 0).length,
        flat: items.filter((i) => i.change_pct === 0).length,
      },
      source: "direct",
    };
  },

  async getBoards(params) {
    const [ind, con] = await Promise.all([
      fetchBoardListEM("industry").catch(() => []),
      fetchBoardListEM("concept").catch(() => []),
    ]);
    let items: BoardInfo[] = [
      ...ind.map((b) => ({ id: b.code, board_code: b.code, board_name: b.name, board_type: "industry" as const, source: "em" })),
      ...con.map((b) => ({ id: b.code, board_code: b.code, board_name: b.name, board_type: "concept" as const, source: "em" })),
    ];
    if (params.board_type) {
      items = items.filter((b) => b.board_type === params.board_type);
    }
    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const start = (page - 1) * pageSize;
    return {
      items: items.slice(start, start + pageSize),
      total: items.length,
      page,
      page_size: pageSize,
    };
  },

  async getBoardMembers(board) {
    const members = await fetchBoardMembersEM(board.board_code);
    return {
      items: members.map((m) => ({ stock_code: m.code, stock_name: m.name })),
      total: members.length,
      page: 1,
      page_size: members.length,
    };
  },

  async getLimitUp(query) {
    if (query.days !== 1) return backendProvider.getLimitUp(query);
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const emItems = await fetchLimitUpEM(today);
    if (!emItems.length) return backendProvider.getLimitUp(query);

    const filtered = query.code_prefixes?.length
      ? emItems.filter((item: LimitUpItem) =>
          query.code_prefixes?.some((prefix) => item.code.startsWith(prefix))
        )
      : emItems;
    const stats = await fetchLimitUpStats(filtered.map((item) => item.code));
    return {
      source: "direct",
      items: filtered.map((item) => {
        const dbStats = stats[item.code] || {};
        return {
          code: item.code,
          name: item.name,
          price: item.price,
          change_pct: item.changePct,
          count: 1,
          trade_date: new Date().toISOString().slice(0, 10),
          turnover: item.turnover,
          amount: item.amount,
          industry: item.industry,
          stats_5d: dbStats.stats_5d ?? (item.changePct >= 9.8 ? 1 : 0),
          stats_30d: dbStats.stats_30d ?? (item.changePct >= 9.8 ? 1 : 0),
          stats_year: dbStats.stats_year ?? (item.changePct >= 9.8 ? 1 : 0),
        };
      }),
    };
  },
};

export function getStockDataProvider(): StockDataProvider {
  return getDataSourceMode() === "direct" ? directProvider : backendProvider;
}
