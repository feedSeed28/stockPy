/** Trend slope screener — MA20 slope across all A-stocks */

import { PageContainer } from "@ant-design/pro-components";
import { Button, Checkbox, Select, Space, Table, Typography, message } from "antd";
import { useNavigate } from "@umijs/max";
import { useState } from "react";
import axios from "axios";

const { Text } = Typography;

const TRENDS = [
  { key: "strong_up", label: "强势上涨", color: "#cf1322", bg: "#fff1f0" },
  { key: "mild_up", label: "温和上涨", color: "#fa8c16", bg: "#fff7e6" },
  { key: "sideways", label: "横盘", color: "#8c8c8c", bg: "#fafafa" },
  { key: "mild_down", label: "温和下跌", color: "#1890ff", bg: "#e6f7ff" },
  { key: "strong_down", label: "大跌", color: "#3f8600", bg: "#f6ffed" },
];

export default function SlopePage() {
  const navigate = useNavigate();
  const [trend, setTrend] = useState("mild_up");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState(20);
  const [excludeSt, setExcludeSt] = useState(true);

  const loadData = async (t?: string) => {
    const currentTrend = t || trend;
    if (t) setTrend(t);
    setLoading(true);
    try {
      const { data } = await axios.get("/api/v1/slope/scan", {
        params: { trend: currentTrend, period, limit: 200, exclude_st: excludeSt },
      });
      if (data.code === 200) setItems(data.data.items || []);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const formatSlope = (v: number) => {
    if (v > 0.5) return <Text style={{ color: "#cf1322", fontWeight: "bold" }}>{v.toFixed(2)}%</Text>;
    if (v > 0.1) return <Text style={{ color: "#fa8c16" }}>{v.toFixed(2)}%</Text>;
    if (v > -0.1) return <Text style={{ color: "#8c8c8c" }}>{v.toFixed(2)}%</Text>;
    if (v > -0.5) return <Text style={{ color: "#1890ff" }}>{v.toFixed(2)}%</Text>;
    return <Text style={{ color: "#3f8600" }}>{v.toFixed(2)}%</Text>;
  };

  const columns = [
    { title: "代码", dataIndex: "code", width: 100 },
    { title: "名称", dataIndex: "name", width: 100 },
    { title: "行业", dataIndex: "industry", width: 100, ellipsis: true },
    { title: "收盘", dataIndex: "close", width: 80 },
    { title: "涨跌幅", dataIndex: "change_pct", width: 80,
      render: (v: number) => <Text style={{ color: v >= 0 ? "#cf1322" : "#3f8600" }}>{v?.toFixed(2)}%</Text> },
    { title: `MA5`, dataIndex: "ma5", width: 80 },
    { title: `MA20`, dataIndex: "ma20", width: 80 },
    { title: "斜率", dataIndex: "slope", width: 100, render: formatSlope },
    { title: "成交额(亿)", dataIndex: "amount", width: 100,
      render: (v: number) => (v ? (v / 1e8).toFixed(1) : "-") },
    { title: "日期", dataIndex: "trade_date", width: 100 },
  ];

  return (
    <PageContainer title="趋势斜率扫描">
      <Space style={{ marginBottom: 16 }} wrap>
        {TRENDS.map((t) => (
          <Button
            key={t.key}
            type={trend === t.key ? "primary" : "default"}
            onClick={() => loadData(t.key)}
            loading={loading && trend === t.key}
            style={{
              background: trend === t.key ? t.color : t.bg,
              borderColor: t.color,
              color: trend === t.key ? "#fff" : t.color,
              fontWeight: "bold",
            }}
          >
            {t.label}
          </Button>
        ))}
        <Select
          value={period}
          onChange={(v) => { setPeriod(v); loadData(trend); }}
          options={[
            { label: "MA5 斜率", value: 5 },
            { label: "MA10 斜率", value: 10 },
            { label: "MA20 斜率", value: 20 },
            { label: "MA30 斜率", value: 30 },
            { label: "MA60 斜率", value: 60 },
          ]}
          style={{ width: 130 }}
        />
        <Checkbox
          checked={excludeSt}
          onChange={(e) => { setExcludeSt(e.target.checked); setTimeout(loadData, 0); }}
        >
          不展示ST股票
        </Checkbox>
      </Space>

      <Table
        dataSource={items}
        columns={columns}
        rowKey="code"
        loading={loading}
        pagination={{ pageSize: 50, showSizeChanger: true }}
        scroll={{ y: 600 }}
        onRow={(r) => ({ onClick: () => navigate(`/stocks/${r.code}`), style: { cursor: "pointer" } })}
      />
    </PageContainer>
  );
}
