import { PageContainer } from "@ant-design/pro-components";
import {
  Badge,
  Button,
  Card,
  Col,
  Input,
  InputNumber,
  message,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined, SyncOutlined, ApiOutlined, ThunderboltOutlined, DatabaseOutlined, DownloadOutlined } from "@ant-design/icons";
import { useEffect, useState, useCallback } from "react";

import {
  fetchStaticExportStatus,
  fetchSyncStatus,
  triggerStaticExport,
  triggerSync,
  type StaticExportStatus,
  type SyncStatusItem,
} from "@/services/dataManagement";
import { getDataSourceMode, setDataSourceMode, type DataSourceMode } from "@/utils/dataSource";

const { Text, Title } = Typography;

// ── 表名中文映射 ──────────────────────────────────────────────────────────
const TABLE_LABELS: Record<string, string> = {
  stock_info: "股票列表",
  stock_daily_quote: "日K线",
  stock_weekly_quote: "周K线",
  stock_monthly_quote: "月K线",
  stock_financial_indicator: "财务指标",
  stock_performance_report: "业绩报表",
  stock_profit_forecast: "盈利预测",
  stock_fund_flow_daily: "资金流",
  stock_board_info: "板块信息",
  stock_board_member: "板块成员",
};

const STATUS_COLORS: Record<string, string> = {
  idle: "green",
  syncing: "processing",
  error: "red",
  pending: "default",
};

const EXPORT_STATUS_COLORS: Record<string, string> = {
  idle: "default",
  queued: "processing",
  running: "processing",
  success: "green",
  error: "red",
};

// ── 组件 ──────────────────────────────────────────────────────────────────

