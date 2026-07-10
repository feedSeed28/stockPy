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
