/** 数据管理 API — 后端接口 */

import axios from "axios";

const http = axios.create({ baseURL: "/api/v1", timeout: 15000 });

export interface SyncStatusItem {
  table_name: string;
  table_label: string;
  last_sync_time: string | null;
  last_data_date: string | null;
  row_count: number | null;
  status: string;
  error_message: string | null;
}

export interface StaticExportRequest {
  symbols?: string;
  all_kline?: boolean;
  kline_limit?: number;
  periods?: string;
  include_board_members?: boolean;
  out?: string;
}

export interface StaticExportStatus {
  status: "idle" | "queued" | "running" | "success" | "error";
  started_at: string | null;
  finished_at: string | null;
  output_dir: string | null;
  command: string | null;
  returncode: number | null;
  stdout_tail: string;
  stderr_tail: string;
  error_message: string | null;
}

/** 获取所有表的同步状态 */
export async function fetchSyncStatus(): Promise<SyncStatusItem[]> {
  try {
    const { data } = await http.get("/data/sync-status");
    return data.data?.items ?? [];
  } catch {
    return [];
  }
}

/** 手动触发某张表的同步 */
export async function triggerSync(table: string): Promise<{ ok: boolean; message: string }> {
  try {
    const { data } = await http.post("/data/trigger-sync", { table });
    return { ok: data.code === 200, message: data.message };
  } catch {
    return { ok: false, message: "请求失败" };
  }
}

/** 触发前端静态数据导出 */
export async function triggerStaticExport(
  payload: StaticExportRequest
): Promise<{ ok: boolean; message: string; status?: StaticExportStatus }> {
  try {
    const { data } = await http.post("/data/export-static", payload);
    return { ok: data.code === 200, message: data.message, status: data.data };
  } catch {
    return { ok: false, message: "请求失败" };
  }
}

/** 获取静态数据导出状态 */
export async function fetchStaticExportStatus(): Promise<StaticExportStatus | null> {
  try {
    const { data } = await http.get("/data/export-static/status");
    return data.data ?? null;
  } catch {
    return null;
  }
}
