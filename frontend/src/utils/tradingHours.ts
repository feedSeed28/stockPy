/** A股交易时段判断工具 */

import dayjs from "dayjs";

/** A股交易日 + 交易时段判断 */
export function isTradingHours(): boolean {
  const now = dayjs();
  const day = now.day();
  // 周末不交易
  if (day === 0 || day === 6) return false;

  const time = now.format("HHmm");
  // 上午 9:30-11:30，下午 13:00-15:00
  return (time >= "0930" && time <= "1130") || (time >= "1300" && time <= "1500");
}

/** 是否使用实时数据源（东方财富 CORS API） */
export function useRealtimeSource(): boolean {
  return isTradingHours();
}

/** A股交易时段描述 */
export function getTradingSessionLabel(): string {
  if (!isTradingHours()) return "盘后（使用本地数据库）";

  const now = dayjs();
  const time = now.format("HHmm");
  if (time >= "0930" && time <= "1130") return "盘中·上午（实时数据）";
  if (time >= "1300" && time <= "1500") return "盘中·下午（实时数据）";
  return "盘中（实时数据）";
}

/** 距下一次开盘时间 */
export function getNextOpenTime(): string {
  const now = dayjs();
  const day = now.day();

  if (day === 0) return "明天 9:30";
  if (day === 6) return "周一 9:30";

  const time = now.format("HHmm");
  if (time < "0930") return "今天 9:30";
  if (time >= "1500" && day === 5) return "周一 9:30";
  if (time >= "1500") return "明天 9:30";
  return "今天 13:00";
}
