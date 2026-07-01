/** Stock API service — wraps all /api/v1 endpoints. */

import axios from "axios";
import type {
  ApiResponse,
  BoardInfo,
  BoardMember,
  FinancialIndicator,
  FundFlowItem,
  KlineBar,
  KlineRange,
  PaginatedData,
  PerformanceReport,
  ProfitForecast,
  StockInfo,
} from "./typings";

const http = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

// ── Stocks ──────────────────────────────────────────────────────────────

export async function fetchStocks(params: {
  exchange?: string;
  board_type?: string;
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedData<StockInfo>> {
  const { data } = await http.get<ApiResponse<PaginatedData<StockInfo>>>(
    "/stocks",
    { params }
  );
  return data.data;
}

export async function fetchStock(
  code: string
): Promise<StockInfo | null> {
  const { data } = await http.get<ApiResponse<StockInfo>>(`/stocks/${code}`);
  return data.code === 200 ? data.data : null;
}

// ── K-line ──────────────────────────────────────────────────────────────

export async function fetchKline(
  code: string,
  params: {
    period?: "daily" | "weekly" | "monthly";
    adjust_type?: "qfq" | "hfq" | "none";
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<PaginatedData<KlineBar>> {
  const period = params.period || "daily";
  const { data } = await http.get<ApiResponse<PaginatedData<KlineBar>>>(
    `/stocks/${code}/${period}`,
    { params }
  );
  return data.data;
}

export async function fetchKlineRange(
  code: string,
  period: string = "daily",
  adjust_type: string = "qfq"
): Promise<KlineRange> {
  const { data } = await http.get<ApiResponse<KlineRange>>(
    `/stocks/${code}/kline-range`,
    { params: { period, adjust_type } }
  );
  return data.data;
}

// ── Performance ─────────────────────────────────────────────────────────

export async function fetchPerformanceReports(
  code: string,
  page: number = 1,
  page_size: number = 20
): Promise<PaginatedData<PerformanceReport>> {
  const { data } = await http.get<
    ApiResponse<PaginatedData<PerformanceReport>>
  >(`/stocks/${code}/performance`, { params: { page, page_size } });
  return data.data;
}

// ── Financials ──────────────────────────────────────────────────────────

export async function fetchFinancialIndicators(
  code: string,
  page: number = 1,
  page_size: number = 20
): Promise<PaginatedData<FinancialIndicator>> {
  const { data } = await http.get<
    ApiResponse<PaginatedData<FinancialIndicator>>
  >(`/stocks/${code}/financials`, { params: { page, page_size } });
  return data.data;
}

// ── Forecast ────────────────────────────────────────────────────────────

export async function fetchProfitForecast(
  code: string
): Promise<ProfitForecast | null> {
  const { data } = await http.get<ApiResponse<ProfitForecast>>(
    `/stocks/${code}/forecast`
  );
  return data.data;
}

// ── Fund Flow ───────────────────────────────────────────────────────────

export async function fetchFundFlow(
  code: string,
  params: {
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<PaginatedData<FundFlowItem>> {
  const { data } = await http.get<ApiResponse<PaginatedData<FundFlowItem>>>(
    `/stocks/${code}/fund-flow`,
    { params }
  );
  return data.data;
}

// ── Boards ──────────────────────────────────────────────────────────────

export async function fetchBoards(params: {
  board_type?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedData<BoardInfo>> {
  const { data } = await http.get<ApiResponse<PaginatedData<BoardInfo>>>(
    "/boards",
    { params }
  );
  return data.data;
}

export async function fetchBoardMembers(
  boardId: string,
  page: number = 1,
  page_size: number = 100
): Promise<PaginatedData<BoardMember>> {
  const { data } = await http.get<ApiResponse<PaginatedData<BoardMember>>>(
    `/boards/${boardId}/members`,
    { params: { page, page_size } }
  );
  return data.data;
}
