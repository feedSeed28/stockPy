/** 东方财富公开 API — 浏览器直调，不经过后端 */

import axios from "axios";

// ── API 端点 ────────────────────────────────────────────────────────────

const EM_PUSH = "https://push2.eastmoney.com/api/qt";
const EM_PUSH_HIS = "https://push2his.eastmoney.com/api/qt/stock/kline";
const EM_PUSH_EX = "https://push2ex.eastmoney.com";
const EM_DATACENTER = "https://datacenter.eastmoney.com/securities/api/data/v1";
const EM_DATACENTER_WEB = "https://datacenter-web.eastmoney.com/api/data/v1";

// ── 工具 ────────────────────────────────────────────────────────────────

/** 股票代码转东方财富 market.code 格式 */
function toSecid(code: string): string {
  const m = code.startsWith("6") ? "1" : "0";
  return `${m}.${code}`;
}

// ── 实时行情 — 个股快照 ──────────────────────────────────────────────────

export interface RealtimeQuote {
  code: string;
  name: string;
  price: number;        // 最新价
  open: number;          // 今开
  high: number;          // 最高
  low: number;           // 最低
  prevClose: number;     // 昨收
  changePct: number;     // 涨跌幅%
  changeAmt: number;     // 涨跌额
  volume: number;        // 成交量(手)
  amount: number;        // 成交额
  turnover: number;      // 换手率%
  amplitude: number;     // 振幅%
  pe: number;            // 市盈率(动)
  totalMv: number;       // 总市值
  floatMv: number;       // 流通市值
}

/** 获取单只股票实时行情 */
export async function fetchRealtimeQuote(code: string): Promise<RealtimeQuote | null> {
  const secid = toSecid(code);
  const fields = "f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171";
  const url = `${EM_PUSH}/stock/get?fltt=2&invt=2&secid=${secid}&fields=${fields}`;

  try {
    const { data } = await axios.get(url, { timeout: 8000 });
    if (!data?.data) return null;

    const d = data.data;
    return {
      code: d.f57 ?? code,
      name: d.f58 ?? "",
      price: (d.f43 ?? 0) / 100,       // 分→元
      open: (d.f46 ?? 0) / 100,
      high: (d.f44 ?? 0) / 100,
      low: (d.f45 ?? 0) / 100,
      prevClose: (d.f60 ?? 0) / 100,
      changePct: d.f168 ?? 0,
      changeAmt: (d.f169 ?? 0) / 100,
      volume: d.f47 ?? 0,
      amount: d.f48 ?? 0,
      turnover: (d.f167 ?? 0) / 100,
      amplitude: d.f171 ?? 0,
      pe: (d.f162 ?? 0) / 100,
      totalMv: d.f116 ?? 0,
      floatMv: d.f117 ?? 0,
    };
  } catch {
    return null;
  }
}

// ── 实时行情 — 全市场列表 ─────────────────────────────────────────────────

export interface MarketItem {
  code: string;
  name: string;
  price: number;
  changePct: number;
  changeAmt: number;
  volume: number;
  amount: number;
  amplitude: number;
  turnover: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
  totalMv: number;
  floatMv: number;
}

/** 获取全市场实时行情列表 */
export async function fetchRealtimeMarket(
  page: number = 1, pageSize: number = 50
): Promise<{ items: MarketItem[]; total: number } | null> {
  // 沪深A股 (排除北交所)
  const fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23";
  const fields = "f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18,f20,f21";
  const url = `${EM_PUSH}/clist/get?pn=${page}&pz=${pageSize}&po=1&np=1&fltt=2&invt=2` +
    `&fid=f3&fs=${encodeURIComponent(fs)}&fields=${fields}`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.data) return null;

    const items: MarketItem[] = (data.data.diff ?? []).map((d: any) => ({
      code: d.f12 ?? "",
      name: d.f14 ?? "",
      price: d.f2 ?? 0,
      changePct: d.f3 ?? 0,
      changeAmt: d.f4 ?? 0,
      volume: d.f5 ?? 0,
      amount: d.f6 ?? 0,
      amplitude: d.f7 ?? 0,
      turnover: d.f8 ?? 0,
      high: d.f15 ?? 0,
      low: d.f16 ?? 0,
      open: d.f17 ?? 0,
      prevClose: d.f18 ?? 0,
      totalMv: d.f20 ?? 0,
      floatMv: d.f21 ?? 0,
    }));

    return { items, total: data.data.total ?? 0 };
  } catch {
    return null;
  }
}

