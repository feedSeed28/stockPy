/** Unified API response shape */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

/** Paginated list */
export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ── Stock ──────────────────────────────────────────────────────────────

export interface StockInfo {
  code: string;
  name: string;
  exchange: "SH" | "SZ" | "BJ";
  board_type: string | null;
  industry: string | null;
  is_active: boolean;
  listed_date: string | null;
}

// ── K-line ─────────────────────────────────────────────────────────────

export interface KlineBar {
  trade_date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  amplitude: number | null;
  change_pct: number | null;
  change_amount: number | null;
  turnover_rate: number | null;
}

export interface KlineRange {
  min_date: string | null;
  max_date: string | null;
}

// ── Performance ────────────────────────────────────────────────────────

export interface PerformanceReport {
  report_date: string;
  eps: number | null;
  revenue: number | null;
  revenue_yoy: number | null;
  revenue_qoq: number | null;
  net_profit: number | null;
  net_profit_yoy: number | null;
  net_profit_qoq: number | null;
  bvps: number | null;
  roe: number | null;
  cfps: number | null;
  gross_margin: number | null;
}

// ── Financials ─────────────────────────────────────────────────────────

export interface FinancialIndicator {
  report_date: string;
  eps_basic: number | null;
  eps_diluted: number | null;
  bvps: number | null;
  cfps: number | null;
  roe: number | null;
  roa: number | null;
  gross_margin: number | null;
  net_margin: number | null;
  revenue_growth: number | null;
  profit_growth: number | null;
  asset_growth: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  debt_ratio: number | null;
  operating_cf: number | null;
  investing_cf: number | null;
  financing_cf: number | null;
}

// ── Forecast ───────────────────────────────────────────────────────────

export interface ProfitForecast {
  stock_code: string;
  stock_name: string | null;
  research_report_num: number | null;
  ratings: {
    buy: number | null;
    overweight: number | null;
    neutral: number | null;
    underweight: number | null;
    sell: number | null;
  };
  forecast_eps: (number | null)[];
  forecast_np: (number | null)[];
  target_avg_price: number | null;
  updated_date: string;
}

// ── Fund Flow ──────────────────────────────────────────────────────────

export interface FundFlowItem {
  trade_date: string;
  close: number | null;
  change_pct: number | null;
  main_net_inflow: number | null;
  main_net_ratio: number | null;
  huge_net_inflow: number | null;
  huge_net_ratio: number | null;
  large_net_inflow: number | null;
  large_net_ratio: number | null;
  medium_net_inflow: number | null;
  medium_net_ratio: number | null;
  small_net_inflow: number | null;
  small_net_ratio: number | null;
}

// ── Boards ─────────────────────────────────────────────────────────────

export interface BoardInfo {
  id: string;
  board_code: string;
  board_name: string;
  board_type: "industry" | "concept";
  source: string;
}

export interface BoardMember {
  stock_code: string;
  stock_name: string | null;
}
