import { PageContainer } from "@ant-design/pro-components";
import {
  Badge,
  Button,
  Card,
  Col,
  message,
  Row,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined, SyncOutlined, ApiOutlined, ThunderboltOutlined, DatabaseOutlined } from "@ant-design/icons";
import { useEffect, useState, useCallback } from "react";

import { fetchSyncStatus, triggerSync, type SyncStatusItem } from "@/services/dataManagement";
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

// ── 组件 ──────────────────────────────────────────────────────────────────

export default function DataManagementPage() {
  const [syncItems, setSyncItems] = useState<SyncStatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncingTable, setSyncingTable] = useState<string | null>(null);
  const [sourceMode, setSourceMode] = useState<DataSourceMode>(getDataSourceMode);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    const items = await fetchSyncStatus();
    setSyncItems(items);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

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
