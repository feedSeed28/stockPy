/** 数据源模式管理 — localStorage 持久化，默认后端模式 */

const STORAGE_KEY = "stock_data_source_mode";

export type DataSourceMode = "direct" | "backend";

/** 获取当前数据源模式（默认后端，需手动开启直连） */
export function getDataSourceMode(): DataSourceMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "direct" || v === "backend") return v;
  } catch {}
  return "backend"; // 默认后端接口模式，直连需在数据管理页手动开启
}

/** 设置数据源模式 */
export function setDataSourceMode(mode: DataSourceMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {}
}

/** 是否使用直连模式（前端直连东方财富/新浪） */
export function useDirectSource(): boolean {
  return getDataSourceMode() === "direct";
}

/** 监听数据源模式变化（用于组件内响应式更新） */
export function onDataSourceChange(fn: () => void): () => void {
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) fn();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}