// ── 实时行情 — 批量个股快照 ──────────────────────────────────────────────

/** 批量获取多只股票实时行情（一次请求） */
export async function fetchRealtimeQuotes(codes: string[]): Promise<RealtimeQuote[]> {
  if (codes.length === 0) return [];
  if (codes.length === 1) {
    const r = await fetchRealtimeQuote(codes[0]);
    return r ? [r] : [];
  }

  // 用 clist/get 批量查询
  const secids = codes.map(toSecid).join(",");
  const fields = "f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171";
  const url = `${EM_PUSH}/stock/get?fltt=2&invt=2&secid=${secids}&fields=${fields}`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.data) return [];

    const items = Array.isArray(data.data) ? data.data : [data.data];
    return items.map((d: any) => ({
      code: d.f57 ?? "",
      name: d.f58 ?? "",
      price: (d.f43 ?? 0) / 100,
      open: (d.f46 ?? 0) / 100,
      high: (d.f44 ?? 0) / 100,
      low: (d.f45 ?? 0) / 100,
      prevClose: (d.f60 ?? 0) / 100,
      changePct: d.f168 ?? 0,
      changeAmt: (d.f169 ?? 0) / 100,
      volume: d.f47 ?? 0,
      amount: d.f48 ?? 0,
      turnover: (d.f167 ?? 0) / 100,
      amplitude: d.f171 ?? 0,
      pe: (d.f162 ?? 0) / 100,
      totalMv: d.f116 ?? 0,
      floatMv: d.f117 ?? 0,
    }));
  } catch {
    return [];
  }
}

// ── K线数据 ──────────────────────────────────────────────────────────────

export interface KlineBar {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  amplitude: number;
  changePct: number;
  changeAmt: number;
  turnover: number;
}

/** K线周期映射 */
const KLT_MAP: Record<string, number> = { daily: 101, weekly: 102, monthly: 103 };

/** 获取K线数据（前复权） */
export async function fetchKlineEM(
  code: string, period: string = "daily", limit: number = 200
): Promise<KlineBar[]> {
  const klt = KLT_MAP[period] ?? 101;
  const url = `${EM_PUSH_HIS}/get?fields1=f1,f2,f3,f4,f5,f6` +
    `&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61` +
    `&ut=7eea3edcaed734bea9cbfc24409ed989` +
    `&klt=${klt}&fqt=1&secid=${toSecid(code)}&lmt=${limit}&end=20500101`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.data?.klines) return [];

    return data.data.klines.map((s: string) => {
      const [date, open, close, high, low, vol, amt, amp, pct, amt2, to] = s.split(",");
      return {
        date,
        open: +open, close: +close, high: +high, low: +low,
        volume: +vol, amount: +amt,
        amplitude: +amp, changePct: +pct, changeAmt: +amt2, turnover: +to,
      };
    });
  } catch {
    return [];
  }
}

// ── 财务指标 ──────────────────────────────────────────────────────────────

export interface EMFinancialIndicator {
  reportDate: string;
  epsBasic: number | null;
  epsDiluted: number | null;
  bvps: number | null;
  cfps: number | null;
  roe: number | null;
  roa: number | null;
  grossMargin: number | null;
  netMargin: number | null;
  revenue: number | null;
  netProfit: number | null;
  revenueGrowth: number | null;
  profitGrowth: number | null;
}