export default function DataManagementPage() {
  const [syncItems, setSyncItems] = useState<SyncStatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncingTable, setSyncingTable] = useState<string | null>(null);
  const [sourceMode, setSourceMode] = useState<DataSourceMode>(getDataSourceMode);
  const [exportSymbols, setExportSymbols] = useState("");
  const [exportAllKline, setExportAllKline] = useState(false);
  const [exportKlineLimit, setExportKlineLimit] = useState(500);
  const [exportPeriods, setExportPeriods] = useState<string[]>(["daily"]);
  const [includeBoardMembers, setIncludeBoardMembers] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<StaticExportStatus | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    const items = await fetchSyncStatus();
    setSyncItems(items);
    setLoading(false);
  }, []);

  const loadExportStatus = useCallback(async () => {
    const status = await fetchStaticExportStatus();
    if (status) setExportStatus(status);
  }, []);

  useEffect(() => {
    loadStatus();
    loadExportStatus();
  }, [loadStatus, loadExportStatus]);

  useEffect(() => {
    if (!exportStatus || !["queued", "running"].includes(exportStatus.status)) return;
    const timer = window.setInterval(loadExportStatus, 3000);
    return () => window.clearInterval(timer);
  }, [exportStatus, loadExportStatus]);

  const handleTriggerSync = async (table: string) => {
    setSyncingTable(table);
    const result = await triggerSync(table);
    if (result.ok) {
      message.success(`${TABLE_LABELS[table] ?? table} 同步已触发`);
    } else {
      message.error(result.message || "触发失败");
    }
    setSyncingTable(null);
    // 等几秒刷新状态
    setTimeout(loadStatus, 3000);
  };

  const handleStaticExport = async () => {
    setExporting(true);
    const result = await triggerStaticExport({
      symbols: exportSymbols.trim() || undefined,
      all_kline: exportAllKline,
      kline_limit: exportKlineLimit,
      periods: exportPeriods.join(","),
      include_board_members: includeBoardMembers,
    });
    if (result.ok) {
      message.success(result.message || "静态数据导出已触发");
      if (result.status) setExportStatus(result.status);
      setTimeout(loadExportStatus, 1500);
    } else {
      message.error(result.message || "触发失败");
    }
    setExporting(false);
  };

  const columns = [
    {
      title: "数据表",
      dataIndex: "table_name",
      key: "table_name",
      render: (_: any, r: SyncStatusItem) =>
        TABLE_LABELS[r.table_name] ?? r.table_name,
    },
    {
      title: "行数",
      dataIndex: "row_count",
      key: "row_count",
      align: "right" as const,
      render: (v: number | null) =>
        v != null ? v.toLocaleString() : "-",
    },
    {
      title: "最后数据日期",
      dataIndex: "last_data_date",
      key: "last_data_date",
      render: (v: string | null) => v ?? "-",
    },
    {
      title: "最后同步",
      dataIndex: "last_sync_time",
      key: "last_sync_time",
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (v: string) => <Tag color={STATUS_COLORS[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "操作",
      key: "actions",
      render: (_: any, r: SyncStatusItem) => (
        <Button
          size="small"
          icon={<SyncOutlined spin={syncingTable === r.table_name} />}
          loading={syncingTable === r.table_name}
          onClick={() => handleTriggerSync(r.table_name)}
        >
          同步
        </Button>
      ),
    },
  ];

  return (
    <PageContainer>
      {/* 数据源切换 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {sourceMode === "direct" ? (
                <ThunderboltOutlined style={{ fontSize: 32, color: "#fa8c16" }} />
              ) : (
                <DatabaseOutlined style={{ fontSize: 32, color: "#1677ff" }} />
              )}
              <div>
                <Text strong style={{ fontSize: 16 }}>
                  {sourceMode === "direct" ? "🔥 前端直连模式" : "💾 后端接口模式"}
                </Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {sourceMode === "direct"
                    ? "浏览器直连东方财富 API（用户 IP，单次查询不会被封）"
                    : "全部走后端 FastAPI → MySQL 数据库（默认）"
                  }
                </Text>
              </div>
            </div>
          </Col>
          <Col flex="auto" style={{ textAlign: "right" }}>
            <Space direction="vertical" size={4} style={{ alignItems: "center" }}>
              <Switch
                checked={sourceMode === "backend"}
                checkedChildren="后端"
                unCheckedChildren="直连"
                onChange={(checked) => {
                  const newMode: DataSourceMode = checked ? "backend" : "direct";
                  setSourceMode(newMode);
                  setDataSourceMode(newMode);
                  message.success(`已切换至：${newMode === "direct" ? "前端直连模式" : "后端接口模式"}`);
                  // 刷新页面以应用新数据源
                  setTimeout(() => window.location.reload(), 500);
                }}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                点击切换 · 自动刷新页面
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据源状态 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="东方财富 API"
              value="正常"
              suffix={<Badge status="success" />}
              prefix={<ApiOutlined />}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              CORS 支持 · 浏览器直调 · 用户 IP 分发
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="新浪 API"
              value="部分可用"
              suffix={<Badge status="warning" />}
              prefix={<ApiOutlined />}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              K线/LHB 正常 · 财务指标已切换EM
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="已缓存数据"
              value={syncItems.reduce((s, i) => s + (i.row_count ?? 0), 0).toLocaleString()}
              suffix="行"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {syncItems.length} 张表
            </Text>
          </Card>
        </Col>
      </Row>

      {/* 静态数据导出 */}
      <Card
        title="前端静态数据导出"
        style={{ marginBottom: 16 }}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={loadExportStatus}>
            刷新状态
          </Button>
        }
      >
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} md={8}>
            <Text type="secondary">股票代码</Text>
            <Input
              placeholder="留空只导出轻量数据；例：000001,600000"
              value={exportSymbols}
              disabled={exportAllKline}
              onChange={(e) => setExportSymbols(e.target.value)}
            />
          </Col>
          <Col xs={12} md={4}>
            <Text type="secondary">K线条数</Text>
            <InputNumber
              min={1}
              max={5000}
              value={exportKlineLimit}
              onChange={(v) => setExportKlineLimit(v || 500)}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={12} md={5}>
            <Text type="secondary">K线周期</Text>
            <Select
              mode="multiple"
              value={exportPeriods}
              onChange={(v) => setExportPeriods(v.length ? v : ["daily"])}
              options={[
                { label: "日K", value: "daily" },
                { label: "周K", value: "weekly" },
                { label: "月K", value: "monthly" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={12} md={3}>
            <Space direction="vertical" size={4}>
              <Text type="secondary">全量K线</Text>
              <Switch checked={exportAllKline} onChange={setExportAllKline} />
            </Space>
          </Col>
          <Col xs={12} md={4}>
            <Space direction="vertical" size={4}>
              <Text type="secondary">板块成员</Text>
              <Switch checked={includeBoardMembers} onChange={setIncludeBoardMembers} />
            </Space>
          </Col>
          <Col xs={24}>
            <Space wrap>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={exporting || exportStatus?.status === "running" || exportStatus?.status === "queued"}
                onClick={handleStaticExport}
              >
                导出静态数据
              </Button>
              <Tag color={EXPORT_STATUS_COLORS[exportStatus?.status || "idle"]}>
                {exportStatus?.status || "idle"}
              </Tag>
              <Text type="secondary">
                默认输出 frontend/public/data；留空股票代码时只导出股票列表、最新行情、板块和 manifest。
              </Text>
            </Space>
          </Col>
          {exportStatus?.finished_at && (
            <Col xs={24}>
              <Text type="secondary">
                最近完成：{new Date(exportStatus.finished_at).toLocaleString("zh-CN")}
                {exportStatus.returncode != null ? ` · returncode=${exportStatus.returncode}` : ""}
              </Text>
            </Col>
          )}
          {exportStatus?.error_message && (
            <Col xs={24}>
              <Text type="danger">{exportStatus.error_message}</Text>
            </Col>
          )}
        </Row>
      </Card>

      {/* 同步状态表 */}
      <Card title="📊 数据库同步状态" extra={
        <Button
          icon={<ReloadOutlined />}
          size="small"
          loading={loading}
          onClick={loadStatus}
        >
          刷新
        </Button>
      }>
        <Table
          dataSource={syncItems}
          columns={columns}
          rowKey="table_name"
          loading={loading}
          pagination={false}
          size="middle"
        />
      </Card>
    </PageContainer>
  );
}