/** 获取单只股票财务指标 */
export async function fetchFinancialsEM(code: string): Promise<EMFinancialIndicator[]> {
  const emCode = code.startsWith("6") ? `"${code}.SH"` : `"${code}.SZ"`;
  const filter = `(SECUCODE=${emCode})`;
  const cols = "REPORT_DATE,EPSJB,EPSXS,BPS,MGJYXJJE,ROEJQ,ZZCJLL," +
    "XSMLL,XSJLL,TOTALOPERATEREVE,PARENTNETPROFIT," +
    "TOTALOPERATEREVETZ,PARENTNETPROFITTZ,NOTICE_DATE";
  const url = `${EM_DATACENTER}/get?reportName=RPT_F10_FINANCE_MAINFINADATA` +
    `&columns=${cols}&filter=${encodeURIComponent(filter)}` +
    `&pageNumber=1&pageSize=50&sortTypes=-1&sortColumns=REPORT_DATE`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.result?.data) return [];

    return data.result.data.map((d: any) => ({
      reportDate: d.REPORT_DATE?.split(" ")[0] ?? "",
      epsBasic: d.EPSJB ?? null,
      epsDiluted: d.EPSXS ?? null,
      bvps: d.BPS ?? null,
      cfps: d.MGJYXJJE ?? null,
      roe: d.ROEJQ ?? null,
      roa: d.ZZCJLL ?? null,
      grossMargin: d.XSMLL ?? null,
      netMargin: d.XSJLL ?? null,
      revenue: d.TOTALOPERATEREVE ?? null,
      netProfit: d.PARENTNETPROFIT ?? null,
      revenueGrowth: d.TOTALOPERATEREVETZ ?? null,
      profitGrowth: d.PARENTNETPROFITTZ ?? null,
    }));
  } catch {
    return [];
  }
}

// ── 业绩报表 ──────────────────────────────────────────────────────────────

export interface EMPerformanceReport {
  reportDate: string;
  eps: number | null;
  revenue: number | null;
  revenueYoy: number | null;
  netProfit: number | null;
  netProfitYoy: number | null;
  bvps: number | null;
  roe: number | null;
  cfps: number | null;
  grossMargin: number | null;
}

/** 获取单只股票业绩报表 */
export async function fetchPerformanceEM(code: string): Promise<EMPerformanceReport[]> {
  const emCode = code.startsWith("6") ? `"${code}.SH"` : `"${code}.SZ"`;
  const filter = `(SECUCODE=${emCode})`;
  const cols = "REPORT_DATE,BASIC_EPS,TOTAL_OPERATE_INCOME," +
    "TOTAL_OPERATE_INCOME_YOY,PARENT_NETPROFIT,PARENT_NETPROFIT_YOY," +
    "BPS,WEIGHTAVG_ROE,OPERATE_CASHFLOW_PER_SHARE,GROSS_PROFIT_MARGIN";
  const url = `${EM_DATACENTER_WEB}/get?reportName=RPT_LICO_FN_CPD` +
    `&columns=${cols}&filter=${encodeURIComponent(filter)}` +
    `&pageNumber=1&pageSize=50&sortTypes=-1&sortColumns=REPORT_DATE`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.result?.data) return [];

    return data.result.data.map((d: any) => ({
      reportDate: d.REPORT_DATE?.split(" ")[0] ?? "",
      eps: d.BASIC_EPS ?? null,
      revenue: d.TOTAL_OPERATE_INCOME ?? null,
      revenueYoy: d.TOTAL_OPERATE_INCOME_YOY ?? null,
      netProfit: d.PARENT_NETPROFIT ?? null,
      netProfitYoy: d.PARENT_NETPROFIT_YOY ?? null,
      bvps: d.BPS ?? null,
      roe: d.WEIGHTAVG_ROE ?? null,
      cfps: d.OPERATE_CASHFLOW_PER_SHARE ?? null,
      grossMargin: d.GROSS_PROFIT_MARGIN ?? null,
    }));
  } catch {
    return [];
  }
}

// ── 涨停板 ────────────────────────────────────────────────────────────────

export interface LimitUpItem {
  code: string;
  name: string;
  price: number;
  changePct: number;
  amount: number;
  floatMv: number;
  totalMv: number;
  turnover: number;
  industry: string;
}

/** 获取当日涨停板列表 */
export async function fetchLimitUpEM(date?: string): Promise<LimitUpItem[]> {
  const targetDate = date ?? new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const url = `${EM_PUSH_EX}/getTopicZTPool` +
    `?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt` +
    `&Pageindex=0&pagesize=200&sort=fbt:asc&date=${targetDate}`;

  try {
    const { data } = await axios.get(url, { timeout: 8000 });
    if (!data?.data?.pool) return [];

    return data.data.pool.map((d: any) => ({
      code: d.c ?? "",
      name: d.n ?? "",
      price: d.p ?? 0,
      changePct: d.zdp ?? 0,
      amount: d.amount ?? 0,
      floatMv: d.ltsz ?? 0,
      totalMv: d.tsz ?? 0,
      turnover: d.hs ?? 0,
      industry: d.hyName ?? "",
    }));
  } catch {
    return [];
  }
}

// ── 资金流（个股历史） ───────────────────────────────────────────────────

export interface FundFlowItem {
  date: string;
  close: number;
  changePct: number;
  mainInflow: number;
  mainRatio: number;
  hugeInflow: number;
  hugeRatio: number;
  largeInflow: number;
  largeRatio: number;
  mediumInflow: number;
  mediumRatio: number;
  smallInflow: number;
  smallRatio: number;
}

/** 获取个股资金流历史 */
export async function fetchFundFlowEM(code: string, days: number = 30): Promise<FundFlowItem[]> {
  const url = `${EM_PUSH_HIS}/fflow/daykline/get` +
    `?lmt=${days}&klt=101&secid=${toSecid(code)}` +
    `&fields1=f1,f2,f3,f7` +
    `&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65` +
    `&ut=b2884a393a59ad64002292a3e90d46a5`;

  try {
    const { data } = await axios.get(url, { timeout: 8000 });
    if (!data?.data?.klines) return [];

    return data.data.klines.map((s: string) => {
      const [date, mainIn, smallIn, midIn, largeIn, hugeIn,
        mainR, smallR, midR, largeR, hugeR, close, pct] = s.split(",");
      return {
        date, close: +close, changePct: +pct,
        mainInflow: +mainIn, mainRatio: +mainR,
        hugeInflow: +hugeIn, hugeRatio: +hugeR,
        largeInflow: +largeIn, largeRatio: +largeR,
        mediumInflow: +midIn, mediumRatio: +midR,
        smallInflow: +smallIn, smallRatio: +smallR,
      };
    });
  } catch {
    return [];
  }
}

// ── 板块 ──────────────────────────────────────────────────────────────────

export interface EMBoardInfo {
  code: string;
  name: string;
  changePct: number;
  price: number;
  boardType: "industry" | "concept";
}

/** 获取行业或概念板块列表 */
export async function fetchBoardListEM(
  type: "industry" | "concept" = "industry"
): Promise<EMBoardInfo[]> {
  const t = type === "industry" ? "2" : "3";
  const url = `${EM_PUSH}/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2` +
    `&fid=f3&fs=m:90+t:${t}&fields=f2,f3,f4,f12,f14,f20,f21`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.data?.diff) return [];

    return data.data.diff.map((d: any) => ({
      code: d.f12 ?? "",
      name: d.f14 ?? "",
      changePct: d.f3 ?? 0,
      price: d.f2 ?? 0,
      boardType: type,
    }));
  } catch {
    return [];
  }
}

export interface EMStockBrief {
  code: string;
  name: string;
}

/** 获取板块成分股 */
export async function fetchBoardMembersEM(boardCode: string): Promise<EMStockBrief[]> {
  const url = `${EM_PUSH}/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2` +
    `&fid=f12&fs=b:${boardCode}&fields=f12,f14`;

  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    if (!data?.data?.diff) return [];

    return data.data.diff.map((d: any) => ({
      code: d.f12 ?? "",
      name: d.f14 ?? "",
    }));
  } catch {
    return [];
  }
}
